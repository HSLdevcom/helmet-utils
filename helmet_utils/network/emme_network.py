import webbrowser
import geopandas as gpd
import pandas as pd
import numpy as np
from pandas.api.types import is_float_dtype, is_integer_dtype
from datetime import datetime
from shapely.ops import Point
from tabulate import tabulate
from .height_data import HeightData
from pathlib import Path

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
        if (visualization_type == 'default'):
            columns_to_drop = [col for col in to_be_visualized.columns if col.startswith('@')]
            # Drop the columns and use the 'explore' method from GeoDataFrame
            no_extras = to_be_visualized.drop(columns=columns_to_drop)
            map = no_extras.explore(column=column, cmap=cmap)
            map.save('map.html')
            webbrowser.open('map.html')
        elif (visualization_type == 'bikes'):
            visualize_bikes = to_be_visualized[to_be_visualized['@pyoratieluokka']>0].copy()
            visualize_bikes['geometry'] = visualize_bikes['geometry'].apply(lambda x: x.offset_curve(-1))
            map = to_be_visualized.explore(column=column, cmap=cmap)
            visualize_bikes.explore(m=map, column="@pyoratieluokka", cmap=cmap)
            map.save('map.html')
            webbrowser.open('map.html')
        elif (visualization_type == 'all'):
            map = to_be_visualized.explore(column=column, cmap=cmap)
            map.save('map.html')
            webbrowser.open('map.html')

    # def merge(self, args*, kwargs**):
    #     super().merge(args*, kwargs**)

    @property
    def nodes(self):
        # Create a list to store node data
        nodes_data = []
        
        # Identify all columns with '_from' suffix
        from_columns = [col for col in self.columns if col.endswith('_from')]
        
        # Iterate through all links (rows) in the network
        for _, link in self.iterrows():            
            # Extract the first point of the linestring geometry
            from_geometry = Point(link.geometry.coords[0])
            
            # Check if 'From' node is a centroid
            from_is_centroid = 1 if link['c_from'].startswith('a*') else 0
            
            # Extract the attributes for the 'From' node
            node_data = {'Node': link['From'], 
                         'geometry': from_geometry, 
                         'is_centroid': from_is_centroid}
            
            for col in from_columns:
                node_data[col.replace('_from', '')] = link[col]
            
            nodes_data.append(node_data)

        # Create a DataFrame from the nodes data
        nodes_df = pd.DataFrame(nodes_data)
        unique_nodes_df = nodes_df.drop_duplicates(subset='Node')
        nodes_gdf = gpd.GeoDataFrame(unique_nodes_df, geometry='geometry', crs=self.crs)
        
        return nodes_gdf
    
    @property
    def centroids(self):
        return self.nodes[self.nodes['is_centroid']==1]
    
    def add_gradients(self, api_key, processors, elevation_fixes=None, full=True, in_place=False):
        if elevation_fixes is None:
            elevation_fixes = Path(__file__).resolve().parent.parent / 'data' / 'elevation_fixes.csv'
        height_data_writer = HeightData(api_key=api_key, nodes=self.nodes, links=self, in_place=in_place)
        print("here1")
        height_data_writer.add_height_data_parallel(processors=processors)
        print("here2")
        gdf = height_data_writer.gradient(elevation_fixes=elevation_fixes)
        
        # Merge @kaltevuus, @korkeus_from, @korkeus_to to the original network
        df_network_with_height = pd.merge(self, gdf[['From', 'To', '@kaltevuus', '@korkeus_from', '@korkeus_to']], on=['From', 'To'], how='left')
        print(self.head())
        print(gdf.head())
        print(df_network_with_height.head())
        network_with_height = EmmeNetwork(df_network_with_height)
        if in_place:
            self.update(network_with_height)
        return network_with_height
    
    def export_base_network(self, output_folder, project_name='default_project', scen_number='1', scen_name='default_scenario', export_datetime=None):
        current_date = export_datetime if export_datetime else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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

        def format_float(value):
            if value.is_integer():
                return str(int(value))
            else:
                return f"{value:.6f}".rstrip('0').rstrip('.')

        nodes['X-coord'] = nodes['geometry'].x.apply(float_to_string)
        nodes['Y-coord'] = nodes['geometry'].y.apply(float_to_string)
        nodes['Data1'] = nodes['Data1'].apply(format_float)
        nodes['Data2'] = nodes['Data2'].apply(format_float)
        nodes['Data3'] = nodes['Data3'].apply(format_float)

        
        # Drop 'geometry' column and create 'c' column based on 'is_centroid'
        nodes = nodes.drop(columns=['geometry'])
        nodes['c'] = nodes['is_centroid'].map({1: 'a*', 0: 'a'})
        nodes = nodes.sort_values(by='Node', ascending=True)
        links = links.sort_values(by='From', ascending=True)

        # Reorder the columns
        nodes = nodes[['c', 'Node', 'X-coord', 'Y-coord', 'Data1', 'Data2', 'Data3', 'Label']]
        links['Length'] = links['Length'].apply(format_float)
        links['Typ'] = links['Typ'].apply(format_float)
        links['Lan'] = links['Lan'].apply(format_float)
        links['VDF'] = links['VDF'].apply(format_float)
        links['Data1'] = links['Data1'].apply(format_float)
        links['Data2'] = links['Data2'].apply(format_float)
        links['Data3'] = links['Data3'].apply(format_float)

        output_path = Path(output_folder) / f"base_network_{scen_number}.txt"
        with open(output_path, 'w') as f:
            f.write(f"c Modeller - Base Network Transaction\nc Date: {current_date}\nc Project: {project_name}\nc Scenario {scen_number}: {scen_name}\nt nodes\n")
            self._to_fwf(nodes, f)
            f.write("\nt links\n")
            self._to_fwf(links, f)

    def export_extra_links(self, output_folder, scen_number=1, include_model_results=True):
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

        output_path = Path(output_folder) / f"extra_links_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            formatted_df.to_string(f, index=None)

    def export_extra_nodes(self, output_folder, scen_number=1):
        # Select all columns starting with "@" and ending in '_from' or '_to'
        if "@korkeus" in self.nodes.columns:
            to_be_printed = self.nodes[['Node', '@korkeus', '@hsl']].copy()
        else:
            to_be_printed = self.nodes[['Node', '@hsl']].copy()
        to_be_printed = to_be_printed.rename(columns={'Node': 'inode'})

        # Prepare export by creating the extra_attribute definitions read by EMME
        definition_string = "t extra_attributes\n"
        for column_name in to_be_printed.columns:
            if column_name == 'inode':
                continue
            definition_string = definition_string + f"{column_name} NODE 0.0 ''\n"
        definition_string = definition_string + "end extra_attributes\n"

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)

        output_path = Path(output_folder) / f"extra_nodes_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            formatted_df.to_string(f, index=None)

    def export_netfield_links(self, output_folder, scen_number=1):
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

        output_path = Path(output_folder) / f"netfield_links_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            formatted_df.to_string(f, index=None)

    def export(self, output_folder):
        self.export_base_network(output_folder)
        self.export_extra_links(output_folder)
        self.export_extra_nodes(output_folder)
        self.export_netfield_links(output_folder)

    def export_geopackage(self, filename):
        self.to_file(filename, driver='GPKG')
    
    def _to_fwf(self, df, file):
        content = tabulate(df.values.tolist(), list(df.columns), tablefmt="plain", disable_numparse=True)
        # Adjust formatting to match the original file
        # content = content.replace("  ", " ").replace(" \n", "\n")
        file.write(content)

    def export(self, output_folder):
        self.export_base_network(output_folder)
        self.export_extra_links(output_folder)
        self.export_extra_nodes(output_folder)
        self.export_netfield_links(output_folder)

