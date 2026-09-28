"""Phase 2: the campus network as a graph.

Nodes are devices (routers, switches, endpoints, servers).
Edges are cables (links), each with a capacity in Mbps.
"""
import networkx as nx

# Which department each endpoint and server belongs to (VLANs come in Phase 3).
ENDPOINTS = {
    "ACCESS-1": {"hr-pc-1": "HR", "fin-pc-1": "Finance", "ap-1": "Wireless"},
    "ACCESS-2": {"eng-pc-1": "Engineering", "iot-cam-1": "IoT", "guest-1": "Guest"},
}
SERVERS = {"eng-srv": "Engineering", "fin-srv": "Finance", "hr-srv": "HR"}


def build_campus() -> nx.Graph:
    g = nx.Graph()

    # --- Infrastructure devices, one per layer of the design ---
    g.add_node("INTERNET", role="internet", layer="wan")
    g.add_node("EDGE", role="router", layer="edge")
    g.add_node("CORE", role="switch", layer="core")
    for d in ("DIST-1", "DIST-2"):
        g.add_node(d, role="switch", layer="distribution")
    for a in ENDPOINTS:
        g.add_node(a, role="switch", layer="access")

    # --- Links: the bigger the layer, the fatter the pipe ---
    g.add_edge("INTERNET", "EDGE", capacity_mbps=1_000, kind="wan")
    g.add_edge("EDGE", "CORE", capacity_mbps=10_000, kind="backbone")
    g.add_edge("CORE", "DIST-1", capacity_mbps=10_000, kind="backbone")
    g.add_edge("CORE", "DIST-2", capacity_mbps=10_000, kind="backbone")
    g.add_edge("DIST-1", "DIST-2", capacity_mbps=10_000, kind="backbone")
    # Every access switch is dual-homed: one uplink to EACH distribution switch.
    for a in ENDPOINTS:
        g.add_edge(a, "DIST-1", capacity_mbps=1_000, kind="uplink")
        g.add_edge(a, "DIST-2", capacity_mbps=1_000, kind="uplink")

    # --- Endpoints plug into access ports; servers hang off the core ---
    for switch, hosts in ENDPOINTS.items():
        for host, dept in hosts.items():
            g.add_node(host, role="endpoint", layer="endpoint", dept=dept)
            g.add_edge(host, switch, capacity_mbps=1_000, kind="access-port")
    for srv, dept in SERVERS.items():
        g.add_node(srv, role="server", layer="server", dept=dept)
        g.add_edge(srv, "CORE", capacity_mbps=10_000, kind="server-port")

    return g


def nodes_in_layer(g: nx.Graph, layer: str) -> list[str]:
    return sorted(n for n, data in g.nodes(data=True) if data["layer"] == layer)


if __name__ == "__main__":
    g = build_campus()
    print(f"Campus: {g.number_of_nodes()} nodes, {g.number_of_edges()} links\n")
    for layer in ("wan", "edge", "core", "distribution", "access", "endpoint", "server"):
        print(f"{layer:>12}: {', '.join(nodes_in_layer(g, layer))}")
    print("\nUplinks (access -> distribution):")
    for access in nodes_in_layer(g, "access"):
        for dist in nodes_in_layer(g, "distribution"):
            mbps = g.edges[access, dist]["capacity_mbps"]
            print(f"  {access} <-> {dist}  {mbps} Mbps")