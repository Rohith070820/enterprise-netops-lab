"""Phase 5, Task 1: telemetry derived from traffic.

Nothing here is a random dashboard number. We generate traffic FLOWS
(who talks to whom, how many Mbps), push each flow along its real path through
the topology, and add up the load on every link:

    utilization % = (sum of Mbps of all flows crossing the link) / link capacity

Flows the ACL denies still travel up to the gateway, then get dropped there.
"""
import random
from dataclasses import dataclass

import networkx as nx
import pandas as pd

from netops.paths import find_path
from netops.policy import evaluate
from netops.topology import build_campus

# Typical demand per endpoint, in Mbps. Each endpoint stands in for its
# department's users on that switch, so the numbers are group totals.
DEMAND = [
    ("eng-pc-1",  "eng-srv",  "builds",  300),
    ("eng-pc-1",  "internet", "web",     150),
    ("fin-pc-1",  "fin-srv",  "erp",      80),
    ("fin-pc-1",  "internet", "web",      40),
    ("hr-pc-1",   "hr-srv",   "hr-app",   30),
    ("hr-pc-1",   "internet", "web",      30),
    ("guest-1",   "internet", "video",    60),
]


@dataclass(frozen=True)
class Flow:
    src: str
    dst: str
    app: str
    mbps: float
    port: int = 443


def generate_flows(seed: int = 42, extra: list[Flow] | None = None) -> list[Flow]:
    """Same seed -> same flows, so every run is reproducible."""
    rng = random.Random(seed)
    flows = [Flow(s, d, app, round(mbps * rng.uniform(0.85, 1.15), 1)) for s, d, app, mbps in DEMAND]
    return flows + (extra or [])


def flow_path(g: nx.Graph, flow: Flow) -> tuple[list[str], str]:
    """The path a flow actually travels, and whether the ACL allowed it."""
    path = find_path(g, flow.src, "INTERNET" if flow.dst == "internet" else flow.dst)
    if path is None:
        return [], "UNREACHABLE"
    verdict = evaluate(flow.src, flow.dst, flow.port)
    if verdict.action == "DENY":  # travels to the gateway, then dropped
        gateway = next(i for i, n in enumerate(path) if g.nodes[n]["layer"] == "distribution")
        return path[: gateway + 1], "DENIED"
    return path, "ALLOWED"


def link_utilization(g: nx.Graph, flows: list[Flow]) -> pd.DataFrame:
    load = {tuple(sorted(e)): 0.0 for e in g.edges}
    for flow in flows:
        path, _ = flow_path(g, flow)
        for a, b in zip(path, path[1:]):
            load[tuple(sorted((a, b)))] += flow.mbps

    rows = []
    for (a, b), mbps in load.items():
        cap = g.edges[a, b]["capacity_mbps"]
        rows.append({"link": f"{a}<->{b}", "kind": g.edges[a, b]["kind"], "capacity_mbps": cap,
                     "load_mbps": round(mbps, 1), "utilization_pct": round(100 * mbps / cap, 1)})
    return pd.DataFrame(rows).sort_values("utilization_pct", ascending=False, ignore_index=True)


if __name__ == "__main__":
    g = build_campus()
    flows = generate_flows(seed=42)

    print("Traffic flows (seed 42):")
    for f in flows:
        path, status = flow_path(g, f)
        print(f"  {f.src:<9} -> {f.dst:<8} {f.app:<7} {f.mbps:>6} Mbps  {status:<8} {' > '.join(path)}")

    df = link_utilization(g, flows)
    print("\nBusiest links (inter-switch and WAN):")
    busy = df[df["kind"].isin(["uplink", "backbone", "wan"])].head(6)
    print(busy.to_string(index=False))