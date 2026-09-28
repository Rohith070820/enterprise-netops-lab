"""Phase 2, Task 2: paths and failover.

A path is the list of hops traffic takes. Failover is what happens when a
link or device on that path breaks and traffic has to find another way.
"""
import networkx as nx

from netops.topology import build_campus


def find_path(g: nx.Graph, src: str, dst: str) -> list[str] | None:
    """Shortest path from src to dst, or None if there is no way through."""
    try:
        return nx.shortest_path(g, src, dst)
    except (nx.NetworkXNoPath, nx.NodeNotFound):   # no way through, or one end is powered off
        return None


def fail_link(g: nx.Graph, a: str, b: str) -> nx.Graph:
    """Return a copy of the network with the cable between a and b cut."""
    broken = g.copy()
    broken.remove_edge(a, b)
    return broken


def fail_device(g: nx.Graph, device: str) -> nx.Graph:
    """Return a copy of the network with one device powered off."""
    broken = g.copy()
    broken.remove_node(device)
    return broken


def degrade_link(g: nx.Graph, a: str, b: str, loss_pct: float = 0.0, latency_ms: float = 0.0) -> nx.Graph:
    """Return a copy of the network where the cable between a and b works, but badly.

    Not every problem is about load. A dirty or failing optic corrupts frames (loss),
    and a struggling internet provider adds delay, even when the link is nearly empty.
    """
    damaged = g.copy()
    damaged.edges[a, b]["extra_loss_pct"] = loss_pct
    damaged.edges[a, b]["extra_latency_ms"] = latency_ms
    return damaged


def show(label: str, path: list[str] | None) -> None:
    print(f"{label:<34} {' -> '.join(path) if path else 'NO PATH: user is cut off'}")


if __name__ == "__main__":
    g = build_campus()
    src, dst = "fin-pc-1", "fin-srv"
    print(f"Finance laptop ({src}) to Finance server ({dst})\n")

    show("1. Normal:", find_path(g, src, dst))

    g1 = fail_link(g, "ACCESS-1", "DIST-1")
    show("2. Uplink ACCESS-1<->DIST-1 cut:", find_path(g1, src, dst))

    g2 = fail_device(g, "DIST-1")
    show("3. DIST-1 switch dies:", find_path(g2, src, dst))

    g3 = fail_link(g1, "ACCESS-1", "DIST-2")
    show("4. BOTH ACCESS-1 uplinks cut:", find_path(g3, src, dst))