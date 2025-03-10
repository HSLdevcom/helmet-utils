# helmet-utils

Repository for the processing and adjusting of data used by Helmet. Can be used as a Python library, or through the command line. 

Can be used to add height data to an Emme/Helmet network, which requires a Maanmittauslaitos API key from: https://www.maanmittauslaitos.fi/rajapinnat/api-avaimen-ohje

Landuse functions are still a work in progress, and they cannot currently be used through the command line interface. Most of the work for recalculating the .lnd file has been completed, but 

## Installation

You can install the package directly from the GitHub repository using pip:

```sh
pip install git+https://github.com/HSLdevcom/helmet-utils.git
```

## Usage as a Python Library

To use `helmet_utils` as a Python library, you can import the necessary classes and functions in your Python script

Adding height data to a network:

```python
from helmet_utils.network import scenario_reader

API_KEY = 'your_api_key'

def main():
    # Initialize the ScenarioReader with the path to your scenario directory
    scenario = scenario_reader.get_emme_scenario('path/to/scenario_directory')

    # Perform operations on the scenario, such as adding gradients
    scenario.add_gradients(api_key=API_KEY, processors=4)  # Currently supports 2 or 4 processors
    scenario.export('output_folder')

# When writing gradients to a network, you must protect your code like this
if __name__ == "__main__":
    main()
```

You can access the road or transit networks as GeoDataFrame -like objects. Here is how you can print information about centroids:

```python
from helmet_utils.network import scenario_reader

def main():
    # Initialize the ScenarioReader with the path to your scenario directory
    scenario = scenario_reader.get_emme_scenario('path/to/scenario_directory')

    # Get the network and transit objects
    network = scenario.network
    transit = scenario.transit

    # Print the total number, and the attributes of the first 10 centroids
    print(len(network.centroids))
    print(network.centroids.head(10))

# Doing this is good practice even when not required
if __name__ == "__main__":
    main()

```

You can easily add automatic traffic counts to the network. The aht and iht values are calculated as the mean maximum full hour traffic counts (7:00 to 8:00 or 8:00 to 9:00 for aht, whichever is larger) multiplied by 1.2. This is because FinTraffic's historical data only includes full hours. This could be fixed by processing the raw data.

```python
from helmet_utils.network import scenario_reader

def main():
    # Initialize the ScenarioReader with the path to your scenario directory
    scenario = scenario_reader.get_emme_scenario('path/to/scenario_directory')

    # Get the network and transit objects
    network = scenario.network

    network.add_lam_data()
    network.export_extra_links('output_folder')
    network.export_netfield_links('output_folder')

if __name__ == "__main__":
    main()

```

It is also possible to recalculate zone input data based on predrawn zone geometries and landcover raster data. The zonedata operations require an installation of rasterio and rasterstats. The installation of these libraries can be tricky, but you can contact the maintainer of this helmet-utils for help if needed.

A user can split existing zones into new ones using a GIS program, specifying the SIJ2023 parameter according to the centroids that are added to the network. The modified zones can then be used to recalculate landuse data. Population data is also adjusted according to landuse information, but should be manually adjusted afterwards.


```python
from helmet_utils.network import scenario_reader

def main():
    zonedata = zonedata_reader.get_helmet_zonedata("2023", "redrawn_zones.gpkg")
    zonedata.recalculate_zonedata(output_path="2023_new", area_changes={292:[292, 295]}, split_areas=False)

if __name__ == "__main__":
    main()

```

Optionally, you can let the program redraw zone geometries automatically from added centroids

```python
from helmet_utils.network import scenario_reader

def main():
    zonedata = zonedata_reader.get_helmet_zonedata("2023")
    zonedata.recalculate_zonedata(output_path="2023_new", split_areas=True, network_folder="scenario/folder/with/added/centroids")

if __name__ == "__main__":
    main()

```



## Usage through the Command Line

You can also use `helmet_utils` through the command line, although some features are currently not available. The command line interface is a work in progress and is not thoroughly tested. Contributions are very welcome!

The following command adds height data to the network:

```sh
python -m helmet_utils add_height --scenario_folder path/to/scenario_folder --api_key your_api_key --processors 4 --output_folder output_folder
```

The following command recalculates zonedata based on provided inputs:

```sh
python -m helmet_utils recalculate_zonedata --zonedata_folder path/to/zonedata_folder --output_folder output_folder --zones path/to/zones.gpkg --area_changes "{1:[1,4,5], 2:[2,3]}"
```

Or, to split zones automatically based on the locations of added centroids:

```sh
python -m helmet_utils recalculate_zonedata --zonedata_folder path/to/zonedata_folder --output_folder output_folder --scenario_folder path/to/scenario_folder --split_zones
```

### Command Line Arguments

#### `add_height` Command

- `--scenario_folder`: Path to the exported EMME scenario/network folder.
- `--api_key`: Maanmittauslaitos API key for reading height data.
- `--processors`: Number of processors to use (default is 2).
- `--output_folder`: Folder to save the updated network (optional).

#### `recalculate_zonedata` Command

- `--zonedata_folder`: Path to the original zonedata folder for a specific year.
- `--output_folder`: Folder to save the recalculated zonedata (optional).
- `--zones`: Path to a .gpkg file with split zone geometries (required for manual splitting).
- `--area_changes`: Area changes in dictionary format, e.g., `"{1:[1,4,5], 2:[2,3]}"` (required for manual splitting).
- `--scenario_folder`: Path to the exported EMME scenario/network folder with added centroids (required for automatic splitting).
- `--split_zones`: Flag to split zones based on the locations of the added centroids (required for automatic splitting).

For more information on the available commands and options, run:

```sh
python -m helmet_utils --help
```
## Feature Requests and Support

We welcome feature requests and suggestions! Please submit your requests by opening an issue on our GitHub repository:

[https://github.com/HSLdevcom/helmet-utils/issues](https://github.com/HSLdevcom/helmet-utils/issues)

Alternatively, you can contact us via email.


