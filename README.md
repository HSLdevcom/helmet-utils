# helmet-utils

Repository for the processing and adjusting of data used by Helmet. Can be used as a Python library, or throught the command line.

Can be used to add height data to an Emme/Helmet network, which requires a Maanmittauslaitos API key from: https://www.maanmittauslaitos.fi/rajapinnat/api-avaimen-ohje

## Installation

You can install the package directly from the GitHub repository using pip:

```sh
pip install git+https://github.com/HSLdevcom/helmet-utils.git
```

## Usage as a Python Library

To use `helmet_utils` as a Python library, you can import the necessary classes and functions in your Python script

Adding height data to a network:

```python
from helmet_utils.network.scenario_reader import ScenarioReader

# Initialize the ScenarioReader with the path to your scenario directory
scenario_reader = ScenarioReader('path/to/scenario_directory')

# Get the scenario object
scenario = scenario_reader.scenario()

# Perform operations on the scenario
scenario.add_gradients(api_key='your_api_key', processors=4)
scenario.export('output_folder')
```

You can access the road or transit networks as GeoDataFrame -like objects. Here is how you can print information about centroids:

```python
from helmet_utils.network.scenario_reader import ScenarioReader

# Initialize the ScenarioReader with the path to your scenario directory
scenario_reader = ScenarioReader('path/to/scenario_directory')

# Get the scenario object
scenario = scenario_reader.scenario()

# Get the network and transit objects
network = scenario.network
transit = scenario.transit

# Print the total number, and the attributes of the first 10 centroids
print(len(network.centroids))
print(network.centroids.head(10))


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

## Feature Requests

We welcome feature requests and suggestions! Please submit your requests by opening an issue on our GitHub repository:

[https://github.com/HSLdevcom/helmet-utils/issues](https://github.com/HSLdevcom/helmet-utils/issues)

Alternatively, you can contact us via email.


