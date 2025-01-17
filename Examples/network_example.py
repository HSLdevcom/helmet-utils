from helmet_utils.network import scenario_reader

# Create a ScenarioReader object
reader = scenario_reader.ScenarioReader("Examples/Data/Scenario_1")

# Output network object
network = reader.scenario().network

# Work with network
# return all centroids
centroids = network.centroids

# Display entire network
network.visualize(visualization_type="all", column='is_connector', cmap='coolwarm')
