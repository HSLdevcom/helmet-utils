import webbrowser
from datetime import datetime
from pathlib import Path

from tabulate import tabulate
import pandas as pd

class TransitNetwork():

    def __init__(self, segments, transit_lines, stops):
        self.transit_lines = transit_lines
        self.segments = segments
        self.stops = stops

    def modify_headways(self, lines, ahts=None, pts=None, ihts=None, inplace=False):

        # If lines is a single integer, convert it to a list
        if not isinstance(lines, list):
            lines = [lines]
        lines = [str(line) for line in lines]

        # If only one headway value is provided, apply it to all three headways
        if ahts is not None and pts is None and ihts is None:
            pts = ihts = ahts
        
        # If headways are provided as single float values, convert them to lists
        ahts = [ahts] * len(lines) if isinstance(ahts, float) else ahts
        pts = [pts] * len(lines) if isinstance(pts, float) else pts
        ihts = [ihts] * len(lines) if isinstance(ihts, float) else ihts
        
        if inplace:
            for line, aht, pt, iht in zip(lines, ahts, pts, ihts):
                self.transit_lines.loc[self.transit_lines['Line']==line, "@hw_aht"] = aht
                self.transit_lines.loc[self.transit_lines['Line']==line, "@hw_pt"] = pt
                self.transit_lines.loc[self.transit_lines['Line']==line, "@hw_iht"] = iht

        else:
            transit_lines_with_new_headway = self.transit_lines.copy()
            for line, aht, pt, iht in zip(lines, ahts, pts, ihts):
                transit_lines_with_new_headway.loc[self.transit_lines['Line']==line, "@hw_aht"] = aht
                transit_lines_with_new_headway.loc[self.transit_lines['Line']==line, "@hw_pt"] = pt
                transit_lines_with_new_headway.loc[self.transit_lines['Line']==line, "@hw_iht"] = iht
            return transit_lines_with_new_headway

    def visualize(self, visualization_type=None, direction=None, draw_stops=True):
        if not visualization_type:
            print("Visualization type must be specified with transit network.\n Valid choices: ['all','hsl','hsl-bus','bus','tram'], 'all' is not recommended due to issues with Folium.\n\n You can also manually visualize transit lines using the transit_lines.explore() and stops.explore() methods. ")
            return
        else:
            if visualization_type=='tram':
                if direction:
                    map = self.transit_lines[(self.transit_lines['Mod'].isin(['t','p'])) & (self.transit_lines['Direction'] == str(direction))].explore(column='Line')
                    if draw_stops:
                        self.stops[self.stops['Mod'].isin(['t','p']) & (self.stops['Direction'] == str(direction))].explore(m=map, column='Line', legend_kwds={'caption':'Stops'},  marker_kwds={'radius':5})
                else:
                    map = self.transit_lines[(self.transit_lines['Mod'].isin(['t','p']))].explore(column='Line')
                    if draw_stops:
                        self.stops[self.stops['Mod'].isin(['t','p'])].explore(m=map, column='Line', legend_kwds={'caption':'Stops'},  marker_kwds={'radius':5})

                    print('No direction specified, printing both directions. Readability can be improved by specifying line direction [1, 2].')
            elif visualization_type=='hsl-bus':
                if direction:
                    map = self.transit_lines[(self.transit_lines['Mod'].isin(['b'])) & (self.transit_lines['Direction'] == str(direction))].explore(color='blue')
                    self.transit_lines[(self.transit_lines['Mod'].isin(['g'])) & (self.transit_lines['Direction'] == str(direction))].explore(m=map, color='orange')
                    if draw_stops:
                        self.stops[self.stops['Mod'].isin(['b']) & (self.stops['Direction'] == str(direction))].explore(m=map, color='blue', legend_kwds={'caption':'Stops'},  marker_kwds={'radius':5})
                        self.stops[self.stops['Mod'].isin(['g']) & (self.stops['Direction'] == str(direction))].explore(m=map, color='orange', legend_kwds={'caption':'Stops'},  marker_kwds={'radius':5})
                else:
                    map = self.transit_lines[(self.transit_lines['Mod'].isin(['t','p','b','g','j']))].explore(column='Line')
                    if draw_stops:
                        self.stops[self.stops['Mod'].isin(['t','p','b','g','j'])].explore(m=map, column='Line', legend_kwds={'caption':'Stops'},  marker_kwds={'radius':5})

                    print('No direction specified, printing both directions. Readability can be improved by specifying line direction [1, 2].')

        map.save('map.html')
        webbrowser.open('map.html')

    # Export functions
    def export_transit_lines(self, output_folder, scen_number=1, export_datetime=None):
        current_date = export_datetime if export_datetime else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = (
            "c Modeller - Transit Line Transaction\n"
            f"c Date: {current_date}\n"
            f"c Project: {self.project_name}\n"
            f"c Scenario {scen_number}: {self.scenario_name}\n"
            "t lines\n"
            "c Transit Lines\n"
            "c Line  Mod Veh Headwy Speed Description             Data1  Data2  Data3\n"
        )

        output_path = Path(output_folder) / f"transit_lines_{scen_number}.txt"
        lines_content = [header]

        for line in self.transit_lines.itertuples():
            start_str = (
                f"a'{line.Line}' {line.Mod}   {line.Veh}  {line.Headwy:.2f}  {line.Speed:.2f} "
                f"'{line.Description}'      {line.Data1}      {line.Data2}      {line.Data3}\n"
                "  path=no\n"
            )
            lines_content.append(start_str)
            route_nodes = self.segments.loc[line.Line]
            for i, node in enumerate(route_nodes.itertuples()):
                if i == len(route_nodes) - 1:
                    lines_content.append(f"   {node.From}        lay={node.lay}\n")
                else:
                    lines_content.append(f"   {node.From}      dwt={node.dwt}   ttf={node.ttf}   us1={node.us1}   us2={node.us2}   us3={node.us3}\n")
            end_str = f"c '{line.Line}' first:      dwt={line.first_dwt} hidden:    us1=0   us2=0   us3=0\n"
            lines_content.append(end_str)

        with open(output_path, 'w') as f:
            f.writelines(lines_content)


    # TODO: rewrite in a more general way like EmmeNetwork functions
    def export_extra_transit_lines(self, output_folder, scen_number=1):
        to_be_printed = self.transit_lines[['Line', '@hw_aht', '@hw_pt', '@hw_iht']].copy()
        # Reformat line numbers to match emme format
        to_be_printed = to_be_printed.rename(columns={'Line':'line'})
        to_be_printed['line'] = to_be_printed['line'].apply(lambda num: f"'{str(num).ljust(6)}'")

        # Prepare export by creating the extra_attribute definitions read by EMME
        definition_string = "t extra_attributes\n@hw_aht TRANSIT_LINE 0.0 ''\n"\
                            +"@hw_pt TRANSIT_LINE 0.0 ''\n@hw_iht TRANSIT_LINE 0.0 ''\n"\
                            +"end extra_attributes\n"

        output_path = Path(output_folder) / f"extra_transit_lines_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            # Use to_string with formatters to ensure proper spacing and alignment
            f.write(to_be_printed.to_string(index=False, header=True, formatters={
            'line': '{:<8}'.format,
            '@hw_aht': '{:>9}'.format,
            '@hw_pt': '{:>9}'.format,
            '@hw_iht': '{:>9}'.format}))

    def export_segments(self, output_folder, scen_number=1):
        to_be_printed = self.segments.copy().reset_index()
        extra_columns = [col for col in to_be_printed.columns if '@' in col]
        netfield_columns = [col for col in to_be_printed.columns if '#' in col]
        
        if extra_columns:
            self._export_extra_segments(to_be_printed, output_folder, scen_number, extra_columns)
        if netfield_columns:
            self._export_netfield_segments(to_be_printed, output_folder, scen_number, netfield_columns)

    def _export_extra_segments(self, to_be_printed, output_folder, scen_number, extra_columns):
        to_be_printed = to_be_printed[['Line','From','To', 'loop_idx'] + extra_columns]
        to_be_printed = to_be_printed.rename(columns={'Line': 'line', 'From': 'inode', 'To': 'jnode'})
        to_be_printed['line'] = to_be_printed['line'].apply(lambda num: f"'{str(num).ljust(6)}'")

        definition_string = "t extra_attributes\n"
        for column_name in extra_columns:
            if column_name == '@wait_time_dev':
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'wait time st.dev.'\n"
            elif column_name == '@ccost':
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'congestion cost'\n"
            elif 'base_timtr' in column_name:
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'uncongested transit time'\n"
            elif 'transit_wor' in column_name:
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'transit_work {self._get_transit_description(column_name)}'\n"
            elif 'transit_lei' in column_name:
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'transit_leisure {self._get_transit_description(column_name)}'\n"
            else:
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 ''\n"
        definition_string += "end extra_attributes\n"

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)
        output_path = Path(output_folder) / f"extra_segments_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            f.write(formatted_df.to_string(index=None))

    def _export_netfield_segments(self, to_be_printed, output_folder, scen_number, netfield_columns):
        to_be_printed = to_be_printed[['Line','From','To', 'loop_idx'] + netfield_columns]
        to_be_printed = to_be_printed.rename(columns={'Line': 'line', 'From': 'inode', 'To': 'jnode'})
        to_be_printed['line'] = to_be_printed['line'].apply(lambda num: f"'{str(num).ljust(6)}'")

        definition_string = "t network_fields\n"
        for column_name in netfield_columns:
            definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 ''\n"
        definition_string += "end network_fields\n"

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)
        for column in netfield_columns:
            formatted_df[column] = formatted_df[column].apply(lambda x: f"'{x}'" if pd.notnull(x) else "''")

        formatted_df['jnode'] = formatted_df['jnode'].apply(lambda node: "None" if node=="0" else node)
        output_path = Path(output_folder) / f"netfield_segments_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            self._to_fwf(formatted_df, f)

    def export_extra_segments(self, output_folder, scen_number=1):
        to_be_printed = self.segments.copy().reset_index()
        # Check if columns with '@' exist, otherwise return None
        extra_columns = [col for col in to_be_printed.columns if '@' in col]
        if not extra_columns:
            return None
        
        to_be_printed = to_be_printed[['Line','From','To', 'loop_idx'] + extra_columns]
        to_be_printed = to_be_printed.rename(columns={'Line': 'line', 'From': 'inode', 'To': 'jnode'})
        
        # Reformat line numbers to match emme format
        to_be_printed['line'] = to_be_printed['line'].apply(lambda num: f"'{str(num).ljust(6)}'")

        # Prepare export by creating the extra_attribute definitions read by EMME
        definition_string = "t extra_attributes\n"
        for column_name in to_be_printed.columns:
            if column_name in ['line', 'inode', 'jnode', 'segment_num', 'loop_idx']:
                continue
            if column_name == '@wait_time_dev':
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'wait time st.dev.'\n"
            elif column_name == '@ccost':
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'congestion cost'\n"
            elif 'base_timtr' in column_name:
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'uncongested transit time'\n"
            elif 'transit_wor' in column_name:
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'transit_work {self._get_transit_description(column_name)}'\n"
            elif 'transit_lei' in column_name:
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 'transit_leisure {self._get_transit_description(column_name)}'\n"
            else:
                definition_string += f"{column_name} TRANSIT_SEGMENT 0.0 ''\n"
        definition_string += "end extra_attributes\n"

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)

        output_path = Path(output_folder) / f"extra_segments_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            f.write(formatted_df.to_string(index=None))

    def export_netfield_transit_lines(self, output_folder, scen_number=1):
        to_be_printed = self.transit_lines.copy()
        netfield_columns = [col for col in to_be_printed.columns if '#' in col]
        print(to_be_printed.columns)
        if not netfield_columns:
            return None
        to_be_printed = to_be_printed[['Line'] + netfield_columns]
        to_be_printed = to_be_printed.rename(columns={'Line':'line'})
        to_be_printed['line'] = to_be_printed['line'].apply(lambda num: f"'{str(num).ljust(6)}'")

        definition_string = "t network_fields\n"
        for column_name in to_be_printed.columns:
            if column_name == 'line':
                continue
            else:
                definition_string += f"{column_name} TRANSIT_LINE STRING ''\n"
                to_be_printed[column_name] = to_be_printed[column_name].apply(lambda x: f"'{x}'" if pd.notnull(x) else "''")
        definition_string += "end network_fields\n"

        output_path = Path(output_folder) / f"netfield_transit_lines_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            to_be_printed.to_string(f, index=None)
               
    def export_netfield_segments(self, output_folder, scen_number=1):
        to_be_printed = self.segments.copy().reset_index()
        # Check if columns with '@' exist, otherwise return None
        netfield_columns = [col for col in to_be_printed.columns if '#' in col]
        if not netfield_columns:
            return None
        
        to_be_printed = to_be_printed[['Line','From','To', 'loop_idx'] + netfield_columns]
        to_be_printed = to_be_printed.rename(columns={'Line': 'line', 'From': 'inode', 'To': 'jnode'})
        
        # Reformat line numbers to match emme format
        to_be_printed['line'] = to_be_printed['line'].apply(lambda num: f"'{str(num).ljust(6)}'")

        formatted_df = to_be_printed.map(lambda x: f'{x:g}' if isinstance(x, (int, float)) else x)
        # Prepare export by creating the extra_attribute definitions read by EMME
        definition_string = "t network_fields\n"
        for column_name in to_be_printed.columns:
            if column_name in ['line', 'inode', 'jnode', 'loop_idx']:
                continue
            else:
                definition_string += f"{column_name} TRANSIT_SEGMENT STRING ''\n"
                formatted_df[column_name] = formatted_df[column_name].apply(lambda x: f"'{x}'" if pd.notnull(x) else "''")
        definition_string += "end network_fields\n"

        formatted_df['jnode'] = formatted_df['jnode'].apply(lambda node: "None" if node=="0" else node)
        output_path = Path(output_folder) / f"netfield_segments_{scen_number}.txt"
        with open(output_path, 'a') as f:
            f.write(definition_string)
            self._to_fwf(formatted_df, f)

    def _get_transit_description(self, column_name):
        description_string = ''
        if 'vol' in column_name:
            description_string += 'transit_volumes'
        elif 'boa' in column_name:
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

    def export(self, output_folder):
        self.export_transit_lines(output_folder)
        self.export_extra_transit_lines(output_folder)

    def _to_fwf(self, df, file):
        content = tabulate(df.values.tolist(), list(df.columns), tablefmt="plain", disable_numparse=True)
        # Adjust formatting to match the original file
        # content = content.replace("  ", " ").replace(" \n", "\n")
        file.write(content)

