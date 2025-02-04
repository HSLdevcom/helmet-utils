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

    def __getitem__(self, key):
        result = super().__getitem__(key)
        if isinstance(result, gpd.GeoDataFrame):
            return EmmeNetwork(result)
        else:
            return result

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if isinstance(value, gpd.GeoDataFrame):
            self.__dict__.update(value.__dict__)

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
        nodes_gdf = self._add_hsl_extra_attribute(nodes_gdf)
        
        return nodes_gdf
    
    @property
    def centroids(self):
        return self.nodes[self.nodes['is_centroid']==1]

    def update_nodes(self, updated_nodes):
        """
        Update the nodes in the network with the provided updated nodes DataFrame.
        """
        # Iterate through the updated nodes and update the corresponding links
        for _, node in updated_nodes.iterrows():
            node_id = node['Node']
            self.loc[self['From'] == node_id, 'geometry'] = node['geometry']
            self.loc[self['From'] == node_id, 'is_centroid'] = node['is_centroid']
            for col in node.index:
                if col not in ['Node', 'geometry', 'is_centroid']:
                    self.loc[self['From'] == node_id, f'{col}_from'] = node[col]

    
    def add_gradients(self, api_key, processors, elevation_fixes=None, full=True, in_place=False):
        if elevation_fixes is None:
            elevation_fixes = Path(__file__).resolve().parent.parent / 'data' / 'elevation_fixes.csv'
        
        # Ensure the necessary columns exist
        for col in ['@kaltevuus', '@korkeus_from', '@korkeus_to']:
            if col not in self.columns:
                self[col] = 0.0
        
        # Determine which links need to be updated
        network_to_update = self.copy()
        if not full:
            # drop rows where @kaltevuus is something other than 0
            network_to_update = network_to_update[network_to_update['@kaltevuus'] == 0]

        height_data_writer = HeightData(api_key=api_key, network=network_to_update)
        height_data_writer.add_height_data_parallel(processors=processors)
        gdf = height_data_writer.gradient(elevation_fixes=elevation_fixes)
        
        # Create a copy of self to modify
        network_copy = self.copy()
        
        # Vectorized update of the new values
        mask = (network_copy['From'].isin(gdf['From'])) & (network_copy['To'].isin(gdf['To']))
        network_copy.loc[mask, ['@kaltevuus', '@korkeus_from', '@korkeus_to']] = gdf.set_index(['From', 'To'])[['@kaltevuus', '@korkeus_from', '@korkeus_to']].values
        
        if in_place:
            self.update(network_copy)
            return self
        else:
            return EmmeNetwork(network_copy)
        

    @staticmethod
    def float_to_string(value):
        if value % 1 == 0:
            return str(int(value))
        else:
            return str(value)

    @staticmethod
    def format_float(value):
        if value.is_integer():
            return str(int(value))
        else:
            return f"{value:.6f}".rstrip('0').rstrip('.')

    def export_base_network(self, output_folder, project_name='default_project', scen_number='1', scen_name='default_scenario', export_datetime=None):
        current_date = export_datetime if export_datetime else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        links = self.copy()
        links['c'] = 'a'
        links = links[['c', 'From', 'To', 'Length', 'Modes', 'Typ', 'Lan', 'VDF', 'Data1', 'Data2', 'Data3']]
        links = links[links['To']>0]
        nodes = self.nodes

        nodes['X-coord'] = nodes['geometry'].x.apply(self.float_to_string)
        nodes['Y-coord'] = nodes['geometry'].y.apply(self.float_to_string)
        nodes['Data1'] = nodes['Data1'].apply(self.format_float)
        nodes['Data2'] = nodes['Data2'].apply(self.format_float)
        nodes['Data3'] = nodes['Data3'].apply(self.format_float)

        # Drop 'geometry' column and create 'c' column based on 'is_centroid'
        nodes = nodes.drop(columns=['geometry'])
        nodes['c'] = nodes['is_centroid'].map({1: 'a*', 0: 'a'})
        nodes = nodes.sort_values(by='Node', ascending=True)
        links = links.sort_values(by='From', ascending=True)

        # Reorder the columns
        nodes = nodes[['c', 'Node', 'X-coord', 'Y-coord', 'Data1', 'Data2', 'Data3', 'Label']]
        links['Length'] = links['Length'].apply(self.format_float)
        links['Typ'] = links['Typ'].apply(self.format_float)
        links['Lan'] = links['Lan'].apply(self.format_float)
        links['VDF'] = links['VDF'].apply(self.format_float)
        links['Data1'] = links['Data1'].apply(self.format_float)
        links['Data2'] = links['Data2'].apply(self.format_float)
        links['Data3'] = links['Data3'].apply(self.format_float)

        output_path = Path(output_folder) / f"base_network_{scen_number}.txt"
        with open(output_path, 'w') as f:
            f.write(f"c Modeller - Base Network Transaction\nc Date: {current_date}\nc Project: {project_name}\nc Scenario {scen_number}: {scen_name}\nt nodes\n")
            self._to_fwf(nodes, f)
            f.write("\nt links\n")
            self._to_fwf(links, f)

    def _add_hsl_extra_attribute(self, nodes):
        nodes['@hsl'] = 0
        nodes['@hsl'] = nodes['Label'].apply(lambda x: 1 if any(char in x for char in 'ABCDE') else 0)
        return nodes

    def export_extra_links(self, output_folder, scen_number=1, include_model_results=True):
        model_has_run = "@time_freeflow_car" in self.columns
        helmet_5 = "@kaltevuus" in self.columns
        self.fillna(0, inplace=True)

        # Allow user to remove model_results from extra_links
        if not include_model_results:
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

        # Apply formatting functions
        to_be_printed['inode'] = to_be_printed['inode'].apply(self.float_to_string)
        to_be_printed['jnode'] = to_be_printed['jnode'].apply(self.float_to_string)
        for col in to_be_printed.columns:
            if col not in ['inode', 'jnode']:
                to_be_printed[col] = to_be_printed[col].apply(self.format_float)

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

        output_path = Path(output_folder) / f"extra_links_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            self._to_fwf(to_be_printed, f)

    def export_extra_nodes(self, output_folder, scen_number=1):
        # Select the 'Node' column and all columns containing '@'
        to_be_printed = self.nodes[['Node'] + [col for col in self.nodes.columns if '@' in col]].copy()
        to_be_printed = to_be_printed.rename(columns={'Node': 'inode'})

        # Prepare export by creating the extra_attribute definitions read by EMME
        definition_string = "t extra_attributes\n"
        for column_name in to_be_printed.columns:
            if column_name == 'inode':
                continue
            if column_name == '@hsl':
                definition_string += f"{column_name} NODE 0.0 'Hsl alue'\n"
            elif 'transit_won' in column_name:
                definition_string += f"{column_name} NODE 0.0 'transit_work {self._get_transit_description(column_name)}'\n"
            elif 'transit_len' in column_name:
                definition_string += f"{column_name} NODE 0.0 'transit_leisure {self._get_transit_description(column_name)}'\n"
            else:
                definition_string += f"{column_name} NODE 0.0 ''\n"
        definition_string += "end extra_attributes\n"

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)

        output_path = Path(output_folder) / f"extra_nodes_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            formatted_df.to_string(f, index=None)

    def _get_transit_description(self, column_name):
        description_string = ''
        if 'boa' in column_name:
            description_string += 'total_boardings'
        elif 'trb' in column_name:
            description_string += 'transfer_boardings'
        if 'vrk' in column_name:
            description_string += ' vrk'
        elif 'aht' in column_name:
            description_string += ' aht'
        elif 'pt' in column_name:
            description_string += ' pt'
        elif 'iht' in column_name: 
            description_string += ' iht'
        return description_string

    def export_netfield_links(self, output_folder, scen_number=1):
        #TODO: only continue if columns with # are present
        self.fillna(0, inplace=True)
        to_be_printed = self.copy()
        netfield_columns = [col for col in to_be_printed.columns if '#' in col and '_to' not in col and '_from' not in col]
        if not netfield_columns:
            return None
        to_be_printed = to_be_printed.loc[self['To']>0, ['From', 'To'] + netfield_columns]

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
    
    def to_crs(self, crs=None, epsg=None, inplace=False):
        if inplace:
            super().to_crs(crs=crs, epsg=epsg, inplace=True)
            return None
        else:
            new_gdf = super().to_crs(crs=crs, epsg=epsg, inplace=False)
            # Create a new EmmeNetwork object with the new GeoDataFrame
            new_emme_network = EmmeNetwork(new_gdf)
            # Ensure all the original metadata is copied to the new object
            new_emme_network.__dict__.update(self.__dict__)
            return new_emme_network
        

    def drop(self, labels=None, axis=0, index=None, columns=None, level=None, inplace=False, errors='raise'):
        if inplace:
            super().drop(labels=labels, axis=axis, index=index, columns=columns, level=level, inplace=inplace, errors=errors)
            return None
        else:
            new_gdf = super().drop(labels=labels, axis=axis, index=index, columns=columns, level=level, inplace=inplace, errors=errors)
            new_emme_network = EmmeNetwork(new_gdf)
            new_emme_network.__dict__.update(self.__dict__)
            return new_emme_network
        
    def copy(self):
        new_gdf = super().copy()
        new_emme_network = EmmeNetwork(new_gdf)
        new_emme_network.__dict__.update(self.__dict__)
        return new_emme_network