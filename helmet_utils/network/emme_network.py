import webbrowser
import geopandas as gpd
import pandas as pd
from datetime import datetime
from shapely.ops import Point

class EmmeNetwork(gpd.GeoDataFrame):
    """
    This is a class for working with an EMME network. Created in network_utils.py
    """


    # Initialize the EmmeNetwork with the same parameters as GeoDataFrame
    def __init__(self, gdf, *args, **kwargs):
        super().__init__(gdf, *args, **kwargs)

    # New method 'visualize'
    def visualize(self, visualization_type='default', column=None, cmap=None):
        # Define different visualizations based on the type
        if visualization_type == 'default':
            columns_to_drop = [col for col in self.columns if col.startswith('@')]
            # Drop the columns and use the 'explore' method from GeoDataFrame
            no_extras = self.drop(columns=columns_to_drop)
            map = no_extras.explore(column=column, cmap=cmap)
            map.save('map.html')
            webbrowser.open('map.html')
        elif visualization_type == 'all':
            map = self.explore(column=column, cmap=cmap)
            map.save('map.html')
            webbrowser.open('map.html')

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

            nodes_data.append({'Node': link['From'], 
                               'geometry': from_geometry, 
                               'is_centroid': from_is_centroid, 
                               'Data1':link['Data1_from'],
                               'Data2':link['Data2_from'],
                               'Data3':link['Data3_from'],
                               'Label':link['Label_from']})

        # Create a DataFrame from the nodes data
        nodes_df = pd.DataFrame(nodes_data)
        unique_nodes_df = nodes_df.drop_duplicates(subset='Node')
        nodes_gdf = gpd.GeoDataFrame(unique_nodes_df, geometry='geometry')
        
        return nodes_gdf
    
    @property
    def centroids(self):
        return self.nodes[self.nodes['is_centroid']==1]


    def export_base_network(self, project_name="default_project", scen_number=1, scen_name="default_scenario"):
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        links = self.copy()
        links['c'] = 'a'
        links = links[['c', 'From', 'To', 'Length', 'Modes', 'Typ', 'Lan', 'VDF', 'Data1', 'Data2', 'Data3']]
        print(links.head())
        
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
        
        # Reorder the columns
        nodes = nodes[['c', 'Node', 'X-coord', 'Y-coord', 'Data1', 'Data2', 'Data3', 'Label']]
        print(nodes.head())

        f = open(f"base_network.txt", 'a')
        f.write(f"c Helmet_utils\nc Date: {current_date}\nc Project: {project_name}\nc Scenario {scen_number}: {scen_name}\nt nodes\n")
        nodes.to_string(f, index=None)
        f.write("\nt links\n")
        links.to_string(f, index=None)
        f.close()

        
        return
    
    def export_extra_links(self, scen_number=1, include_model_results=True):
        model_has_run = "@car_work_vrk" in self.columns
        helmet_5 = "@kaltevuus" in self.columns

        # Allow user to remove model_results from extra_links
        if model_has_run and not include_model_results:
            if helmet_5:
                to_be_printed = self[['From','To','@hinta_aht','@hinta_pt','@hinta_iht','@pyoratieluokka','@kaltevuus']].copy()
                to_be_printed = to_be_printed.rename(columns={'From':'inode', 'To':'jnode'})
            else:
                to_be_printed = self[['From','To','@hinta_aht','@hinta_pt','@hinta_iht','@pyoratieluokka']].copy()
                to_be_printed = to_be_printed.rename(columns={'From':'inode', 'To':'jnode'})
        else:
            # Select all columns starting with "@" plus "From" and "To"
            to_be_printed = self[self.columns[self.columns.str.startswith('@') | self.columns.isin(['From', 'To'])]].copy()
            to_be_printed = to_be_printed.rename(columns={'From': 'inode', 'To': 'jnode'})
        
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

        f = open(f"extra_attributes_{scen_number}.txt", 'a')
        f.write(definition_string)
        to_be_printed.to_string(f, index=None)
        f.close()
        return
