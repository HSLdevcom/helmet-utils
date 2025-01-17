import time
import webbrowser
import geopandas as gpd
import pandas as pd
import numpy as np
from pandas.api.types import is_float_dtype, is_integer_dtype
from datetime import datetime
from shapely.ops import Point
from tabulate import tabulate
from .height_data import HeightData

class EmmeNetwork(gpd.GeoDataFrame):
    """
    This is a class for working with an EMME network. Created in scenario_reader.py
    """

    # Initialize the EmmeNetwork with the same parameters as GeoDataFrame
    def __init__(self, gdf, *args, **kwargs):
        super().__init__(gdf, *args, **kwargs)

    
    def to_crs(self, crs=None, epsg=None, inplace=False):
        # If inplace is True, update the CRS in place and return None
        if inplace:
            super().to_crs(crs=crs, epsg=epsg, inplace=True)
            return None
        # Otherwise, create a new GeoDataFrame with the updated CRS
        else:
            new_gdf = super().to_crs(crs=crs, epsg=epsg, inplace=False)
            # Create a new EmmeNetwork object with the new GeoDataFrame
            new_emme_network = EmmeNetwork(new_gdf)
            # Ensure all the original metadata is copied to the new object
            new_emme_network.__dict__.update(self.__dict__)
            return new_emme_network
        
    def copy(self):
        return EmmeNetwork(super().copy())

    # New method 'visualize'
    def visualize(self, visualization_type='default', column=None, cmap=None):
        to_be_visualized = self[self['To']>0].copy()
        to_be_visualized['geometry'] = to_be_visualized['geometry'].apply(lambda x: x.offset_curve(-0.6))
        # Define different visualizations based on the type
        if visualization_type == 'default':
            columns_to_drop = [col for col in to_be_visualized.columns if col.startswith('@')]
            # Drop the columns and use the 'explore' method from GeoDataFrame
            no_extras = to_be_visualized.drop(columns=columns_to_drop)
            map = no_extras.explore(column=column, cmap=cmap)
            map.save('map.html')
            webbrowser.open('map.html')
        elif visualization_type == 'bikes':
            visualize_bikes = to_be_visualized[to_be_visualized['@pyoratieluokka']>0].copy()
            visualize_bikes['geometry'] = visualize_bikes['geometry'].apply(lambda x: x.offset_curve(-1))
            map = to_be_visualized.explore(column=column, cmap=cmap)
            visualize_bikes.explore(m=map, column="@pyoratieluokka", cmap=cmap)
            map.save('map.html')
            webbrowser.open('map.html')
        elif visualization_type == 'all':
            map = to_be_visualized.explore(column=column, cmap=cmap)
            map.save('map.html')
            webbrowser.open('map.html')

    # def merge(self, args*, kwargs**):
    #     super().merge(args*, kwargs**)

    @property
    def nodes(self):
         # Create a list to store node data
        nodes_data = []
        
        # Iterate through all links (rows) in the network
        for _, link in self.iterrows():            
            # Extract the first and last points of the linestring geometry
            from_geometry = Point(link.geometry.coords[0])
            
            # Check if 'From' node is a centroid
            from_is_centroid = 1 if link['c_from'].startswith('a*') else 0

            # Extract the elevation and other attributes for the 'From' node
            elevation_from = link.get('@korkeus_from', None)
            hsl_from = link.get('@hsl_from', None)

            nodes_data.append({'Node': link['From'], 
                               'geometry': from_geometry, 
                               'is_centroid': from_is_centroid, 
                               'Data1': link['Data1_from'],
                               'Data2': link['Data2_from'],
                               'Data3': link['Data3_from'],
                               'Label': link['Label_from'],
                               '@korkeus': elevation_from,
                               '@hsl': hsl_from})

        # Create a DataFrame from the nodes data
        nodes_df = pd.DataFrame(nodes_data)
        unique_nodes_df = nodes_df.drop_duplicates(subset='Node')
        nodes_gdf = gpd.GeoDataFrame(unique_nodes_df, geometry='geometry', crs=self.crs)
        
        return nodes_gdf
    
    @property
    def centroids(self):
        return self.nodes[self.nodes['is_centroid']==1]
    
    def add_gradients(self, api_key, processors, full=True, in_place=False):
        height_data_writer = HeightData(api_key=api_key, network=self, in_place=in_place)
        height_data_writer.add_height_data_parallel(processors=processors)
        updated_network = height_data_writer.gradient(elevation_fixes="elevation_fixes.csv")
        if in_place:
            self.update(updated_network)
        else:
            return EmmeNetwork(updated_network)
    
    def export_base_network(self, project_name='default_project', scen_number='1', scen_name='default_scenario'):
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        links = self.copy()
        links['c'] = 'a'
        links = links[['c', 'From', 'To', 'Length', 'Modes', 'Typ', 'Lan', 'VDF', 'Data1', 'Data2', 'Data3']]
        links = links[links['To']>0]
        nodes = self.nodes

        def float_to_string(value):
            if value % 1 == 0:
                return str(int(value))
            else:
                return str(value)

        nodes['X-coord'] = nodes['geometry'].x.apply(float_to_string)
        nodes['Y-coord'] = nodes['geometry'].y.apply(float_to_string)
        
        # Drop 'geometry' column and create 'c' column based on 'is_centroid'
        nodes = nodes.drop(columns=['geometry'])
        nodes['c'] = nodes['is_centroid'].map({1: 'a*', 0: 'a'})
        nodes = nodes.sort_values(by='Node', ascending=True)
        links = links.sort_values(by='From', ascending=True)

        # Reorder the columns
        nodes = nodes[['c', 'Node', 'X-coord', 'Y-coord', 'Data1', 'Data2', 'Data3', 'Label']]
        f = open(f"base_network_{scen_number}.txt", 'a')
        f.write(f"c Modeller - Base Network Transaction\nc Date: {current_date}\nc Project: {project_name}\nc Scenario {scen_number}: {scen_name}\nt nodes\n")
        self._to_fwf(nodes, f)
        f.write("\nt links\n")
        self._to_fwf(links, f)
        f.close()

        return

    def export_extra_links(self, scen_number=1, include_model_results=True):
        model_has_run = "@time_freeflow_car" in self.columns
        helmet_5 = "@kaltevuus" in self.columns
        self.fillna(0, inplace=True)

        # Allow user to remove model_results from extra_links
        if model_has_run and not include_model_results:
            if helmet_5:
                to_be_printed = self[['From','To','@hinta_aht','@hinta_pt','@hinta_iht','@pyoratieluokka','@kaltevuus']].copy()
                to_be_printed = to_be_printed.rename(columns={'From':'inode', 'To':'jnode'})
            else:
                to_be_printed = self[['From','To','@hinta_aht','@hinta_pt','@hinta_iht','@pyoratieluokka']].copy()
                to_be_printed = to_be_printed.rename(columns={'From':'inode', 'To':'jnode'})
        else:
            # Select all columns starting with "@" plus "From" and "To", excluding those ending in '_from' or '_to'
            to_be_printed = self[self.columns[self.columns.str.startswith('@') & ~self.columns.str.endswith(('_from', '_to')) | self.columns.isin(['From', 'To'])]].copy()
            to_be_printed = to_be_printed.rename(columns={'From': 'inode', 'To': 'jnode'})
        
        to_be_printed = to_be_printed.sort_values(by=['inode', 'jnode'], ascending=True)
        to_be_printed = to_be_printed[to_be_printed['jnode']>0]

        # Prepare export by creating the extra_attribute definitions read by EMME
        definition_string = "t extra_attributes\n"
        for column_name in to_be_printed.columns:
            if column_name in ['inode', 'jnode']:
                continue
            elif column_name in ['@hinta_aht','@hinta_pt','@hinta_iht']:
                definition_string = definition_string + f"{column_name} LINK 0.0 ''\n"
            else:
                # Defining the attribute hints
                times_of_day = ['_aht','_vrk','_pt','_iht']
                for time in times_of_day:
                    if time in column_name:
                        if any(sub in column_name for sub in ['aux_transit','cost','time']):
                            column_name_stripped = column_name.replace(time, "")
                            break
                        else:
                            column_name_stripped = column_name.replace(time, " volume")
                            break
                else:
                    # If no changes, don't change anything
                    column_name_stripped = column_name
                definition_string = definition_string + f"{column_name} LINK 0.0 '{column_name_stripped.lstrip('@')}'\n"
        definition_string = definition_string + "end extra_attributes\n"

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)

        f = open(f"extra_links_{scen_number}.txt", 'a')
        f.write(definition_string)
        formatted_df.to_string(f, index=None)
        f.close()
        return

    def export_extra_nodes(self, scen_number=1):
        # Select all columns starting with "@" and ending in '_from' or '_to'
        to_be_printed = self.nodes[['Node', '@korkeus', '@hsl']].copy()
        
        # Prepare export by creating the extra_attribute definitions read by EMME
        definition_string = "t extra_attributes\n"
        for column_name in to_be_printed.columns:
            if column_name == 'Node':
                continue
            definition_string = definition_string + f"{column_name} NODE 0.0 ''\n"
        definition_string = definition_string + "end extra_attributes\n"

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)

        f = open(f"extra_nodes_{scen_number}.txt", 'a')
        f.write(definition_string)
        formatted_df.to_string(f, index=None)
        f.close()
        return
    
    def export_netfield_links(self, scen_number=1):
        self.fillna(0, inplace=True)
        to_be_printed = self.loc[self['To']>0, self.columns[self.columns.str.startswith('#') | self.columns.isin(['From', 'To'])]].copy()
        to_be_printed = to_be_printed.rename(columns={'From': 'inode', 'To': 'jnode'})
        
        to_be_printed = to_be_printed.sort_values(by=['inode', 'jnode'], ascending=True)
        to_be_printed = to_be_printed[to_be_printed['jnode']>0]

        # Prepare export by creating the extra_attribute definitions read by EMME
        definition_string = "t network_fields\n"
        for column_name in to_be_printed.columns:
            if column_name in ['inode', 'jnode']:
                continue
            if is_float_dtype(self[column_name]):
                type_string = 'REAL'
            elif is_integer_dtype(self[column_name]):
                type_string = 'INTEGER32'
            else:
                unhandled_datatype = self[column_name].dtype()
                print(f"Datatype not handled: {unhandled_datatype}")
                
            column_name_stripped = column_name
            definition_string = definition_string + f"{column_name} LINK {type_string} '{column_name_stripped.lstrip('#')}'\n"
        definition_string = definition_string + "end network_fields\n"

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)


        f = open(f"netfield_links_{scen_number}.txt", 'a')
        f.write(definition_string)
        formatted_df.to_string(f, index=None)
        f.close()
        return

    def export_geopackage(self, filename):
        self.to_file(filename, driver='GPKG')
    
    def _to_fwf(self, df, file):
        content = tabulate(df.values.tolist(), list(df.columns), tablefmt="plain", disable_numparse=True)
        file.write(content)

    def export(self, output_folder):
        self.export_base_network(output_folder)
        self.export_extra_links(output_folder)
        self.export_extra_nodes(output_folder)
        self.export_netfield_links(output_folder)

