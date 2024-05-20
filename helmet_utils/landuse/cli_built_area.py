import argparse
import json
from built_area import BuiltArea
from pathlib import Path

def get_data():
    parser = argparse.ArgumentParser(description='Recalculate built area of zones.')
    parser.add_argument('-a', '--area_changes', type=json.loads, help='dictionary describing area changes')
    parser.add_argument('-l', '--landuse', help='filepath of the original .lnd file')
    parser.add_argument('-c', '--landcover', help='filepath of the landcover file to be used in calculating the built area')
    parser.add_argument('-z', '--zones', help='filepath of the shapefile representing the zones')
    parser.add_argument('-y', '--year', type=int, help='year of the examination in question', default=2024)
    args = parser.parse_args()

    # Initialize a dictionary to hold area changes
    area_changes = args.area_changes if args.area_changes else {}

    # Gather file paths from arguments or user input
    landuse = Path(args.landuse) if args.landuse else Path(input("Enter filepath of the original .lnd file: "))
    landcover = Path(args.landcover) if args.landcover else Path(input("Enter filepath of the landcover file to be used in calculating the built area: "))
    zones = Path(args.zones) if args.zones else Path(input("Enter filepath of the shapefile representing the zones: "))

    # If area_changes is not provided, prompt the user to input them
    if not area_changes:
        while True:
            key = input("Enter original zone id: ")
            values = input("Enter new zone ids separated by commas: ")
            area_changes[int(key)] = [int(v) for v in values.split(',')]
            if input("Do you want to add more area_changes? (y/n): ").lower() != 'y':
                break

    # Return all gathered data
    return area_changes, landuse, landcover, zones, args.year

def main():
    area_changes, landuse, landcover, zones, year = get_data()
    built_area = BuiltArea(landuse, landcover, zones, year, area_changes)
    built_area.calculate()

if __name__ == '__main__':
    main()