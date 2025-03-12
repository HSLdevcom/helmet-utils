from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiPoint
from .emme_network import EmmeNetwork
from .transit_network import TransitNetwork
from .emme_scenario import EmmeScenario
import re

class ScenarioReader:
    """
    This is a class that processes an exported Emme scenario folder

    ...

    Attributes
    ----------
    scenario_directory : str
        Scenario directory location

    Methods
    -------
    scenario():
        Returns an EmmeScenario object for working on scenarios with Python data processing tools

    """

    def __init__(self, scenario_directory) -> None:
        self.input_folder = scenario_directory
        print("Currently only supports an Emme/Helmet scenario that has not been run. Make sure that data has not been lost if the model has run.")
        self.scenario_dir = Path(scenario_directory)
        # Network
        self.base_network_file = next(self.scenario_dir.glob('base_network*.txt'), None)
        self.extra_links_file = next(self.scenario_dir.glob('extra_links*.txt'), None)
        self.extra_nodes_file = next(self.scenario_dir.glob('extra_nodes*.txt'), None)
        # Transit
        self.transit_lines_file = next(self.scenario_dir.glob('transit_lines*.txt'), None)
        self.extra_transit_lines_file = next(self.scenario_dir.glob('extra_transit_lines*.txt'), None)
        # Only present if the model has run
        self.extra_segments_file = next(self.scenario_dir.glob('*extra_segments*.txt'), None)
        # Optional netfield values
        self.netfield_links_file = next(self.scenario_dir.glob('netfield_links*.txt'), None)
        self.netfield_nodes_file = next(self.scenario_dir.glob('netfield_nodes*.txt'), None)
        self.netfield_segments_file = next(self.scenario_dir.glob('netfield_segments*.txt'), None)
        self.netfield_transit_lines_file = next(self.scenario_dir.glob('netfield_transit_lines*.txt'), None)
        # Additional files
        self.link_shape_file = next(self.scenario_dir.glob('link_shape_*.txt'), None)
        self.modes_file = next(self.scenario_dir.glob('modes_*.txt'), None)
        self.turns_file = next(self.scenario_dir.glob('turns_*.txt'), None)
        self.vehicles_file = next(self.scenario_dir.glob('vehicles_*.txt'), None)
        # Process the files if they exist
        if self.base_network_file:
            self.gdf_nodes, self.df_links = self._extract_df_from_base_network()
            # Create a dictionary to map node geometries to node numbers
            self.node_dict = dict(zip(self.gdf_nodes['Node'], self.gdf_nodes['geometry']))
        else:
            raise FileNotFoundError("Scenario directory not found.")


    def scenario(self) -> EmmeScenario:
        gdf_links = self.links_to_gdf()

        gdf_links['From'] = gdf_links['From'].astype('int64')
        gdf_links['To'] = gdf_links['To'].astype('int64')
        network = EmmeNetwork(gdf_links, geometry='geometry', crs='EPSG:3879')
        transit = self.transit()
        link_shape = self.import_link_shape()
        modes = self.import_modes()
        turns = self.import_turns()
        vehicles = self.import_vehicles()
        return EmmeScenario(network, transit, self.input_folder, self.project_name, self.scenario_name, link_shape, modes, turns, vehicles)


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
            if "Project:" in line:
                self.project_name = line.split('Project:')[-1].strip()
            if "Scenario" in line:
                self.scenario_number = line.split('Scenario')[-1].split(':')[0]
                self.scenario_name = line.split('Scenario')[-1].split(':')[-1].strip()
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

        # Explicitly set the data types for each column
        df_nodes = df_nodes.astype({
            'Node': 'Int32',
            'X-coord': 'float64',
            'Y-coord': 'float64',
            'Data1': 'float64',
            'Data2': 'float64',
            'Data3': 'float64',
            'Label': 'str'
        })
        df_links = df_links.astype({
            'From': 'Int32',
            'To': 'Int32',
            'Length': 'float64',
            'Modes': 'str',
            'Typ': 'int32',
            'Lan': 'float64',
            'VDF': 'int32',
            'Data1': 'float64',
            'Data2': 'float64',
            'Data3': 'float64'
        })

        # Read extra nodes file if it exists
        if self.extra_nodes_file:
            df_extra_nodes, _ = self.extra_attributes_to_df(self.extra_nodes_file)
            df_nodes = df_nodes.merge(df_extra_nodes, left_on='Node', right_on='inode', how='left').drop(columns=['inode'])

        df_nodes['geometry'] = df_nodes.apply(lambda row: Point(row['X-coord'], row['Y-coord']), axis=1)
        gdf_nodes = gpd.GeoDataFrame(df_nodes, geometry="geometry", crs="EPSG:3879")
        return gdf_nodes, df_links
        
    def nodes_to_gdf(self):
        self.df_nodes['geometry'] = self.df_nodes.apply(lambda row: Point(row['X-coord'], row['Y-coord']), axis=1)
        return gpd.GeoDataFrame(self.df_nodes, geometry="geometry", crs="EPSG:3879")

    def links_to_gdf(self, include_node_data=True):     
        # Map geometries to the 'From' and 'To' columns
        self.df_links['geometry_from'] = self.df_links['From'].map(self.node_dict)
        self.df_links['geometry_to'] = self.df_links['To'].map(self.node_dict)

        # Create LineStrings from geometries
        self.df_links['geometry'] = self.df_links.apply(lambda row: LineString([row['geometry_from'], row['geometry_to']]), axis=1)
        self.df_links = self.df_links.drop(columns=['geometry_from', 'geometry_to'])

        # Read extra links file if it exists
        if self.extra_links_file:
            df_extra_links, _ = self.extra_attributes_to_df(self.extra_links_file)
            self.df_links = self.df_links.merge(df_extra_links, left_on=['From', 'To'], right_on=['inode', 'jnode'], how='left').drop(columns=['inode', 'jnode'])

        # Read netfield links file if it exists
        if self.netfield_links_file:
            df_netfield_links = self._netfield_links_to_df()
            try:
                self.df_links = self.df_links.merge(df_netfield_links, left_on=['From', 'To'], right_on=['inode', 'jnode'], how='left')
            except KeyError:
                self.df_links = self.df_links.merge(df_netfield_links, on=['From', 'To'], how='left')

        if include_node_data:
            # Find orphan nodes with no connecting links
            all_nodes = set(self.gdf_nodes['Node'])
            linked_nodes = set(self.df_links['From']).union(set(self.df_links['To']))
            orphan_nodes = all_nodes - linked_nodes

            # Create DataFrame for orphan nodes with their geometries
            orphan_df = self.gdf_nodes[self.gdf_nodes['Node'].isin(orphan_nodes)].copy()
            orphan_df['From'] = orphan_df['Node']
            orphan_df['To'] = 0  # No node has this id, used to find orphan nodes when exporting
            orphan_df['geometry'] = orphan_df['geometry']

            # Append orphan nodes to links DataFrame
            self.df_links = pd.concat([self.df_links, orphan_df[['From', 'To', 'geometry']]], ignore_index=True)

            # Merge node data for 'From' nodes
            self.df_links = self.df_links.merge(self.gdf_nodes.add_suffix('_from'), left_on='From', right_on='Node_from', how='left')
            # Merge node data for 'To' nodes
            self.df_links = self.df_links.merge(self.gdf_nodes.add_suffix('_to'), left_on='To', right_on='Node_to', how='left')
            self.df_links['is_connector'] = self.df_links.apply(lambda row: 1 if row['c_to']=='a*' or row['c_from']=='a*' else 0, axis=1)
            self.df_links = self.df_links.drop(columns=['c', 'c_to', 'Node_from', 'Node_to', 'X-coord_from', 'X-coord_to', 'Y-coord_from', 'Y-coord_to','geometry_from', 'geometry_to'])

        
        # Convert to GeoDataFrame
        return gpd.GeoDataFrame(self.df_links, geometry='geometry', crs='EPSG:3879')

    def extra_attributes_to_df(self, extra_attributes_file):
        with open(extra_attributes_file, 'r') as file:
            # Skip lines until the end of the header
            header = []
            while True:
                line = file.readline()
                if line.startswith('t extra_attributes'):
                    continue
                elif line.startswith('end extra_attributes'):
                    break
                else:
                    header.append(line)
            
            # The next line contains the column names
            columns = file.readline().strip().split()
            
            # Read the rest of the file into a DataFrame
            df_extra_attributes = pd.read_csv(file, names=columns, sep=r'\s+')
        return df_extra_attributes, header
    
    def _netfield_links_to_df(self):
        with open(self.netfield_links_file, 'r') as file:
            # Skip lines until the end of the header
            header = []
            while True:
                line = file.readline()
                if line.startswith('t network_fields'):
                    continue
                elif line.startswith('end network_fields'):
                    break
                else:
                    header.append(line)
            
            # The next line contains the column names
            columns = file.readline().strip().split()
            
            # Read the rest of the file into a DataFrame
            df_netfield_links = pd.read_csv(file, names=columns, sep=r'\s+')
        
        return df_netfield_links
    
    def _extra_segments_to_df(self):
        # Extra segments has a weird structure, requires its own parser
        data = []
        with open(self.extra_segments_file, 'r') as file:
            header = []
            while True:
                line = file.readline()
                if line.startswith('t extra_attributes'):
                    continue
                elif line.startswith('end extra_attributes'):
                    break
                else:
                    header.append(line)
            # The next line contains the column names
            columns = file.readline().strip().split()
            columns.append('Segment_num')  # Add segment_num to columns
            current_line_id = None
            segment_num = 0
            for line in file.readlines():
                parts = line.strip().split("'")
                line_id = str(parts[1]).strip()
                if line_id != current_line_id:
                    current_line_id = line_id
                    segment_num = 1
                else:
                    segment_num += 1
                data.append([line_id] + parts[2].strip().split() + [segment_num])  # Add segment_num to data

        df_segments = pd.DataFrame(data, columns=columns)
        df_segments = df_segments.rename(columns={'line': 'Line', 'segment_num': 'Segment_num'})
        return df_segments
    
    def _netfield_segments_to_df(self):
        data = []
        with open(self.netfield_segments_file, 'r') as file:
            # Skip lines until the end of the header
            while True:
                line = file.readline()
                if line.startswith('end network_fields'):
                    break

            # The next line contains the column names
            columns = file.readline().strip().split()
            columns.append('segment_num')  # Add segment_num to columns
            current_line_id = None
            segment_num = 0
            for line in file.readlines():
                parts = line.strip().split("'")
                line_id = parts[1].strip()
                if line_id != current_line_id:
                    current_line_id = line_id
                    segment_num = 1
                else:
                    segment_num += 1
                data.append([line_id] + parts[2].strip().split() + [parts[3]] + [segment_num])  # Add segment_num to data

        df_netfield_segments = pd.DataFrame(data, columns=columns)
        df_netfield_segments = df_netfield_segments.rename(columns={'line': 'Line', 'segment_num': 'Segment_num'})
        return df_netfield_segments
    
    def _netfield_transit_lines_to_df(self):
        data = []
        with open(self.netfield_transit_lines_file, 'r') as file:
            # Skip lines until the end of the header
            while True:
                line = file.readline()
                if line.startswith('end network_fields'):
                    break
            
            # The next line contains the column names
            columns = file.readline().strip().split()
            for line in file.readlines():
                parts = re.split("'\s+'", line.strip())
                data.append([part.strip("'").strip() for part in parts])  # Add segment_num to data
            
        # Read the rest of the file into a DataFrame
        df_netfield_transit_lines = pd.DataFrame(data, columns=columns)
        return df_netfield_transit_lines
    
    
    def extra_transit_lines_to_df(self):
        with open(self.extra_transit_lines_file, 'r') as file:
            # Skip lines until the end of the header
            while True:
                line = file.readline()
                if line.startswith('end extra_attributes'):
                    break
            
            # The next line contains the column names
            columns = file.readline().strip().split()
            columns[0] = 'Line'
            rows = []
            for line in file.readlines():
                sections = line.split()
                linenum = sections[0].strip("'").strip()
                try:
                    aht, pt, iht = sections[2:]
                except ValueError:
                    aht, pt, iht = sections[1:]
                rows.append([linenum, aht, pt, iht])
            
            # Read the rest of the file into a DataFrame
            df_headways = pd.DataFrame(rows, columns=columns)
        return df_headways
    
    def transit(self):
        segments, transit_lines, stops = self.parse_transit()
        transit_network = TransitNetwork(segments, transit_lines, stops)
        transit_network.project_name = self.project_name
        transit_network.scenario_name = self.scenario_name
        return transit_network


    def parse_transit(self):
        with open(self.transit_lines_file, 'r') as file:
            lines = file.readlines()
        
        # Read the extra attributes file, skipping the lines before the column names
        df_headways = self.extra_transit_lines_to_df()

        # Identifiers for the start of each transit line
        transit_line_header = "a'"
        transit_line_route = "path="
        transit_line_end = "c '"

        # Dictionary to hold the lines for each transit line
        transit_lines = []
        transit_line_routes = {}
        transit_line_stops = {}
        transit_lines_data = []

        # Flags to identify which part we're currently reading
        reading_transit_routes = False

        # Temporary variables to hold data
        current_line_code = None
        single_route = []

        # Process each line in the file
        for line in lines:
            if transit_line_header in line: # Get the line header for the current transit line
                current_line_code = str(line.split("'")[1]).strip()
                direction = current_line_code[-1]
                parts = line.split()
                mod, veh, headwy, speed = parts[1:5]
                description = ' '.join(parts[5:-3]).strip("'")
                data1, data2, data3 = map(float, parts[-3:])
            elif transit_line_route in line: # Start reading the route for the current transit line
                reading_transit_routes = True
                single_route = []  # Reset the route list for a new transit line
                single_route_numbers = []
                continue
            elif transit_line_end in line and current_line_code: # Save the route data for the transit line
                first_dwt = line.split('dwt=')[1].split()[0]  # Extract first_dwt
                transit_lines.append([current_line_code, direction, mod, int(veh), float(headwy), float(speed), description, data1, data2, data3, first_dwt])
                route_stops, transit_lines_data = self.separate_route_links(single_route, transit_lines_data, current_line_code)
                transit_line_routes[current_line_code] = [self.node_dict[int(node_id)] for node_id in single_route_numbers]
                transit_line_stops[current_line_code] = [self.node_dict[int(node_id)] for node_id in route_stops]
                reading_transit_routes = False
                current_line_code = None  # Reset the line code for the next transit line
                direction = None
            # If no other indicators are found, we're between header and end, or reading the route data
            if reading_transit_routes and line and not (line.startswith(transit_line_route) or line.startswith(transit_line_end)):
                node_id = int(line.split()[0])
                single_route_numbers.append(node_id)
                single_route.append(line)  # Add the route data, skipping the identifier line
            
        df_routes = pd.DataFrame(transit_lines_data, columns=['Line', 'Segment_num', 'From', 'To', 'dwt', 'lay', 'ttf', 'us1', 'us2', 'us3', 'geometry'])

        df_transit_lines = pd.DataFrame(transit_lines, columns=['Line', 'Direction', 'Mod', 'Veh', 'Headwy', 'Speed', 'Description', 'Data1', 'Data2', 'Data3', 'first_dwt'])
        if self.netfield_transit_lines_file:
            df_netfield_transit_lines = self._netfield_transit_lines_to_df()
            df_transit_lines_with_geom = df_transit_lines.merge(df_netfield_transit_lines, left_on="Line", right_on='line', how='left')
        else:
            df_transit_lines_with_geom = df_transit_lines.copy()
        
        df_transit_stops = df_transit_lines.copy()
        df_transit_stops['geometry'] = df_transit_stops['Line'].map(lambda x: MultiPoint(transit_line_stops.get(x, [])))
        df_transit_lines_with_geom['geometry'] = df_transit_lines_with_geom['Line'].map(lambda x: LineString(transit_line_routes.get(x, [])))
        df_transit_lines_with_geom = pd.merge(df_transit_lines_with_geom, df_headways, on="Line", how='left')

        df_routes.set_index(['Line', 'Segment_num'], inplace=True)
        df_transit_lines.set_index('Line', inplace=True)
        combined_gdf = df_routes.merge(df_transit_lines, left_index=True, right_index=True, how='left')
        if self.extra_segments_file:
            df_extra_segments = self._extra_segments_to_df().drop(columns=['inode', 'jnode'])
            df_extra_segments.set_index(['Line', 'Segment_num'], inplace=True)
            combined_gdf = combined_gdf.merge(df_extra_segments, left_index=True, right_index=True, how='left')
            combined_gdf = combined_gdf.drop(columns=['loop_idx_y'])

        
        if self.netfield_segments_file:
            df_netfield_segments = self._netfield_segments_to_df().drop(columns=['inode', 'jnode'])
            df_netfield_segments.set_index(['Line', 'Segment_num'], inplace=True)
            combined_gdf = combined_gdf.merge(df_netfield_segments, left_index=True, right_index=True, how='left')        

        # Convert the DataFrames to GeoDataFrames
        transit_segments_gdf = gpd.GeoDataFrame(combined_gdf, crs='EPSG:3879')  # Full data, each segment of each line
        transit_lines_gdf = gpd.GeoDataFrame(df_transit_lines_with_geom, geometry="geometry", crs='EPSG:3879')  # Complete routes of each line
        stops_gdf = gpd.GeoDataFrame(df_transit_stops, geometry='geometry', crs='EPSG:3879')  # Stops of each line as a MultiPoint

        return transit_segments_gdf, transit_lines_gdf, stops_gdf
    

    def separate_route_links(self, single_route, transit_lines_data, current_line_code):
        route_stops = []
        stop_flag = False
        route_length = len(single_route)
        segment_number = 0
        for i, turn in enumerate(single_route):
            segment_number += 1
            # Extract the node id and its data
            node_data = turn.split()
            node_id = int(node_data[0])
            dwt = node_data[1].split('=')[1]
            if stop_flag == True or i == 0:
                route_stops.append(node_id)
                stop_flag = False
            if dwt == '+0.01':
                stop_flag = True
            
            try:
                ttf, us1, us2, us3 = [data.split('=')[1] for data in node_data[2:6]]
                lay = None
            except ValueError:
                lay = dwt

            # Get the Point for the current node
            current_point = self.node_dict[node_id]
            # Check if there's a next node in the list
            if i < route_length - 1:
                next_node_id = int(single_route[i + 1].split()[0])
                next_point = self.node_dict[next_node_id]
                geometry = LineString([current_point, next_point])
            else:
                # If there's no next node, create a Point geometry
                next_node_id = 0
                geometry = current_point

            # Append the extracted data to the transit_lines_data list
            transit_lines_data.append([current_line_code, segment_number, node_id, next_node_id, dwt, lay, ttf, us1, us2, us3, geometry])
        
        return route_stops, transit_lines_data
    
    # Import additional files

    def import_link_shape(self):
        if self.link_shape_file:
            with open(self.link_shape_file, 'r') as file:
                lines = file.readlines()
            try:
                columns = lines[6].strip().split()
                data = [line.strip().split() for line in lines[7:]]
                df_link_shape = pd.DataFrame(data, columns=columns, sep=r'\s+')
                return df_link_shape
            except IndexError:
                return None
        else:
            return None

    def import_modes(self):
        if self.modes_file:
            with open(self.modes_file, 'r') as file:
                lines = file.readlines()
            columns = lines[5].strip().split()
            data = []
            for line in lines[6:]:
                parts = line.strip().split("'")
                marker, id = parts[0].strip().split()
                description = f"'{parts[1]}'"
                rest = parts[2].strip().split()
                mode_type = rest[0]
                colour = rest[1]
                cost_time_coeff = rest[2] if len(rest) > 2 else None
                cost_distance_coeff = rest[3] if len(rest) > 3 else None
                energy_time_coeff = rest[4] if len(rest) > 4 else None
                energy_distance_coeff = rest[5] if len(rest) > 5 else None
                speed_factor = rest[6] if len(rest) > 6 else None
                data.append([marker, id, description, mode_type, colour, cost_time_coeff, cost_distance_coeff, energy_time_coeff, energy_distance_coeff, speed_factor])
            df_modes = pd.DataFrame(data, columns=columns)
            return df_modes
        else:
            return None

    def import_turns(self):
        if self.turns_file:
            with open(self.turns_file, 'r') as file:
                lines = file.readlines()
            columns = lines[5].strip().split()
            data = [line.strip().split() for line in lines[6:]]
            df_turns = pd.DataFrame(data, columns=columns)
            return df_turns
        else:
            return None

    def import_vehicles(self):
        if self.vehicles_file:
            with open(self.vehicles_file, 'r') as file:
                lines = file.readlines()
            columns = lines[5].strip().split()
            data = [line.strip().split() for line in lines[6:]]
            df_vehicles = pd.DataFrame(data, columns=columns)
            return df_vehicles
        else:
            return None

def get_emme_scenario(scenario_directory: str) -> EmmeScenario:
    scenario_reader = ScenarioReader(scenario_directory)
    return scenario_reader.scenario()