import osmnx as ox

G = ox.graph.graph_from_place(
    query="Ilocos Norte, Philippines",
    network_type="all_public",
    simplify=True,
    truncate_by_edge=True,
)

ox.io.save_graphml(G, "assets/ilocos_norte_osmnx.graphml")
