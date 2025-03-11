import os
import pandas as pd
import geopandas as gpd
import numpy as np
import requests
from typing import Optional, Dict

from shapely.geometry import Point, MultiPoint
from shapely import voronoi_polygons
from pathlib import Path

from ..network import scenario_reader

AREA_MULTIPLIER = 400*0.000001

class ZoneData():
    def __init__(self, landuse, population, workplace, education, bikes, zones, landcover_file):
        self.landuse = landuse
        self.population = population
        self.workplace = workplace
        self.education = education
        self.bikes = bikes
        self.zones = zones
        self.landcover_file = landcover_file

    def get_ryhti_within_zone(self, zone_id):
        # Get the geometry of the specified zone
        zone = self.zones.to_crs("EPSG:4326")[self.zones['SIJ2023'] == zone_id].geometry.iloc[0]
        
        # Get the bounding box of the zone
        minx, miny, maxx, maxy = zone.bounds
        
        # SYKE RYHTI database includes data on buildings. 
        url = f"https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1/collections/open_building/items?f=application/json&bbox={minx},{miny},{maxx},{maxy}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            features = data['features']
            
            # Convert features to GeoDataFrame
            gdf = gpd.GeoDataFrame.from_features(features)
            gdf.crs = "EPSG:4326"
            gdf = gdf.to_crs("EPSG:3879")  # Same crs as self.zones
            
            # Only include features within the zone
            gdf = gpd.overlay(gdf, self.zones[self.zones['SIJ2023']==zone_id], how='intersection')
        else:
            print(f"Failed to fetch data from OGC server. Status code: {response.status_code}")

        return gdf
    
    def calculate_floorarea_shares(self, area_changes:dict, new_zones:gpd.GeoDataFrame):
        floorarea_shares = {}
        for original_zone_id in area_changes.keys():
            buildings = self.get_ryhti_within_zone(original_zone_id)
            total_floorarea = buildings['gross_floor_area'].sum()
            for new_zone_id in area_changes[original_zone_id]:
                # Get buildings within the sub zone
                buildings_within_sub_zone = gpd.overlay(buildings, new_zones[new_zones['SIJ2023']==new_zone_id], how='intersection')
                sub_zone_floorarea = buildings_within_sub_zone['gross_floor_area'].sum()

                # Calculate the share of the sub zone's floor area compared to the total floor area
                floorarea_share = sub_zone_floorarea / total_floorarea if total_floorarea > 0 else 0
                floorarea_shares[new_zone_id] = (original_zone_id, floorarea_share)
        
        return floorarea_shares

    
    def recalculate_zonedata(self, output_path: str, area_changes:Optional[Dict[int, int]] = None, split_areas=False, network_folder: str='', year=2023, split_zones_filename:str=None):
        if split_areas and area_changes:
            print("Cannot split areas with predefined area changes.")
            return
        elif split_areas:
            if not network_folder:
                print("Network is required to split areas. Either provide a network or set split_areas to False.")
                return
            zones, area_changes = self.split_areas(network_folder, output_path, split_zones_filename=split_zones_filename)
        else:
            zones = self.zones
            area_changes = area_changes

        print(f"Target year: {year}")
        if area_changes:
            print(f"Area changes received: {area_changes}")
        else:
            print("No area changes defined, skipping population recalculation")
            print("If changes have been made to existing zone geometry, please adjust populations by hand for now.")
            print("Otherwise, specify area changes or set split_areas to True")

        # Calculate landuse according to area splits
        lnd, landuse_changes = self.recalculate_landuse(zones, self.landcover_file, year, area_changes)
        landuse_changes = self.calculate_floorarea_shares(area_changes, zones)
        # Calculate the rest using landuse data
        if area_changes:
            print("Redistributing population data based on landuse patterns on modified areas.")
            print("Only total values are changed, shares will stay the same. Please check that the redistributed values make sense")
            print("Especially .edu will need readjustments")
            pop = self.recalculate_population(landuse_changes)
            wrk = self.recalculate_workplace(landuse_changes)
            edu = self.recalculate_education(landuse_changes)
            bks = self.recalculate_bikes(landuse_changes)
        else:
            pop = self.population
            wrk = self.workplace
            edu = self.education
            bks = self.bikes
        self.fill_folder(lnd, edu, pop, wrk, bks, year, output_path)
        print(f"Done. Output in {output_path}. Please double check the recalculated values and copy the rest of the input files.")

    def _read_landcover(self, zones:gpd.GeoDataFrame, landcover_filepath: str, year:int) -> gpd.GeoDataFrame:
        try:
            import rasterstats
        except ImportError:
            raise ImportError("The 'rasterstats' library is required to calculate built area.")

        sijoittelualueet = zones.to_crs("EPSG:3067")
        corine = rasterstats.zonal_stats(sijoittelualueet.geometry, landcover_filepath, categorical=True)
        df_corine = pd.DataFrame(data=corine)
        landcover = sijoittelualueet.join(df_corine)
        landcover = self.calculate_landuse_metrics(landcover, year)
        landcover.index.name = None
        return landcover

    def recalculate_landuse(self, zones:gpd.GeoDataFrame, landcover_file: str, year: int=2023, area_changes: Optional[Dict[int, int]] = None):
        # Corine ids representing built area, then convert squares to km^2
        original_landuse = self.landuse.copy()
        df = self._read_landcover(zones, landcover_file, 2023)

        area_changes_mapped = {i: int(original) for original, new in area_changes.items() for i in new}
        # Create a dictionary of the form {original_zone_id: [(new_zone_id1, share_of_original_landuse1), (new_zone_id2, share_of_original_landuse2)]}
        try:
            landuse_changes = {i: (original, df.loc[i, 'builtar']/original_landuse.loc[original, 'builtar']) for original, new in area_changes.items() for i in new}
        except KeyError:
            raise KeyError("Area changes and zones do not match. Cut zones using a GIS editor, or automatically split areas by setting split_areas=True")
        df['detach'] = original_landuse['detach']
        df = self._calculate_detach_share_for_region(df, area_changes_mapped, original_landuse)
        df = df[['builtar', 'sportsar', 'detach']]
        return df, landuse_changes


    def recalculate_population(self, landuse_changes):
        original_population = self.population
        pop = original_population.copy()
        for id, landuse_share in landuse_changes.items():
            pop.loc[id, 'total'] = round(original_population.loc[landuse_share[0]]['total'] * landuse_share[1])
            pop.loc[id, 'sh_7-17'] = original_population.loc[landuse_share[0], 'sh_7-17']
            pop.loc[id, 'sh_1829'] = original_population.loc[landuse_share[0], 'sh_1829']
            pop.loc[id, 'sh_3049'] = original_population.loc[landuse_share[0], 'sh_3049']
            pop.loc[id, 'sh_5064'] = original_population.loc[landuse_share[0], 'sh_5064']
            pop.loc[id, 'sh_65-'] = original_population.loc[landuse_share[0], 'sh_65-']
        return pop
    
    def recalculate_workplace(self, landuse_changes):
        original_workplace = self.workplace
        wrk = original_workplace.copy()
        for id, landuse_share in landuse_changes.items():
            wrk.loc[id, 'total'] = round(original_workplace.loc[landuse_share[0]]['total'] * landuse_share[1])
            wrk.loc[id, 'sh_serv'] = original_workplace.loc[landuse_share[0], 'sh_serv']
            wrk.loc[id, 'sh_shop'] = original_workplace.loc[landuse_share[0], 'sh_shop']
            wrk.loc[id, 'sh_logi'] = original_workplace.loc[landuse_share[0], 'sh_logi']
            wrk.loc[id, 'sh_indu'] = original_workplace.loc[landuse_share[0], 'sh_indu']
        return wrk
    
    def recalculate_education(self, landuse_changes):
        # TODO: Actually recalculate from data
        original_education = self.education
        edu = original_education.copy()
        for id, landuse_share in landuse_changes.items():
            edu.loc[id, 'compreh'] = round(original_education.loc[landuse_share[0], 'compreh'] * landuse_share[1])
            edu.loc[id, 'secndry'] = round(original_education.loc[landuse_share[0], 'secndry'] * landuse_share[1])
            edu.loc[id, 'tertiary'] = round(original_education.loc[landuse_share[0], 'tertiary'] * landuse_share[1])
        return edu
    
    def recalculate_bikes(self, landuse_changes):
        # TODO: Actually recalculate from data
        # Currently not used in the model so only adding 0s now
        original_bikes = self.bikes
        bks = original_bikes.copy()
        for id, landuse_share in landuse_changes.items():
            if id == landuse_share[0]:
                bks.loc[id, 'distance'] = original_bikes.loc[landuse_share[0], 'distance']
                bks.loc[id, 'rel_capacity'] = original_bikes.loc[landuse_share[0], 'rel_capacity']
                bks.loc[id, 'rel_stations'] = original_bikes.loc[landuse_share[0], 'rel_stations']
                bks.loc[id, 'operator'] = original_bikes.loc[landuse_share[0], 'operator']
            else:
                bks.loc[id, 'distance'] = original_bikes.loc[landuse_share[0], 'distance']
                bks.loc[id, 'rel_capacity'] = 0.0
                bks.loc[id, 'rel_stations'] = 0.0
                bks.loc[id, 'operator'] = original_bikes.loc[landuse_share[0], 'operator']

        return bks

    def _calculate_detach_share_for_region(self, df, area_changes_mapped, original_lnd):
        for i in area_changes_mapped.keys():
            df.loc[i, 'detach'] = original_lnd.loc[area_changes_mapped[i], 'detach']
        return df
    
    def split_areas(self, scenario_directory: str, output_directory: str, split_zones_filename: str=None):
        print("Splitting zones based on added centroids.")
        if not os.path.exists(f"{output_directory}"):
            os.makedirs(f"{output_directory}")
        if not split_zones_filename:
            split_zones_filename = "SIJ2023_aluejako_jaettu"
        split_zones_filename = split_zones_filename.rstrip(".gpkg")

        scenario = scenario_reader.get_emme_scenario(scenario_directory)
        centroids = scenario.network.centroids
        area_centroids = centroids[(centroids['Node'] < 34000) | (centroids['Node'] > 35999)]
        
        # Create a dictionary with zones to split and the corresponding centroids
        zones_to_split = self._get_zones_to_split(area_centroids)
        
        if not zones_to_split:
            print("No zones to split.")
            return
        print(f"Zones to split: {zones_to_split}")
        
        split_zones = self.voronoi(self.zones, area_centroids, zones_to_split)
        
        # Remove original zones that were split
        original_zones_to_keep = self.zones[~self.zones['SIJ2023'].isin(zones_to_split.keys())]
        
        # Combine original zones with split zones
        combined_zones = pd.concat([original_zones_to_keep, split_zones], ignore_index=True)
        combined_zones.fillna(0, inplace=True)
        combined_zones.to_file(f"{output_directory}/{split_zones_filename}.gpkg", driver='GPKG')
        print("Zones split successfully.")
        
        return combined_zones, zones_to_split

    def _get_zones_to_split(self, centroids):
        zones_to_split = {}
        for zone in self.zones.itertuples():
            matching_centroids = [centroid.Node for centroid in centroids.itertuples() if Point(centroid.geometry.centroid).within(zone.geometry) and centroid.Node != zone.SIJ2023]
            if matching_centroids:
                zones_to_split[zone.SIJ2023] = matching_centroids + [zone.SIJ2023]
        return zones_to_split

    @staticmethod
    def voronoi(zones, centroids, zones_to_split):
        new_zones = []
        for zone_id, centroid_nodes in zones_to_split.items():
            zone = zones[zones['SIJ2023'] == zone_id].iloc[0]
            matching_centroids = centroids[centroids['Node'].isin(centroid_nodes)]
            
            # Extract coordinates
            points = MultiPoint([Point(centroid.geometry.centroid) for centroid in matching_centroids.itertuples()])
            # Convert bounds to Polygon
            # bounds_polygon = Polygon.from_bounds(*zone.geometry.bounds)
            vor = voronoi_polygons(points, extend_to=zone.geometry)

            # Create new zones based on Voronoi regions
            for region in vor.geoms:
                if region.is_valid and region.intersects(zone.geometry):
                    intersection = region.intersection(zone.geometry)
                    new_zone = gpd.GeoDataFrame(geometry=[intersection], crs=zones.crs)
                    new_zones.append(new_zone)

        # Combine new zones into a single GeoDataFrame
        split_zones = gpd.GeoDataFrame(pd.concat(new_zones, ignore_index=True), crs=zones.crs)

        # Assign attributes to new zones
        for i, zone in split_zones.iterrows():
            centroid = matching_centroids.iloc[i]
            original_zone = zones[zones['SIJ2023'] == zone_id].iloc[0]
            split_zones.at[i, 'SIJ2019'] = original_zone['SIJ2019']
            split_zones.at[i, 'KELA'] = original_zone['KELA']
            split_zones.at[i, 'SIJ_ID'] = centroid['Node']
            split_zones.at[i, 'SIJ2023'] = centroid['Node']

        return split_zones

    def fill_folder(self, lnd:pd.DataFrame, edu: pd.DataFrame, pop: pd.DataFrame, wrk: pd.DataFrame, bks: pd.DataFrame, year: int, output_path:str):
        if not os.path.exists(f"{output_path}"):
            os.makedirs(f"{output_path}")
        
        # EDU
        edu = edu.astype({'compreh': 'int', 'secndry': 'int', 'tertiary': 'int'})
        f = open(f'{output_path}/{year}.edu', 'a')
        f.write('# Schools 2023\n#\n# compreh: Students in comprehensive school (1-9)\n# secndry: Students in upper secondary education (gymnasium, vocational)\n# tertiary: Students in tertiary education (university, college, polytechnic)\n#\n')
        edu.to_csv(f, sep="\t", lineterminator='\n')
        f.close()

        # POP
        pop = pop.fillna(0)
        pop = pop.astype({'total': 'int','sh_7-17': 'float','sh_1829': 'float','sh_3049': 'float','sh_5064': 'float','sh_65-': 'float'})
        f = open(f'{output_path}/{year}.pop', 'a')
        f.write('# Population 2023\n#\n# total: total number of residents in zone\n# sh_7-17: share of population aged 7-17\n# sh_1829: share of population aged 18-29\n# sh_3049: share of population aged 30-49\n# sh_5064: share of population aged 50-64\n# sh_65-: share of population aged over 65\n#\n')
        
        pop.to_csv(f, float_format='%.4g', sep="\t", lineterminator='\n')
        f.close()

        # WRK
        wrk = wrk.fillna(0)
        wrk = wrk.astype({'total': 'int', 'sh_serv': 'float', 'sh_shop': 'float', 'sh_logi': 'float', 'sh_indu': 'float'})
        f = open(f'{output_path}/{2022}.wrk', 'a')
        f.write('# Workplaces 2022\n#\n# total: total number of workplaces in zone\n# sh_serv: service workplaces as share of total number of workplaces\n# sh_shop: retail workplaces as share of total number of workplaces\n# sh_logi: logistics workplaces as share of total number of workplaces\n# sh_indu: industry workplaces as share of total number of workplaces\n#\n')
        wrk.to_csv(f, float_format='%.4g', sep="\t", lineterminator='\n')
        f.close()

        # LND
        f = open(f'{output_path}/{2023}.lnd', 'a')
        f.write('# Land use 2023\n#\n# builtar: area of built environment\n# sportsar: area of sports or leisure facilities, currently not used in Helmet 5.0\n# detach: detached houses as share of total number of houses\n#\n')

        lnd.to_csv(f, float_format='%.4g', sep="\t", lineterminator='\n')
        f.close()

        # BKS
        f = open(f'{output_path}/{year}.bks', 'a')
        f.write('# Sharebikes 2023\n# rel_capacity: total capacity at stations / zone area\n# rel_stations: number of stations / zone_area\n# operator: operator city or region\n# HE: Helsinki-Espoo\n# VA: Vantaa\n# PO: Porvoo\n# LA: Lahti\n#\n')
        lnd.to_csv(f, float_format='%.4g', sep="\t", lineterminator='\n')
        f.close()

        return

    def calculate_landuse_metrics(self, gdf: gpd.GeoDataFrame, year: int) -> gpd.GeoDataFrame:
        gdf['area'] = gdf['geometry'].area
        gdf = gdf.fillna(0)
        gdf['id'] = gdf.index
        if year == 2012:  
            gdf['builtar'] = (gdf[1] + gdf[2] + gdf[3] + gdf[4] + gdf[5] + gdf[6] + gdf[7] + gdf[8] + gdf[9] + gdf[10] + gdf[11] + gdf[12] + gdf[13] + gdf[14] + gdf[15])*AREA_MULTIPLIER
            gdf['vesi'] = (gdf[46] + gdf[47] + gdf[48]) * AREA_MULTIPLIER
            gdf['kosteikko'] = (gdf[40] + gdf[41] + gdf[42] + gdf[43] + gdf[44] + gdf[45]) * AREA_MULTIPLIER
            gdf['sportsar'] = gdf[13] * AREA_MULTIPLIER
        elif year >= 2018:  # Corine has changed slightly
            gdf['builtar'] = (gdf[1] + gdf[2] + gdf[3] + gdf[4]+ gdf[5] + gdf[6] + gdf[7] + gdf[8] + gdf[9] + gdf[10] + gdf[11] + gdf[13] + gdf[14] + gdf[15] + gdf[16])*AREA_MULTIPLIER
            gdf['vesi'] = (gdf[47] + gdf[48] + gdf[49]) * AREA_MULTIPLIER
            gdf['kosteikko'] = (gdf[41] + gdf[42] + gdf[43] + gdf[44] + gdf[45] + gdf[46]) * AREA_MULTIPLIER
            gdf['sportsar'] = gdf[14] * AREA_MULTIPLIER

        gdf['land_area'] = gdf['area']-gdf['vesi']
        gdf['builtar'] = gdf.apply(lambda row: row['builtar'] if row['builtar'] <= row['land_area'] else row['land_area'], axis=1)
        gdf['SIJ2023'] = gdf['SIJ2023'].astype(int)
        gdf = gdf.set_index('SIJ2023').sort_index()
        gdf = gdf[['builtar','sportsar']]
    
        return gdf

