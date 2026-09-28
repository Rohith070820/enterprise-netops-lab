"""Phase 2, Task 3: single points of failure and blast radius.

A single point of failure (SPOF) is a device or link whose failure
disconnects someone. Blast radius is WHO gets disconnected, and from WHAT.
"""
import networkx as nx

from netops.topology import SERVERS, build_campus, nodes_in_layer

# Which server each department's users need. Guest, IoT and Wireless only need the internet.
DEPT_SERVER = {dept: srv for srv, dept in SERVERS.items()}
INFRA_LAYERS = {"edge", "core", "distribution", "access"}


def single_points_of_failure(g: nx.Graph) -> list[str]:
    """Infrastructure devices whose loss splits the network in two (graph articulation points)."""
    return sorted(n for n in nx.articulation_points(g) if g.nodes[n]["layer"] in INFRA_LAYERS)


def critical_links(g: nx.Graph) -> list[tuple[str, str]]:
    """Links between infrastructure devices with no backup path (graph bridges)."""
    return sorted(
        tuple(sorted((a, b))) for a, b in nx.bridges(g)
        if g.nodes[a]["layer"] in INFRA_LAYERS | {"wan"} and g.nodes[b]["layer"] in INFRA_LAYERS | {"wan"}
    )


def blast_radius(g: nx.Graph, failed_device: str) -> dict[str, list[str]]:
    """For each user device, what it loses if failed_device goes down."""
    broken = g.copy()
    broken.remove_node(failed_device)
    impact = {}
    for user in nodes_in_layer(g, "endpoint"):
        lost = []
        if not nx.has_path(broken, user, "INTERNET"):
            lost.append("internet")
        server = DEPT_SERVER.get(g.nodes[user]["dept"])
        if server and (server == failed_device or not nx.has_path(broken, user, server)):
            lost.append(server)
        if lost:
            impact[user] = lost
    return impact


if __name__ == "__main__":
    g = build_campus()
    print("Single points of failure:", ", ".join(single_points_of_failure(g)))
    print("Critical links:          ", ", ".join(f"{a}<->{b}" for a, b in critical_links(g)))

    print("\nBlast radius if each infrastructure device fails:")
    devices = [n for n in g if g.nodes[n]["layer"] in INFRA_LAYERS]
    def severity(d):  # rank by total connections lost, then by users affected
        impact = blast_radius(g, d)
        return (-sum(len(lost) for lost in impact.values()), -len(impact), d)

    for device in sorted(devices, key=severity):
        impact = blast_radius(g, device)
        lost_total = sum(len(lost) for lost in impact.values())
        print(f"  {device:<9} {len(impact)} users affected, {lost_total} connections lost")
        for user, lost in impact.items():
            print(f"             - {user} loses {', '.join(lost)}")