"""Phase 6, Task 1: Spanning Tree Protocol (simplified).

Redundant links between switches form LOOPS. Ethernet frames have no TTL, so a
broadcast caught in a loop circles forever and multiplies (a "broadcast storm").
STP prevents this by turning the switch network into a TREE:

1. Elect a ROOT bridge: lowest bridge ID = (priority, MAC). Admins set a low
   priority on the core so the right switch wins.
2. Every other switch picks its ROOT PORT: the port with the cheapest path to the root
   (1 Gbps link cost 4, 10 Gbps cost 2; ties go to the neighbor with the lower bridge ID).
3. Links used as root-port links FORWARD. Every other switch-to-switch link is BLOCKED.

If a forwarding link fails, STP recalculates and a blocked link takes over.
A switch with no path left to the root becomes the root of its own little "island".
We compute the RESULT of STP; we do not replay its timers or messages.
"""
import networkx as nx

from netops.topology import build_campus

BRIDGE_MAC = {  # an older access switch happens to have the lowest MAC
    "ACCESS-1": "02:00:00:99:00:02",
    "ACCESS-2": "02:00:00:99:00:03",
    "DIST-1": "02:00:00:99:00:04",
    "DIST-2": "02:00:00:99:00:05",
    "CORE": "02:00:00:99:00:06",
}
DEFAULT_PRIORITY = 32768
DESIGNED_PRIORITY = {"CORE": 4096, "DIST-1": 8192, "DIST-2": 8192}   # core = root on purpose
COST = {1_000: 4, 10_000: 2}                                        # STP path cost by link speed


def switch_graph(g: nx.Graph, failed: tuple[tuple[str, str], ...] = ()) -> nx.Graph:
    """Only switches take part in STP (routers and end devices do not)."""
    s = g.subgraph(n for n, d in g.nodes(data=True) if d["role"] == "switch").copy()
    s.remove_edges_from(failed)
    return s


def compute_stp(g: nx.Graph, priorities: dict[str, int] | None = None,
                failed: tuple[tuple[str, str], ...] = ()) -> dict:
    prio = DESIGNED_PRIORITY if priorities is None else priorities
    s = switch_graph(g, failed)
    bid = {n: (prio.get(n, DEFAULT_PRIORITY), BRIDGE_MAC[n]) for n in s}
    root = min(s, key=bid.get, default=None)

    for a, b in s.edges:
        s.edges[a, b]["cost"] = COST[s.edges[a, b]["capacity_mbps"]]

    root_ports, cut_off = {}, []
    for island in nx.connected_components(s):     # normally just one: the whole switch network
        island_root = min(island, key=bid.get)    # an island cut off from the root elects its own
        if root not in island:
            cut_off.extend(island)
        root_cost = nx.single_source_dijkstra_path_length(s, island_root, weight="cost")
        for bridge in island - {island_root}:
            best = min(s.neighbors(bridge), key=lambda n: (root_cost[n] + s.edges[bridge, n]["cost"], bid[n]))
            root_ports[bridge] = best

    forwarding = {tuple(sorted((b, n))) for b, n in root_ports.items()}
    blocked = {tuple(sorted(e)) for e in s.edges} - forwarding
    return {"root": root, "bridge_id": bid, "root_ports": root_ports,
            "forwarding": sorted(forwarding), "blocked": sorted(blocked), "cut_off": sorted(cut_off)}


def active_topology(g: nx.Graph, priorities: dict[str, int] | None = None) -> nx.Graph:
    """The network traffic can actually use: every working cable except the ones STP blocked."""
    active = g.copy()
    active.remove_edges_from(compute_stp(g, priorities)["blocked"])
    return active


def show(title: str, result: dict) -> None:
    print(f"{title}")
    print(f"  Root bridge: {result['root']}  (bridge ID {result['bridge_id'][result['root']]})")
    for b, via in sorted(result["root_ports"].items()):
        print(f"  {b:<8} reaches the root via {via}")
    print("  FORWARDING:", ", ".join(f"{a}<->{b}" for a, b in result["forwarding"]))
    print("  BLOCKED:   ", ", ".join(f"{a}<->{b}" for a, b in result["blocked"]))
    if result["cut_off"]:
        print("  CUT OFF from the root:", ", ".join(result["cut_off"]))


if __name__ == "__main__":
    g = build_campus()
    s = switch_graph(g)
    print(f"Switches: {s.number_of_nodes()}, switch-to-switch links: {s.number_of_edges()}, "
          f"independent loops: {len(nx.cycle_basis(s))}  -> without STP, broadcasts circle forever\n")

    show("1. DESIGNED: core configured as root", compute_stp(g))
    print()
    show("2. DEFAULT priorities: lowest MAC wins", compute_stp(g, priorities={}))
    print()
    show("3. DESIGNED, after ACCESS-2<->DIST-1 fails", compute_stp(g, failed=(("ACCESS-2", "DIST-1"),)))
    print()
    show("4. DESIGNED, after BOTH ACCESS-1 uplinks fail",
         compute_stp(g, failed=(("ACCESS-1", "DIST-1"), ("ACCESS-1", "DIST-2"))))