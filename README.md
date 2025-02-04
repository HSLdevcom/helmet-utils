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

def main():
    # Initialize the ScenarioReader with the path to your scenario directory
    scenario = scenario_reader.get_emme_scenario('path/to/scenario_directory')

    # Perform operations on the scenario, such as adding gradients
    scenario.add_gradients(api_key='your_api_key', processors=4)  # Currently supports 2 or 4 processors
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


## Usage through the Command Line

You can also use `helmet_utils` through the command line. The following command adds height data to the network:

```sh
python -m helmet_utils.cli network add-height path/to/scenario_folder --api-key your_api_key --processors 4 --output-folder output_folder
```

### Command Line Arguments

- `scenario_folder`: Path to the exported EMME scenario/network folder.
- `--api-key`: Maanmittauslaitos API key for reading height data.
- `--processors`: Number of processors to use (default is 2).
- `--output-folder`: Folder to save the updated network (optional).

For more information on the available commands and options, run:

```sh
python -m helmet_utils.cli --help
```

## Feature Requests and Support

We welcome feature requests and suggestions! Please submit your requests by opening an issue on our GitHub repository:

[https://github.com/HSLdevcom/helmet-utils/issues](https://github.com/HSLdevcom/helmet-utils/issues)

Alternatively, you can contact us via email.


