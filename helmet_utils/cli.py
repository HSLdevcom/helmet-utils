import argparse
import warnings
import json
from helmet_utils.network import scenario_reader
from helmet_utils.zonedata import zonedata_reader

# Suppress warnings caused by GeoPandas
warnings.filterwarnings("ignore", category=FutureWarning, module='numpy')


def add_height_data(scenario_folder: str, api_key: str, processors: int, output_folder: str = None, full: bool = True):
    # Read the network
    scenario = scenario_reader.get_emme_scenario(scenario_folder)
    network = scenario.network
    network.add_gradients(api_key, processors=processors, full=full)
    network.export_extra_links(output_folder=output_folder)
    network.export_extra_nodes(output_folder=output_folder)

    print(f"Height data added to network. Updated network saved to {output_folder or f'updated_{scenario_reader.input_folder}'}")

def recalculate_zone_data(zonedata_folder:str, split_areas:bool, area_changes=None, output_folder: str = None, network_folder:str = None, zones:str=None, landcover:str=None):
    zonedata = zonedata_reader.get_helmet_zonedata(zonedata_folder, zones_filepath=zones, landcover_filepath=landcover)
    # zonedata.recalculate_zonedata(output_path="2023_test_output", area_changes={292:[292, 295]}, split_areas=True)
    zonedata.recalculate_zonedata(output_path=output_folder, split_areas=split_areas, area_changes=area_changes, network_folder=network_folder)


def main():
    parser = argparse.ArgumentParser(description="Helmet Utils CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Subparser for adding height data to the network
    parser_add_height = subparsers.add_parser("add_height", help="Add height data to the network")
    parser_add_height.add_argument("-s", "--scenario_folder", type=str, required=True, help="Path to the exported EMME scenario/network folder")
    parser_add_height.add_argument("-a", "--api_key", type=str, required=True, help="Maanmittauslaitos API key for reading height data (https://www.maanmittauslaitos.fi/rajapinnat/api-avaimen-ohje)")
    parser_add_height.add_argument("-p", "--processors", type=int, default=2, help="Number of processors to use, 2 or 4")
    parser_add_height.add_argument("-o", "--output_folder", type=str, help="Folder to save the updated network")

    # Subparser for recalculating zonedata
    parser_recalculate_zonedata = subparsers.add_parser("recalculate_zonedata", help="Recalculate zonedata based on provided inputs")
    parser_recalculate_zonedata.add_argument("-z", "--zonedata_folder", type=str, required=True, help="Path to the original zonedata folder for a specific year")
    parser_recalculate_zonedata.add_argument("-o", "--output_folder", type=str, help="Folder to save the recalculated zonedata")
    # If the user wants to split zones, there are two possible methods, either splitting manually and passing in the split zone geometries and changes, or automatically splitting.
    # These two must be used together:
    parser_recalculate_zonedata.add_argument("--zones", type=str, help=".gpkg file with split zone geometries.")
    parser_recalculate_zonedata.add_argument("--area_changes", type=str, help="Area changes of the form '{1:[1,4,5], 2:[2,3]}', where 1 and 2 are the original zone numbers and the lists contain the new zones after splitting. Must represent changes in the zone geometry.")
    # Or these two must be used together, but not with the last two:
    parser_recalculate_zonedata.add_argument("--network_folder", type=str, help="Path to the exported EMME scenario with added centroids")
    parser_recalculate_zonedata.add_argument("--split_zones", action="store_true", help="Split zones based on the locations of the added centroids")

    args = parser.parse_args()

    if args.command == "add_height":
        add_height_data(args.scenario_folder, args.api_key, args.processors, args.output_folder)
    elif args.command == "recalculate_zonedata":
        if (args.zones and args.area_changes) and args.split_zones:
            print("Error: You cannot use both manual and automatic zone splitting methods at the same time.")
            return
        if not (args.zones and args.area_changes) and not args.split_zones:
            print("Error: You must provide either manual or automatic zone splitting information.")
            return
        area_changes = json.loads(args.area_changes) if args.area_changes else None
        recalculate_zone_data(
            zonedata_folder=args.zonedata_folder,
            split_areas=args.split_zones,
            area_changes=area_changes,
            output_folder=args.output_folder,
            network_folder=args.network_folder,
            zones=args.zones
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()