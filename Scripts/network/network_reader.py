from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.ops import Point, LineString
from emme_network import EmmeNetwork

class NetworkReader():
    """
    This is a class that processes exported Emme network folder

    ...

    Attributes
    ----------
    network_directory : str
        Network directory location

    Methods
    -------
    network():
        Returns an EmmeNetwork object for working on networks with Python data processing tools

    """

    def __init__(self, network_directory) -> None:
        self.network_dir = Path(network_directory)
        self.base_network_file = next(self.network_dir.glob('*base_network*.txt'), None)
        self.extra_links_file = next(self.network_dir.glob('*extra_links*.txt'), None)

        # Process the files if they exist
        if self.base_network_file and self.extra_links_file:
            self.gdf_nodes, self.df_links = self._extract_df_from_base_network()

    def _extract_df_from_base_network(self):
        with open(self.base_network_file, 'r') as file:
            lines = file.readlines()

        # Identifiers for the start of each table
        nodes_start = 't nodes'
        links_start = 't links'

        # Lists to hold the lines for each table
        nodes_lines = []
        links_lines = []

        # Flags to identify which table we're currently reading
        reading_nodes = False
        reading_links = False

        # Process each line in the file
        for line in lines:
            if nodes_start in line:
                reading_nodes = True
                reading_links = False
                continue  # Skip the line with the table identifier
            elif links_start in line:
                reading_nodes = False
                reading_links = True
                continue  # Skip the line with the table identifier

            # If we're reading a table, add the line to the appropriate list
            if reading_nodes:
                nodes_lines.append(line)
            elif reading_links:
                links_lines.append(line)

        # Convert lists to DataFrames
        df_nodes = pd.DataFrame([line.split() for line in nodes_lines[1:]], columns=nodes_lines[0].split())
        df_links = pd.DataFrame([line.split() for line in links_lines[1:]], columns=links_lines[0].split())

        df_nodes['geometry'] = df_nodes.apply(lambda row: Point(row['X-coord'], row['Y-coord']), axis=1)
        gdf_nodes = gpd.GeoDataFrame(df_nodes, geometry="geometry", crs="EPSG:3879")
        return gdf_nodes, df_links

    def centroids(self):
        return self.gdf_nodes[self.gdf_nodes['c'].str.contains("\*")]
        
    def nodes_to_gdf(self):
        self.df_nodes['geometry'] = self.df_nodes.apply(lambda row: Point(row['X-coord'], row['Y-coord']), axis=1)
        return gpd.GeoDataFrame(self.df_nodes, geometry="geometry", crs="EPSG:3879")

    def links_to_gdf(self, include_node_data=True):
        # Create a dictionary to map node geometries
        node_dict = dict(zip(self.gdf_nodes['Node'], self.gdf_nodes['geometry']))
        
        # Map geometries to the 'From' and 'To' columns
        self.df_links['geometry_from'] = self.df_links['From'].map(node_dict)
        self.df_links['geometry_to'] = self.df_links['To'].map(node_dict)
        
        # Create LineStrings from geometries
        self.df_links['geometry'] = self.df_links.apply(lambda row: LineString([row['geometry_from'], row['geometry_to']]), axis=1)
        self.df_links = self.df_links.drop(columns=['geometry_from', 'geometry_to'])
        if include_node_data:
            # Merge node data for 'From' nodes
            self.df_links = self.df_links.merge(self.gdf_nodes.add_suffix('_from'), left_on='From', right_on='Node_from', how='left')
            # Merge node data for 'To' nodes
            self.df_links = self.df_links.merge(self.gdf_nodes.add_suffix('_to'), left_on='To', right_on='Node_to', how='left')
            self.df_links['is_connector'] = self.df_links.apply(lambda row: 1 if row['c_to']=='a*' or row['c_from']=='a*' else 0, axis=1)
            self.df_links = self.df_links.drop(columns=['c', 'c_to', 'Node_from', 'Node_to', 'X-coord_from', 'X-coord_to', 'Y-coord_from', 'Y-coord_to','geometry_from', 'geometry_to'])

        
        # Convert to GeoDataFrame
        return gpd.GeoDataFrame(self.df_links, geometry='geometry', crs='EPSG:3879')

    def extra_links_to_df(self):
        with open(self.extra_links_file, 'r') as file:
            # Skip lines until the end of the header
            while True:
                line = file.readline()
                if line.startswith('end extra_attributes'):
                    break
            
            # The next line contains the column names
            columns = file.readline().strip().split()
            
            # Read the rest of the file into a DataFrame
            df_extra_links = pd.read_csv(file, names=columns, delim_whitespace=True)
        return df_extra_links

    def network(self):
        gdf_links = self.links_to_gdf()
        df_extra_links = self.extra_links_to_df()
        gdf_links['From'] = gdf_links['From'].astype('int64')
        gdf_links['To'] = gdf_links['To'].astype('int64')
        gdf = gdf_links.merge(df_extra_links, left_on=['From', 'To'], right_on=['inode', 'jnode'], how='left')
        network = EmmeNetwork(gdf.drop(columns=['inode','jnode']), geometry='geometry', crs='EPSG:3879')
        return network

