from .emme_network import EmmeNetwork
from .transit_network import TransitNetwork
import os

class EmmeScenario:
    def __init__(self, network: EmmeNetwork, transit: TransitNetwork, input_folder: str, project_name: str, scenario_name: str):
        self.network = network
        self.transit = transit
        self.input_folder = input_folder
        self.project_name = project_name
        self.scenario_name = scenario_name

    def add_gradients(self, api_key, processors, in_place=False):
        self.network.add_gradients(api_key, processors, in_place)

    def export(self, output_folder=None, project_name=None, scenario_name=None):
        if output_folder is None:
            input_folder_name = os.path.basename(self.input_folder)
            output_folder = f"updated_{input_folder_name}"
        os.makedirs(output_folder, exist_ok=True)
        
        project_name = project_name or self.project_name
        scenario_name = scenario_name or self.scenario_name
        
        self.network.export_base_network(output_folder, project_name=project_name, scen_name=scenario_name)
        self.network.export_extra_links(output_folder)
        self.network.export_extra_nodes(output_folder)
        self.transit.export_transit_lines(output_folder)
        self.transit.export_extra_transit_lines(output_folder)
