from Scripts.network import network_reader

# Create a NetworkReader object
reader = network_reader.NetworkReader("Examples/Data/Scenario_1")

# Output network object
network = reader.network()

# Work with network
# return all centroids
centroids = network.centroids

# Display entire network
network.visualize(visualization_type="all", column='is_connector', cmap='coolwarm')
