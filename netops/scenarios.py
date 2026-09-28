"""Phase 6, Task 2: failure and anomaly scenarios.

A scenario is one thing going wrong: a cable is cut, a device dies, traffic surges,
a device misbehaves, an optic goes bad, the internet provider slows down, or someone
makes a bad config change. We change the MODEL (links, devices, flows, ACL, or a
physical fault on a cable) and then re-run everything built so far. No metric is ever
typed in: every number below is recomputed from the damaged network.

1. FAULTS:   remove failed cables and devices; mark damaged cables (extra loss or delay)
2. STP:      recalculate the spanning tree; traffic only uses FORWARDING links
3. TRAFFIC:  push the day's flows through what is left (the ACL still applies)
4. HEALTH:   utilization -> latency, loss and status for every cable (DOWN if cut)
5. IMPACT:   compare every flow with the same flow on a normal day:
             "lost" (it no longer gets through), "degraded" (1%+ loss or twice as slow),
             "none", or "new" (traffic that does not exist on a normal day)
6. SECURITY: every flow the ACL blocks is a security event, like a firewall log line

Every scenario also records its ground truth: the CULPRIT (a link, device, flow source
or rule) and a CATEGORY. Phase 7 has to find them from the symptoms alone, without peeking.
"normal" is the reset state: nothing broken.
"""
import sys
from dataclasses import dataclass

import networkx as nx
import pandas as pd

from netops.health import add_health, path_experience
from netops.paths import degrade_link, fail_device, fail_link
from netops.policy import ACL, evaluate
from netops.stp import active_topology, compute_stp, switch_graph
from netops.telemetry import Flow, flow_path, generate_flows, link_utilization
from netops.topology import build_campus

DEGRADED_LOSS_PCT = 1.0     # from about 1% loss users notice: retransmissions, choppy calls
DEGRADED_SLOWDOWN = 2.0     # ...or when everything takes twice as long as usual

CATEGORIES = ("none", "failure", "congestion", "abnormal-traffic", "security",
              "physical-fault", "provider", "config")


@dataclass(frozen=True)
class LinkFault:
    """A cable that still works but badly: a dirty optic drops frames, a provider adds delay."""
    a: str
    b: str
    extra_loss_pct: float = 0.0
    extra_latency_ms: float = 0.0


@dataclass(frozen=True)
class Scenario:
    name: str
    title: str
    category: str                                 # one of CATEGORIES
    culprit: str | None                           # ground truth: what really broke
    failed_links: tuple[tuple[str, str], ...] = ()
    failed_devices: tuple[str, ...] = ()
    link_faults: tuple[LinkFault, ...] = ()
    extra_flows: tuple[Flow, ...] = ()            # traffic on top of a normal day
    removed_rules: tuple[str, ...] = ()           # ACL rules a bad change deleted
    stp: str = "designed"                         # "designed", "default" (priorities wiped) or "off"


@dataclass(frozen=True)
class Outcome:
    scenario: Scenario
    network: nx.Graph         # the cables traffic can use: failed and STP-blocked ones removed
    stp: dict | None          # the spanning tree, or None when STP is off
    links: pd.DataFrame       # every cable: state (UP / BLOCKED / DOWN), load and health
    flows: pd.DataFrame       # every flow: ACL result, path, what the user feels, impact

    @property
    def affected_users(self) -> list[str]:
        hurt = self.flows[self.flows["impact"].isin(["lost", "degraded"])]
        return sorted(set(hurt["src"]))

    @property
    def security_events(self) -> pd.DataFrame:
        """Every flow the ACL blocked, as a firewall log would show it."""
        denied = self.flows[self.flows["status"] == "DENIED"]
        return denied[["src", "dst", "port", "rule"]].reset_index(drop=True)


NORMAL = Scenario("normal", "A normal working day", "none", None)

SCENARIOS = {s.name: s for s in [
    NORMAL,
    # --- 1. Switch or link failure ---
    Scenario("uplink-cut", "Someone unplugs ACCESS-2's uplink to DIST-1", "failure",
             "ACCESS-2<->DIST-1", failed_links=(("ACCESS-2", "DIST-1"),)),
    Scenario("dist-down", "DIST-1 loses power", "failure", "DIST-1", failed_devices=("DIST-1",)),
    Scenario("access-down", "ACCESS-1, the Finance and HR switch, dies", "failure", "ACCESS-1",
             failed_devices=("ACCESS-1",)),
    Scenario("core-down", "The core switch dies", "failure", "CORE", failed_devices=("CORE",)),
    Scenario("isp-down", "The line to the internet provider is cut", "failure", "EDGE<->INTERNET",
             failed_links=(("EDGE", "INTERNET"),)),
    Scenario("server-down", "The finance server crashes", "failure", "fin-srv", failed_devices=("fin-srv",)),
    # --- 2. Congested uplink ---
    Scenario("big-download", "An engineer starts a 450 Mbps download", "congestion", "eng-pc-1",
             extra_flows=(Flow("eng-pc-1", "eng-srv", "huge-download", 450.0),)),
    # --- 3. Abnormal high traffic ---
    Scenario("guest-surge", "A guest pulls 700 Mbps from the internet", "abnormal-traffic", "guest-1",
             extra_flows=(Flow("guest-1", "internet", "bulk-download", 700.0),)),
    # --- 4. Unauthorized VLAN access: a guest scans the finance server's doors ---
    Scenario("guest-probe", "A guest probes the finance server (HTTPS, SMB, SSH, RDP)", "security", "guest-1",
             extra_flows=tuple(Flow("guest-1", "fin-srv", "probe", 0.5, port=p) for p in (443, 445, 22, 3389))),
    # --- 5. IoT device behaving abnormally: a camera acting like infected malware ---
    Scenario("iot-anomaly", "A camera floods file shares and calls out to the internet", "security", "iot-cam-1",
             extra_flows=(Flow("iot-cam-1", "fin-srv", "smb-flood", 300.0, port=445),
                          Flow("iot-cam-1", "hr-srv", "smb-flood", 300.0, port=445),
                          Flow("iot-cam-1", "internet", "call-out", 100.0))),
    # --- 6. Packet loss without congestion ---
    Scenario("bad-optic", "A failing optic on ACCESS-1's uplink corrupts 8% of frames", "physical-fault",
             "ACCESS-1<->DIST-1", link_faults=(LinkFault("ACCESS-1", "DIST-1", extra_loss_pct=8.0),)),
    # --- 7. High latency ---
    Scenario("isp-slow", "The internet provider adds 150 ms of delay", "provider", "EDGE<->INTERNET",
             link_faults=(LinkFault("EDGE", "INTERNET", extra_latency_ms=150.0),)),
    # --- Configuration mistakes ---
    Scenario("acl-mistake", "A firewall change deletes the Finance rule", "config",
             "ACL rule fin-to-fin-server", removed_rules=("fin-to-fin-server",)),
    Scenario("stp-wrong-root", "A config push wipes the STP priorities", "config", "STP priorities",
             stp="default"),
    Scenario("stp-off", "Someone switches STP off", "config", "STP disabled", stp="off"),
]}


def storm_links(g: nx.Graph) -> list[str]:
    """The cables a broadcast storm floods when nothing blocks the loops.

    A storm needs a loop of switches. A broadcast caught in one is copied out of every
    port, again and again, so it floods every port of every switch on that loop's island.
    Routers do not forward broadcasts: the storm stops at the edge router.
    """
    s = switch_graph(g)
    looped = set().union(*(i for i in nx.connected_components(s) if nx.cycle_basis(s.subgraph(i))))
    flooded = []
    for a, b in g.edges:
        roles = {g.nodes[a]["role"], g.nodes[b]["role"]}
        if (a in looped or b in looped) and not roles & {"router", "internet"}:
            flooded.append("<->".join(sorted((a, b))))
    return sorted(flooded)


def _simulate(s: Scenario, seed: int) -> tuple[nx.Graph, dict | None, pd.DataFrame, pd.DataFrame]:
    campus = build_campus()
    broken = campus
    for a, b in s.failed_links:
        broken = fail_link(broken, a, b)
    for device in s.failed_devices:
        broken = fail_device(broken, device)
    for f in s.link_faults:
        broken = degrade_link(broken, f.a, f.b, f.extra_loss_pct, f.extra_latency_ms)

    if s.stp == "off":                     # no tree: every cable forwards, loops and all
        tree, network = None, broken
    else:
        priorities = {"designed": None, "default": {}}[s.stp]   # {} = every switch at factory default
        tree = compute_stp(broken, priorities)
        network = active_topology(broken, priorities)

    acl = [rule for rule in ACL if rule.name not in s.removed_rules]
    flows = generate_flows(seed, extra=list(s.extra_flows))

    load = link_utilization(network, flows, acl)
    if s.stp == "off":  # simplified storm: the looping copies alone fill each flooded link to capacity
        flooded = load["link"].isin(storm_links(network))
        load.loc[flooded, "load_mbps"] += load.loc[flooded, "capacity_mbps"]
        load.loc[flooded, "utilization_pct"] = (100 * load["load_mbps"] / load["capacity_mbps"])[flooded].round(1)
    links = add_health(load, network)
    links.insert(1, "state", "UP")

    idle = []  # cables that carry nothing: cut or dead (DOWN), or switched off by STP (BLOCKED)
    for a, b in sorted(tuple(sorted(e)) for e in campus.edges):
        if not network.has_edge(a, b):
            state = "BLOCKED" if broken.has_edge(a, b) else "DOWN"
            idle.append({"link": f"{a}<->{b}", "state": state, "kind": campus.edges[a, b]["kind"],
                         "capacity_mbps": campus.edges[a, b]["capacity_mbps"], "load_mbps": 0.0,
                         "utilization_pct": 0.0, "latency_ms": float("nan"), "loss_pct": float("nan"),
                         "status": state})
    if idle:
        links = pd.concat([links, pd.DataFrame(idle)], ignore_index=True)

    rows = []
    for f in flows:
        path, status = flow_path(network, f, acl)
        rule = evaluate(f.src, f.dst, f.port, acl).rule if path else None   # the rule that decided it
        felt = (path_experience(network, links, f.src, f.dst) if status == "ALLOWED"
                else {"latency_ms": None, "loss_pct": None})
        rows.append({"src": f.src, "dst": f.dst, "app": f.app, "port": f.port, "mbps": f.mbps,
                     "status": status, "rule": rule, "path": " > ".join(path), **felt})
    return network, tree, links, pd.DataFrame(rows)


def _impact(flows: pd.DataFrame, usual: pd.DataFrame) -> list[str]:
    """How each flow compares with the same flow on a normal day."""
    before = usual.set_index(["src", "dst", "app"])
    verdicts = []
    for f in flows.itertuples(index=False):
        key = (f.src, f.dst, f.app)
        if key not in before.index:
            verdicts.append("new")
            continue
        was = before.loc[key]
        if was["status"] != "ALLOWED":
            verdicts.append("none")                  # it never worked, so nothing was lost
        elif f.status != "ALLOWED":
            verdicts.append("lost")
        elif f.loss_pct >= DEGRADED_LOSS_PCT or f.latency_ms >= DEGRADED_SLOWDOWN * was["latency_ms"]:
            verdicts.append("degraded")
        else:
            verdicts.append("none")
    return verdicts


def run(scenario: Scenario | str, seed: int = 42) -> Outcome:
    """Break the network the way the scenario says, then measure everything again."""
    s = SCENARIOS[scenario] if isinstance(scenario, str) else scenario
    network, tree, links, flows = _simulate(s, seed)
    _, _, _, usual = _simulate(NORMAL, seed)
    flows["impact"] = _impact(flows, usual)
    return Outcome(s, network, tree, links, flows)


def notable_links(out: Outcome, normal: Outcome) -> pd.DataFrame:
    """Cables that are down, busy, or in a different STP state than on a normal day."""
    usual_state = out.links["link"].map(normal.links.set_index("link")["state"])
    unusual = out.links["status"].isin(["WARNING", "CRITICAL", "DOWN"]) | (out.links["state"] != usual_state)
    return out.links[unusual]


if __name__ == "__main__":
    normal = run(NORMAL)
    if len(sys.argv) > 1:  # python -m netops.scenarios <name>: one scenario in detail
        out = run(sys.argv[1])
        s = out.scenario
        print(f"=== {s.name}: {s.title} ===")
        print(f"Ground truth: {s.culprit} ({s.category})")
        print(f"Spanning tree root: {out.stp['root'] if out.stp else 'none, STP is off'}\n")
        cols = ["link", "state", "utilization_pct", "latency_ms", "loss_pct", "status"]
        odd = notable_links(out, normal)
        print("Cables that look different from a normal day:")
        print(odd[cols].to_string(index=False) if len(odd) else "  none")
        print("\nFlows:")
        print(out.flows.drop(columns="path").to_string(index=False))
        print("\nSecurity events:")
        print(out.security_events.to_string(index=False) if len(out.security_events) else "  none")
    else:
        print(f"{'Scenario':<15} {'Category':<17} {'Culprit':<27} {'Users hurt':<38} {'Sec':>3}  Cables that look different")
        for name in SCENARIOS:
            out = run(name)
            odd = [f"{r.link} {r.status}" for r in notable_links(out, normal).itertuples()]
            cables = ", ".join(odd[:2]) + (f" (+{len(odd) - 2} more)" if len(odd) > 2 else "") or "-"
            print(f"{name:<15} {out.scenario.category:<17} {out.scenario.culprit or '-':<27} "
                  f"{', '.join(out.affected_users) or 'none':<38} {len(out.security_events):>3}  {cables}")
        print("\nDetail for one scenario: python -m netops.scenarios <name>")
