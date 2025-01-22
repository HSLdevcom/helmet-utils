import webbrowser
from datetime import datetime
from pathlib import Path

class TransitNetwork():

    def __init__(self, segments, transit_lines, stops):
        self.transit_lines = transit_lines
        self.segments = segments
        self.stops = stops

    def export_transit(self):
        pass

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
        with open(output_path, 'w') as f:
            f.write(header)
            for line in self.transit_lines.itertuples():
                start_str = (
                    f"a'{line.Line}' {line.Mod}   {line.Veh}  {line.Headwy:.2f}  {line.Speed:.2f} "
                    f"'{line.Description}'      {line.Data1}      {line.Data2}      {line.Data3}\n"
                    "  path=no\n"
                )
                f.write(start_str)
                route_nodes = self.segments.loc[line.Line]
                for i, node in enumerate(route_nodes.itertuples()):
                    if i == len(route_nodes) - 1:
                        f.write(f"   {node.From}        lay={node.lay}\n")
                    else:
                        f.write(f"   {node.From}      dwt={node.dwt}   ttf={node.ttf}   us1={node.us1}   us2={node.us2}   us3={node.us3}\n")
                end_str = f"c '{line.Line}' first:      dwt={line.first_dwt} hidden:    us1=0   us2=0   us3=0\n"
                f.write(end_str)

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

    def export(self, output_folder):
        self.export_transit_lines(output_folder)
        self.export_extra_transit_lines(output_folder)

