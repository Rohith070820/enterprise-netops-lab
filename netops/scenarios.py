"""Phase 6, Task 2: failure and anomaly scenarios.

Each scenario changes the MODEL (cut a link, add a traffic flow, inject a
physical fault), and the telemetry is then recalculated from that model.
Nothing is typed in by hand. "normal" is the reset state.
"""
from dataclasses import dataclass, field

import networkx as nx
import pandas as pd

from netops.health import link_health, path_experience
from netops.policy import evaluate
from netops.telemetry import Flow, flow_path, generate_flows
from netops.topology import build_campus


@dataclass
class Scenario:
    name: str
    description: str
    failed_links: list[tuple[str, str]] = field(default_factory=list)
    extra_flows: list[Flow] = field(default_factory=list)
    faults: dict[str, dict] = field(default_factory=dict)   # link -> {"loss": %, "latency": ms}


SCENARIOS = {
    "normal": Scenario("normal", "Healthy network (reset state)"),
    "link_failure": Scenario(
        "link_failure", "Cable ACCESS-2<->DIST-1 is cut",
        failed_links=[("ACCESS-2", "DIST-1")]),
    "congested_uplink": Scenario(
        "congested_uplink", "Engineering starts a 450 Mbps transfer to the build server",
        extra_flows=[Flow("eng-pc-1", "eng-srv", "huge-transfer", 450.0)]),
    "abnormal_traffic": Scenario(
        "abnormal_traffic", "A guest device pulls 700 Mbps from the internet",
        extra_flows=[Flow("guest-1", "internet", "bulk-download", 700.0)]),
    "unauthorized_access": Scenario(
        "unauthorized_access", "A guest device tries to reach the finance server on 4 ports",
        extra_flows=[Flow("guest-1", "fin-srv", "probe", 0.1, port=p) for p in (443, 445, 22, 3389)]),
    "rogue_iot": Scenario(
        "rogue_iot", "A compromised camera floods internal servers and tries to call out",
        extra_flows=[Flow("iot-cam-1", "fin-srv", "scan", 300.0, port=445),
                     Flow("iot-cam-1", "hr-srv", "scan", 300.0, port=445),
                     Flow("iot-cam-1", "internet", "exfil", 100.0)]),
    "packet_loss": Scenario(
        "packet_loss", "A faulty optic on ACCESS-1<->DIST-1 corrupts frames",
        faults={"ACCESS-1<->DIST-1": {"loss": 8.0}}),
    "high_latency": Scenario(
        "high_latency", "The internet provider has a routing problem",
        faults={"EDGE<->INTERNET": {"latency": 150.0}}),
}


def run(name: str, seed: int = 42) -> dict:
    """Apply a scenario to a fresh copy of the campus and recompute all telemetry."""
    sc = SCENARIOS[name]
    g = build_campus()
    g.remove_edges_from(sc.failed_links)
    flows = generate_flows(seed=seed, extra=sc.extra_flows)

    health = link_health(g, flows)
    for link, fault in sc.faults.items():                   # physical faults, not caused by load
        row = health["link"] == link
        health.loc[row, "loss_pct"] += fault.get("loss", 0.0)
        health.loc[row, "latency_ms"] += fault.get("latency", 0.0)
        health.loc[row, "status"] = "CRITICAL"
    for a, b in sc.failed_links:                             # a dead link reports no traffic
        down = {"link": "<->".join(sorted((a, b))), "kind": "uplink", "capacity_mbps": 0,
                "load_mbps": 0.0, "utilization_pct": 0.0, "latency_ms": 0.0, "loss_pct": 100.0,
                "status": "DOWN"}
        health = pd.concat([health, pd.DataFrame([down])], ignore_index=True)

    events = []
    for f in flows:
        if flow_path(g, f)[1] == "DENIED":
            v = evaluate(f.src, f.dst, f.port)
            events.append({"src": f.src, "dst": f.dst, "port": f.port, "rule": v.rule})

    users = {u: path_experience(g, health, u, d) for u, d in
             [("eng-pc-1", "eng-srv"), ("fin-pc-1", "fin-srv"), ("guest-1", "internet")]}
    return {"scenario": sc, "graph": g, "flows": flows, "health": health,
            "security_events": events, "user_experience": users}


def summarize(result: dict) -> None:
    sc, health = result["scenario"], result["health"]
    print(f"[{sc.name}] {sc.description}")
    problems = health[health["status"] != "OK"]
    for _, r in problems.iterrows():
        print(f"   {r['status']:<8} {r['link']:<20} util {r['utilization_pct']:>5}%  "
              f"latency {r['latency_ms']:>6} ms  loss {r['loss_pct']:>5}%")
    if problems.empty:
        print("   all links OK")
    if result["security_events"]:
        print(f"   {len(result['security_events'])} denied flows: "
              + ", ".join(f"{e['src']}->{e['dst']}:{e['port']}" for e in result["security_events"]))
    ux = "  ".join(f"{u}: {v['latency_ms']}ms/{v['loss_pct']}%" for u, v in result["user_experience"].items())
    print(f"   users (latency/loss): {ux}\n")


if __name__ == "__main__":
    for name in SCENARIOS:
        summarize(run(name))