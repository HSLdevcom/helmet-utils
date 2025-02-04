import argparse
from helmet_utils.network import scenario_reader

def add_height_data(scenario_folder: str, api_key: str, processors: int, output_folder: str = None, full: bool = True):
    # Read the network
    scenario = scenario_reader.get_emme_scenario(scenario_folder)
    network = scenario.network
    network.add_gradients(api_key, processors=processors, full=full)
    network.export_extra_links(output_folder=output_folder)
    network.export_extra_nodes(output_folder=output_folder)

    print(f"Height data added to network. Updated network saved to {output_folder or f'updated_{scenario_reader.input_folder}'}")

def main():
    parser = argparse.ArgumentParser(description="Helmet Utils CLI")
    subparsers = parser.add_subparsers(dest="operation")

    # Subparser for network operations
    parser_network = subparsers.add_parser("network", help="Network operations")
    parser_network.add_argument("action", choices=["add-height"], help="Action to perform on the network")
    parser_network.add_argument("scenario_folder", type=str, help="Path to the exported EMME scenario/network folder")
    parser_network.add_argument("--api-key", type=str, required=True, help="Maanmittauslaitos API key for reading height data (https://www.maanmittauslaitos.fi/rajapinnat/api-avaimen-ohje)")
    parser_network.add_argument("--processors", type=int, default=2, help="Number of processors to use, 2 or 4")
    parser_network.add_argument("--output-folder", type=str, help="Folder to save the updated network")

    # Subparser for landuse operations (not implemented)
    parser_landuse = subparsers.add_parser("landuse", help="Landuse operations")
    parser_landuse.set_defaults(func=lambda _: print("Landuse operations not implemented"))

    args = parser.parse_args()

    if args.operation == "network":
        if args.action == "add-height":
            add_height_data(args.scenario_folder, args.api_key, args.processors, args.output_folder)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()