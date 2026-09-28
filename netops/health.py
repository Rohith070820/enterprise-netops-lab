"""Phase 5, Task 2: latency, packet loss and the baseline.

Latency and loss are DERIVED from utilization with a simple queueing rule:
- a link has a base delay (the time to cross it when it is idle)
- as it fills up, packets wait in a queue: delay = base / (1 - utilization)
- below 80% nothing is dropped; above 80% the queue starts overflowing,
  and above 100% everything beyond capacity is lost

A physical fault (see paths.degrade_link) adds loss or delay ON TOP of that,
whatever the load: loss with an empty link points at hardware, not traffic.

The baseline is "what normal looks like": utilization averaged over many
normal traffic samples. Phase 7 compares live numbers against it.
"""
import networkx as nx
import pandas as pd

from netops.paths import find_path
from netops.policy import ACL, Rule
from netops.telemetry import Flow, generate_flows, link_utilization
from netops.topology import build_campus

BASE_DELAY_MS = {"access-port": 0.2, "server-port": 0.2, "uplink": 0.5, "backbone": 0.3, "wan": 8.0}


def latency_ms(kind: str, utilization_pct: float) -> float:
    rho = min(utilization_pct / 100, 0.99)          # cap so the queue never divides by zero
    return round(BASE_DELAY_MS[kind] / (1 - rho), 2)


def loss_pct(utilization_pct: float) -> float:
    rho = utilization_pct / 100
    if rho <= 0.8:
        return 0.0
    if rho <= 1.0:
        return round(15 * ((rho - 0.8) / 0.2) ** 2, 1)   # queue overflowing more and more
    return round(max(15.0, 100 * (1 - 1 / rho)), 1)      # over capacity: the excess is dropped


def status(utilization_pct: float, loss: float, latency: float = 0.0) -> str:
    # 150 ms one way is the classic limit for a good voice call (ITU-T G.114).
    if utilization_pct >= 90 or loss >= 5 or latency >= 150:
        return "CRITICAL"
    if utilization_pct >= 70 or loss > 0 or latency >= 50:
        return "WARNING"
    return "OK"


def add_health(util: pd.DataFrame, g: nx.Graph | None = None) -> pd.DataFrame:
    """Turn each link's utilization into latency, loss and a status.

    Pass the network too to include physical faults set with paths.degrade_link.
    """
    df = util.copy()
    faults = {"<->".join(sorted((a, b))): d for a, b, d in g.edges(data=True)} if g is not None else {}
    extra_ms = [faults.get(l, {}).get("extra_latency_ms", 0.0) for l in df["link"]]
    extra_loss = [faults.get(l, {}).get("extra_loss_pct", 0.0) for l in df["link"]]

    df["latency_ms"] = [round(latency_ms(k, u) + x, 2) for k, u, x in zip(df["kind"], df["utilization_pct"], extra_ms)]
    # Two independent ways to lose a packet: it survives only if it survives both.
    df["loss_pct"] = [round(100 - (100 - loss_pct(u)) * (1 - x / 100), 1) for u, x in zip(df["utilization_pct"], extra_loss)]
    df["status"] = [status(u, l, ms) for u, l, ms in zip(df["utilization_pct"], df["loss_pct"], df["latency_ms"])]
    return df.sort_values(["utilization_pct", "link"], ascending=[False, True], ignore_index=True)


def link_health(g: nx.Graph, flows: list[Flow], acl: list[Rule] = ACL) -> pd.DataFrame:
    return add_health(link_utilization(g, flows, acl), g)


def path_experience(g: nx.Graph, health: pd.DataFrame, src: str, dst: str) -> dict:
    """What a user actually feels end to end: total latency, combined loss."""
    by_link = health.set_index("link")
    path = find_path(g, src, "INTERNET" if dst == "internet" else dst)
    if path is None:                        # no way through: nothing arrives at all
        return {"latency_ms": None, "loss_pct": 100.0}
    total_ms, delivered = 0.0, 1.0
    for a, b in zip(path, path[1:]):
        row = by_link.loc["<->".join(sorted((a, b)))]
        total_ms += row["latency_ms"]
        delivered *= 1 - row["loss_pct"] / 100
    return {"latency_ms": round(float(total_ms), 1), "loss_pct": round(float(100 * (1 - delivered)), 1)}


def build_baseline(g: nx.Graph, samples: int = 20) -> pd.DataFrame:
    """Normal behavior per link: mean and spread of utilization over many normal samples."""
    runs = [link_utilization(g, generate_flows(seed=s)) for s in range(samples)]
    allruns = pd.concat(runs)
    base = allruns.groupby("link")["utilization_pct"].agg(["mean", "std"]).round(1)
    return base.rename(columns={"mean": "normal_util_pct", "std": "normal_spread"}).reset_index()


if __name__ == "__main__":
    g = build_campus()
    cols = ["link", "utilization_pct", "latency_ms", "loss_pct", "status"]
    key_links = ["ACCESS-2<->DIST-1", "ACCESS-1<->DIST-1", "EDGE<->INTERNET", "CORE<->DIST-1"]

    normal = link_health(g, generate_flows(seed=42))
    print("NORMAL day (seed 42):")
    print(normal[normal["link"].isin(key_links)][cols].to_string(index=False))
    print("  Engineer to build server:", path_experience(g, normal, "eng-pc-1", "eng-srv"))

    big = Flow("eng-pc-1", "eng-srv", "huge-download", 450.0)
    busy = link_health(g, generate_flows(seed=42, extra=[big]))
    print("\nSAME day + a 450 Mbps Engineering download:")
    print(busy[busy["link"].isin(key_links)][cols].to_string(index=False))
    print("  Engineer to build server:", path_experience(g, busy, "eng-pc-1", "eng-srv"))

    print("\nBASELINE (20 normal samples):")
    base = build_baseline(g)
    print(base[base["link"].isin(key_links)].to_string(index=False))