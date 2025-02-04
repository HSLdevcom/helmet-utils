from .emme_network import EmmeNetwork
from .transit_network import TransitNetwork

import pandas as pd
import os
import csv
from pathlib import Path
from datetime import datetime
from tabulate import tabulate


class EmmeScenario:
    def __init__(self, network: EmmeNetwork, transit: TransitNetwork, input_folder: str, project_name: str, scenario_name: str, link_shape: pd.DataFrame=None, modes=None, turns=None, vehicles=None):
        self.network = network
        self.transit = transit
        self.input_folder = input_folder
        self.project_name = project_name
        self.scenario_name = scenario_name
        self.link_shape = link_shape
        self.modes = modes
        self.turns = turns
        self.vehicles = vehicles

    def add_gradients(self, api_key, processors=2, elevation_fixes=None, full=True):
        if api_key is None:
            raise ValueError("Please provide a valid Maanmittauslaitos API key")
        if elevation_fixes is None:
            elevation_fixes = Path(__file__).resolve().parent.parent / 'data' / 'elevation_fixes.csv'
        self.network = self.network.add_gradients(api_key, processors, elevation_fixes=elevation_fixes, full=full)

    def export_link_shape(self, output_folder, project_name='default_project', scen_number='1', scen_name='default_scenario', export_datetime=None):
        os.makedirs(output_folder, exist_ok=True)  # Ensure the output folder exists
        current_date = export_datetime if export_datetime else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_path = Path(output_folder) / f"link_shape_{scen_number}.txt"
        with open(output_path, 'w') as f:
            f.write(f"c Modeller - Link Shape Transaction\nc Date: {current_date}\nc Project: {project_name}\nc Scenario {scen_number}: {scen_name}\nc I_Node J_Node Vertex_No. X-Coord Y-Coord\nt linkvertices\n")
            if self.link_shape is not None:
                self.link_shape.to_csv(f, index=False, sep=' ', header=False)
    
    def export_modes(self, output_folder, project_name='default_project', scen_number='1', scen_name='default_scenario', export_datetime=None):
        os.makedirs(output_folder, exist_ok=True)  # Ensure the output folder exists
        current_date = export_datetime if export_datetime else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_path = Path(output_folder) / f"modes_{scen_number}.txt"
        with open(output_path, 'w') as f:
            f.write(f"c Modeller - Mode Transaction\nc Date: {current_date}\nc Project: {project_name}\nc Scenario {scen_number}: {scen_name}\nt modes\n")
            if self.modes is not None:
                self.modes.to_csv(f, index=False, sep=' ', lineterminator='\n', quoting=csv.QUOTE_NONE, escapechar=' ') # TODO Fix weird double quotes around descriptions with two words

    # TODO: Perhaps integrate to EmmeNetwork
    def export_turns(self, output_folder, project_name='default_project', scen_number='1', scen_name='default_scenario', export_datetime=None):
        os.makedirs(output_folder, exist_ok=True)  # Ensure the output folder exists
        current_date = export_datetime if export_datetime else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_path = Path(output_folder) / f"turns_{scen_number}.txt"
        with open(output_path, 'w') as f:
            f.write(f"c Modeller - Turn Transaction\nc Date: {current_date}\nc Project: {project_name}\nc Scenario {scen_number}: {scen_name}\nt turns\n")
            if self.turns is not None:
                self.turns.to_csv(f, index=False, sep=' ', lineterminator='\n')

    # TODO: Perhaps integrate to TransitNetwork
    def export_vehicles(self, output_folder, project_name='default_project', scen_number='1', scen_name='default_scenario', export_datetime=None):
        os.makedirs(output_folder, exist_ok=True)  # Ensure the output folder exists
        current_date = export_datetime if export_datetime else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_path = Path(output_folder) / f"vehicles_{scen_number}.txt"
        with open(output_path, 'w') as f:
            f.write(f"c Modeller - Vehicle Transaction\nc Date: {current_date}\nc Project: {project_name}\nc Scenario {scen_number}: {scen_name}\nt vehicles\n")
            if self.vehicles is not None:
                self._to_fwf(self.vehicles, f)

    def export(self, output_folder=None, project_name=None, scenario_name=None):
        print("Exporting network to Emme format... Please copy and paste the transit files manually for now.")
        export_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if output_folder is None:
            input_folder_name = os.path.basename(self.input_folder)
            output_folder = f"updated_{input_folder_name}"
        os.makedirs(output_folder, exist_ok=True)
        
        if not project_name:
            project_name = self.project_name
        if not scenario_name:
            scenario_name = self.scenario_name
        
        # Export network files
        self.network.export_base_network(output_folder, project_name=project_name, scen_name=scenario_name, export_datetime=export_datetime)
        self.network.export_extra_links(output_folder)
        self.network.export_extra_nodes(output_folder)
        self.network.export_netfield_links(output_folder)
        # Export the Scenario specific files
        self.export_link_shape(output_folder, project_name=project_name, scen_name=scenario_name, export_datetime=export_datetime)
        self.export_modes(output_folder, project_name=project_name, scen_name=scenario_name, export_datetime=export_datetime)
        self.export_turns(output_folder, project_name=project_name, scen_name=scenario_name, export_datetime=export_datetime)
        self.export_vehicles(output_folder, project_name=project_name, scen_name=scenario_name, export_datetime=export_datetime)
        # Export transit lines
        self.transit.export_transit_lines(output_folder, export_datetime=export_datetime)
        self.transit.export_extra_transit_lines(output_folder)
        self.transit.export_netfield_transit_lines(output_folder)
        self.transit.export_segments(output_folder)
        # self.transit.export_netfield_segments(output_folder)
        # self.transit.export_extra_segments(output_folder)
    
    def _to_fwf(self, df, file):
        content = tabulate(df.values.tolist(), list(df.columns), tablefmt="plain", disable_numparse=True)
        # Adjust formatting to match the original file
        # content = content.replace("  ", " ").replace(" \n", "\n")
        file.write(content)
