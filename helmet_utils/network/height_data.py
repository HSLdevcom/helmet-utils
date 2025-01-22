from __future__ import annotations

import os
import httpx
import rasterio
import tempfile
import webbrowser
import time
import multiprocessing
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiPolygon
from shapely.ops import split
from rtree import index
from concurrent.futures import ProcessPoolExecutor, as_completed


pd.options.display.float_format = '{:.6f}'.format


class HeightData:
    def __init__(self, api_key, nodes, links, in_place=False):
        self.nodes = nodes.to_crs("EPSG:3067")[['Node', 'is_centroid', 'geometry']].copy()
        self.links = links.to_crs("EPSG:3067")[['From','To','@hinta_aht', '@hinta_pt', '@hinta_iht', '@pyoratieluokka', 'geometry']].copy()
        self.api_key = api_key


    def process_half_squares(self, half_squares, api_key: str, nodes):
        idx = self.build_index(nodes)  # Build the index in the local process
        processed_squares = []
        for i, coords in enumerate(half_squares.bounds.values):
            coords_buff = coords + [-10, -10, 10, 10]
            potential = list(idx.intersection(coords_buff))
            if not potential:
                continue

            points_with_elevations = self.read_height_data_parallel(
                np.asarray(nodes.loc[potential].union_all().buffer(20).bounds),
                api_key,
                nodes.loc[potential]['geometry']
            )
            processed_squares.append((points_with_elevations.index, points_with_elevations))
        return processed_squares

    def add_height_data_parallel(self, processors=2):
        available_processors = multiprocessing.cpu_count()
        if processors > available_processors:
            print(f"Warning: Specified number of processors ({processors}) exceeds available CPU cores ({available_processors}). Using {available_processors} processors instead.")
            processors = available_processors

        print("Writing height data requires you to nest your code inside ")
        print("a main function and protect the main module with")
        print("\tif __name__ == '__main__':")
        print("\t\tmain()")
        print("\ninstead of writing python code outside a main function\n")
        centroids = self.nodes[self.nodes['is_centroid']==1].copy()
        centroids['geometry'] = centroids.apply(lambda row: Point([row.geometry.x, row.geometry.y, 0.0]), axis=1)
        self.nodes.loc[centroids.index, 'geometry'] = centroids['geometry']
        not_centroids = self.nodes[self.nodes['is_centroid'] == 0].copy()
        self._prepare_area(not_centroids)
        num_squares = len(self.gdf_squares.explode(index_parts=False).index)
        half = num_squares // 2
        quarter = half // 2
        # Split the squares based on the number of processors
        squares_split = np.array_split(self.gdf_squares.explode(index_parts=False), processors)
        first_half = self.gdf_squares.explode(index_part=False).iloc[:half]
        second_half = self.gdf_squares.explode(index_part=False).iloc[half:]

        first_quarter = self.gdf_squares.explode(index_parts=False).iloc[:quarter]
        second_quarter = self.gdf_squares.explode(index_parts=False).iloc[quarter:half]
        third_quarter = self.gdf_squares.explode(index_parts=False).iloc[half:half+quarter]
        fourth_quarter = self.gdf_squares.explode(index_parts=False).iloc[half+quarter:]


        print(f"Number of raster squares: {num_squares}")
        print(f"Reading elevation data and appending to network using {processors} processors...")
        print()
        quarters_done = 0
        updated_points = {}
        with ProcessPoolExecutor(max_workers=processors) as executor:
            # TODO: Add the ability to use any number of processors
            # futures = [executor.submit(self.process_half_squares, squares, self.api_key, not_centroids) for squares in squares_split]
            if processors == 2:
                future_first_half = executor.submit(self.process_half_squares, first_half, self.api_key, not_centroids)
                future_second_half = executor.submit(self.process_half_squares, second_half, self.api_key, not_centroids)
                process_pool = [future_first_half, future_second_half]
            else:
                future_first_quarter = executor.submit(self.process_half_squares, first_quarter, self.api_key, not_centroids)
                future_second_quarter = executor.submit(self.process_half_squares, second_quarter, self.api_key, not_centroids)
                future_third_quarter = executor.submit(self.process_half_squares, third_quarter, self.api_key, not_centroids)
                future_fourth_quarter = executor.submit(self.process_half_squares, fourth_quarter, self.api_key, not_centroids)
                process_pool = [future_first_quarter, future_second_quarter, future_third_quarter, future_fourth_quarter]

            print('Processing...', end='\r')
            quarters_done = 0
            updated_points = {}
            for i, future in enumerate(as_completed(process_pool)):
                try:
                    points_with_elevations = future.result()
                except Exception as e:
                    print(f"Error processing future {i}: {e}")
                    continue

                if i + 1 > quarters_done:
                    print(f'Processing... {int((i + 1) * (100 / processors))}% done.', end='\r')
                    quarters_done += 1
                    for points in points_with_elevations:
                        updated_points.update(points[1])
        
        for i, point in updated_points.items():
            self.nodes.loc[i, 'geometry'] = point
        print("\nFinished processing height data!")
        return self.nodes
    
    def _prepare_area(self, nodes: gpd.GeoDataFrame):
        print("Cutting model area into manageable squares...", end='\r')
        network_area = nodes.union_all().convex_hull
        geometry_cut = self.quadrat_cut_geometry(network_area.buffer(10), quadrat_width=9500) 
        self.gdf_squares = gpd.GeoDataFrame(geometry=pd.Series(geometry_cut), crs="EPSG:3067")
        print("Cutting model area into manageable squares... Done!")
    
    @staticmethod
    def read_height_data_parallel(coords, api_key, points_list):
        def fetch_with_retries(url, max_retries=3, timeout=10, retry_delay=2):
                """
                Fetch a URL with retry logic.
                
                Parameters:
                - url: The URL to fetch.
                - max_retries: Maximum number of retries on failure.
                - timeout: Timeout for the request.
                - retry_delay: Delay between retries in seconds.
                
                Returns:
                - Response object from httpx.
                """
                attempt = 0
                while attempt < max_retries:
                    try:
                        response = httpx.get(url, timeout=timeout)
                        response.raise_for_status()  # Raise an HTTPError for bad responses
                        return response
                    except httpx.RequestError as e:
                        print(f"Request failed: {e}. Retrying in {retry_delay} seconds...")
                    except httpx.HTTPStatusError as e:
                        print(f"HTTP error occurred: {e}. Retrying in {retry_delay} seconds...")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}. Retrying in {retry_delay} seconds...")
                    
                    attempt += 1
                    time.sleep(retry_delay)
                
                raise Exception(f"Failed to fetch URL {url} after {max_retries} retries.")

        x1, y1, x2, y2 = coords
        url = f"https://avoin-karttakuva.maanmittauslaitos.fi/ortokuvat-ja-korkeusmallit/wcs/v2?service=WCS&version=2.0.1&request=GetCoverage&api-key={api_key}&CoverageID=korkeusmalli_2m&SUBSET=E({int(x1)},{int(x2)})&SUBSET=N({int(y1)},{int(y2)})&format=image/tiff&geotiff:compression=LZW"
        
        try:
            response = fetch_with_retries(url, max_retries=3, timeout=10, retry_delay=2)
            
            with tempfile.NamedTemporaryFile(delete=False) as geotiff:
                geotiff.write(response.content)
            
            try:
                with rasterio.open(geotiff.name) as dataset:
                    for i, point in points_list.items():
                        row, col = dataset.index(point.x, point.y)
                        elevation = dataset.read(1, window=((row, row + 1), (col, col + 1)))[0][0]
                        points_list[i] = Point([point.x, point.y, max(0, elevation)])
            finally:
                os.remove(geotiff.name)
            
            return points_list

        except Exception as e:
            print(f"Failed to read height data: {e}")
            for i, point in points_list.items():
                points_list[i] = Point([point.x, point.y, 0.0])
            return points_list

        # Left these to test the above 20240912:

        # x1, y1, x2, y2 = coords
        # url = f"https://avoin-karttakuva.maanmittauslaitos.fi/ortokuvat-ja-korkeusmallit/wcs/v2?service=WCS&version=2.0.1&request=GetCoverage&api-key={api_key}&CoverageID=korkeusmalli_2m&SUBSET=E({int(x1)},{int(x2)})&SUBSET=N({int(y1)},{int(y2)})&format=image/tiff&geotiff:compression=LZW"

        # try:
        #     r = requests.get(url, stream=True, timeout=10)
        #     r.raise_for_status()
        # except requests.RequestException as e:
        #     print(f"Error fetching elevation data: {e}")
        #     print("Setting elevation to 0 for affected points.")
        #     for i, point in points_list.items():
        #         points_list[i] = Point([point.x, point.y, 0.0])
        #     return points_list

        # with tempfile.NamedTemporaryFile(delete=False) as geotiff:
        #     for chunk in r.iter_content(chunk_size=1024):
        #         if chunk:
        #             geotiff.write(chunk)

        # try:
        #     with rasterio.open(geotiff.name) as dataset:
        #         for i, point in points_list.items():
        #             row, col = dataset.index(point.x, point.y)
        #             elevation = dataset.read(1, window=((row, row + 1), (col, col + 1)))[0][0]
        #             points_list[i] = Point([point.x, point.y, max(0, elevation)])
        # finally:
        #     os.remove(geotiff.name)
        # return points_list

    


    @staticmethod
    def build_index(network: gpd.GeoDataFrame):
        idx = index.Index()
        for id, geom in zip(network.index, network.geometry):
            idx.insert(id, geom.bounds)
        return idx

    @staticmethod
    def quadrat_cut_geometry(geometry, quadrat_width, min_num=3):
        """
        Split a Polygon or MultiPolygon up into sub-polygons of a specified size.


        The MIT License (MIT)

        Copyright (c) 2016-2024 Geoff Boeing https://geoffboeing.com/

        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following condition

        Parameters
        ----------
        geometry : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
            the geometry to split up into smaller sub-polygons
        quadrat_width : numeric
            the linear width of the quadrats with which to cut up the geometry (in
            the units the geometry is in)
        min_num : int
            the minimum number of linear quadrat lines (e.g., min_num=3 would
            produce a quadrat grid of 4 squares)

        Returns
        -------
        geometry : shapely.geometry.MultiPolygon
        """
        # create n evenly spaced points between the min and max x and y bounds
        west, south, east, north = geometry.bounds
        x_num = int(np.ceil((east - west) / quadrat_width) + 1)
        y_num = int(np.ceil((north - south) / quadrat_width) + 1)
        x_points = np.linspace(west, east, num=max(x_num, min_num))
        y_points = np.linspace(south, north, num=(max(y_num, min_num)))

        # create a quadrat grid of lines at each of the evenly spaced points
        vertical_lines = [LineString([(x, y_points[0]), (x, y_points[-1])]) for x in x_points]
        horizont_lines = [LineString([(x_points[0], y), (x_points[-1], y)]) for y in y_points]
        lines = vertical_lines + horizont_lines

        # recursively split the geometry by each quadrat line
        geometries = [geometry]

        for line in lines:
            # split polygon by line if they intersect, otherwise just keep it
            split_geoms = [split(g, line).geoms if g.intersects(line) else [g] for g in geometries]
            # now flatten the list and process these split geoms on the next line in the list of lines
            geometries = [g for g_list in split_geoms for g in g_list]

        return MultiPolygon(geometries)

    @staticmethod
    def process_geometries(df_el, node_dict):
        def create_linestring(geometry_i, geometry_j):
            """
            Creates a LineString object from two geometry points.
            """
            try:
                return LineString([geometry_i, geometry_j])
            except Exception as e:
                print(f"The following geometries raised exception \"{e}\"")
                print(f"geometry_i: {geometry_i}, geometry_j: {geometry_j}")
        """
        Processes the geometries to map nodes to Point objects and create LineString objects.
        """
        # Map the jnode and inode columns to Point objects
        df_el["geometry_j"] = df_el["To"].map(node_dict)
        df_el["geometry_i"] = df_el["From"].map(node_dict)

        # Apply the create_linestring function to each row
        df_el['line_geometry'] = df_el.apply(lambda row: create_linestring(row["geometry_i"], row['geometry_j']) if pd.notna(row['geometry_j']) else row["geometry_i"], axis=1)

        return df_el

    def gradient(self, elevation_fixes=None, output=None):
        if elevation_fixes is None:
            elevation_fixes = Path(__file__).resolve().parent.parent / 'data' / 'elevation_fixes.csv'
        print("Writing gradients to network...")
        centroids = self.nodes[self.nodes["is_centroid"] == 1]

        # Create a dictionary of Node to Point objects
        node_dict = dict(zip(self.nodes["Node"], self.nodes["geometry"]))

        df_fixes = pd.read_csv(elevation_fixes)
        for i, row in df_fixes.iterrows():
            geom = node_dict[row['node']]
            new_geom = Point([geom.x, geom.y, row['elevation']])
            node_dict.update({row['node']: new_geom})

        df_el = self.process_geometries(self.links, node_dict)
        gdf_el = gpd.GeoDataFrame(df_el, geometry="line_geometry", crs="EPSG:3067")
        gdf_el['@korkeus_from'] = gdf_el.apply(lambda row: row['geometry_i'].coords[0][2], axis=1)
        gdf_el['@korkeus_to'] = gdf_el.apply(lambda row: row['geometry_j'].coords[0][2] if row['To']>0 else 0.0, axis=1)
        gdf = gdf_el.drop(columns=["geometry_i", "geometry_j"])
        gdf['elevation_difference'] = gdf.apply(lambda row: row['line_geometry'].coords[1][2] - row['line_geometry'].coords[0][2] if row['To']>0 else 0.0, axis=1)
        gdf['@kaltevuus'] = gdf.apply(lambda row: ((row['line_geometry'].coords[0][2] - row['line_geometry'].coords[1][2]) / row['line_geometry'].length) * 100 if row['To']>0 else 0.0, axis=1)
        gdf.loc[gdf['From'].isin(centroids['Node']) | gdf['To'].isin(centroids['Node']), '@kaltevuus'] = 0.0


        if output:
            # Tiedoston luominen
            extra_links_with_gradient = gdf.rename(columns={'From':'inode','To':'jnode'}).drop(columns=['geometry','line_geometry', 'elevation_difference', 'elevation_i', 'elevation_j'])

            f = open(output, 'a')
            f.write("t extra_attributes\n@hinta_aht LINK 0.0 ''\n@hinta_pt LINK 0.0 ''\n@hinta_iht LINK 0.0 ''\n@pyoratieluokka LINK 0.0 'pyoratieluokka'\n@kaltevuus LINK 0.0 'kaltevuus'\n@korkeus_from LINK 0.0 'korkeus_from'\n@korkeus_to LINK 0.0 'korkeus_to'\nend extra_attributes\n")
            extra_links_with_gradient.to_string(f, index=None)#, formatters=fmts)
            f.close()

            # #Paikallinen visualisointi Foliumilla
            # gdf_over_0 = gdf.loc[gdf['@kaltevuus']>0]
            # map = gdf_over_0.explore(column='@kaltevuus', style_kwds={'weight':3})

            # map.save('map.html')
            # webbrowser.open('map.html')
        else:
            return gdf


# def main():
#     base_network_file = "verkko_23/Scenario_200/base_network_200.txt"
#     extra_links_file = "verkko_23/Scenario_200/extra_links_200.txt"
#     start_time_height_data = time.time()
#     height_data_writer = HeightData(API_KEY, base_network_file, extra_links_file)
#     end_time_height_data = time.time()
#     elapsed_height_data_s = int(end_time_height_data-start_time_height_data)
#     elapsed_height_data_min = (elapsed_height_data_s)//60
#     elapsed_height_data = f"{elapsed_height_data_min} min {elapsed_height_data_s-elapsed_height_data_min*60} s."
#     print(f"Time elapsed reading height data: {elapsed_height_data}.")
# 
#     height_data_writer.gradient("extra_links_gradients_200.txt", "elevation_fixes.csv")

