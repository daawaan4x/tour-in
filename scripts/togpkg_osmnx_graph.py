import osmnx as ox

G = ox.load_graphml("assets/ilocos_norte_osmnx.graphml")

ox.save_graph_geopackage(G, "assets/ilocos_norte_osmnx.gpkg")
