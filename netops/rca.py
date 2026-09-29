"""Phase 7: detection, root-cause analysis and structured findings.

This is the ANALYTICS layer. It is deterministic: the same telemetry always
produces the same diagnosis, and every conclusion points back to evidence.
No AI is involved here; Phase 9 only rephrases what this module decides.

1. DETECT   turn raw telemetry into symptoms (thresholds + deviation from baseline)
2. CORRELATE match the pattern of symptoms to a probable root cause (ordered rules)
3. REPORT   produce a finding: problem, cause, evidence, impact, action, confidence
"""
from dataclasses import dataclass, field

from netops.addressing import VLANS
from netops.health import build_baseline, latency_ms
from netops.inventory import build_inventory
from netops.scenarios import SCENARIOS, run
from netops.telemetry import flow_path
from netops.topology import build_campus

_INV = build_inventory(build_campus())
_BASELINE = build_baseline(build_campus()).set_index("link")


def dept(device: str) -> str:
    return VLANS[_INV[device].vlan].name


# ---------------------------------------------------------------- 1. DETECT
@dataclass
class Symptom:
    kind: str          # link_down, congestion, above_baseline, loss_without_load,
                       # latency_without_load, policy_violation, user_impact
    target: str        # a link, a device or a user
    detail: str


def detect(result: dict, normal: dict) -> list[Symptom]:
    symptoms = []
    for _, r in result["health"].iterrows():
        link, util = r["link"], r["utilization_pct"]
        if r["status"] == "DOWN":
            symptoms.append(Symptom("link_down", link, "link reports down"))
            continue
        if util >= 90:
            symptoms.append(Symptom("congestion", link, f"{util}% utilization"))
        if link in _BASELINE.index:
            mean, spread = _BASELINE.loc[link, "normal_util_pct"], _BASELINE.loc[link, "normal_spread"]
            z = (util - mean) / max(spread, 1.0)
            if z >= 3 and util >= 30:
                symptoms.append(Symptom("above_baseline", link, f"{util}% vs normal {mean}% ± {spread}"))
        if r["loss_pct"] > 0 and util < 70:
            symptoms.append(Symptom("loss_without_load", link, f"{r['loss_pct']}% loss at only {util}% load"))
        expected = latency_ms(r["kind"], util)
        if r["latency_ms"] - expected > 20 and util < 70:
            symptoms.append(Symptom("latency_without_load", link,
                                    f"{r['latency_ms']} ms, expected {expected} ms at {util}% load"))

    for e in result["security_events"]:
        symptoms.append(Symptom("policy_violation", e["src"], f"{e['src']} -> {e['dst']}:{e['port']} ({e['rule']})"))

    for user, now in result["user_experience"].items():
        before = normal["user_experience"][user]
        if now["loss_pct"] >= 1 or now["latency_ms"] >= 3 * before["latency_ms"]:
            symptoms.append(Symptom("user_impact", user,
                                    f"{now['latency_ms']} ms / {now['loss_pct']}% loss "
                                    f"(normally {before['latency_ms']} ms / {before['loss_pct']}%)"))
    return symptoms


# ------------------------------------------------------------ 2 + 3. CORRELATE AND REPORT
@dataclass
class Finding:
    category: str
    culprit: str
    problem: str
    likely_cause: str
    evidence: list[str] = field(default_factory=list)
    impact: str = ""
    action: str = ""
    confidence: str = "Medium"


def _of(symptoms, kind):
    return [s for s in symptoms if s.kind == kind]


def _affected(symptoms) -> list[str]:
    return sorted({s.target for s in _of(symptoms, "user_impact")})


def _groups(users: list[str]) -> str:
    return " and ".join(sorted({dept(u) for u in users}))


def _impact_text(users: list[str]) -> str:
    if not users:
        return "No users are affected right now."
    return f"{_groups(users)} users see slower or unreliable applications ({', '.join(users)})."


def _top_talker(result: dict, link: str):
    """Which flow puts the most load on this link?"""
    a, b = link.split("<->")
    crossing = []
    for f in result["flows"]:
        path, _ = flow_path(result["graph"], f)
        if any({x, y} == {a, b} for x, y in zip(path, path[1:])):
            crossing.append(f)
    top = max(crossing, key=lambda f: f.mbps)
    return top, top.mbps / sum(f.mbps for f in crossing)


def correlate(result: dict, symptoms: list[Symptom]) -> Finding | None:
    users = _affected(symptoms)
    evidence_for = lambda link: [s.detail for s in symptoms if s.target == link]

    # Rule 1: a link is down. Did failover save the users?
    if down := _of(symptoms, "link_down"):
        link = down[0].target
        saved = not users
        return Finding(
            "link_down", link,
            problem=f"Link {link} is down." + (" Users are unaffected." if saved else ""),
            likely_cause=f"Physical failure of {link} (cable, optic or port).",
            evidence=[f"{link} reports DOWN", "traffic rerouted over the redundant uplink"
                      if saved else "no alternate path"],
            impact=_impact_text(users) + (" Redundancy is lost: one more failure would cut users off."
                                          if saved else ""),
            action=f"Replace the cable or optic on {link} to restore redundancy.",
            confidence="High")

    # Rule 2: denied traffic. Combined with congestion it's a compromised device.
    if violations := _of(symptoms, "policy_violation"):
        src = violations[0].target
        congested = _of(symptoms, "congestion")
        if congested:
            link = congested[0].target
            return Finding(
                "compromised_device", src,
                problem=f"{dept(src)} device {src} is flooding the network with blocked traffic.",
                likely_cause=f"{src} appears compromised: it is scanning internal servers and calling out.",
                evidence=[v.detail for v in violations] + evidence_for(link),
                impact=_impact_text(users) + f" The ACL blocked every attempt, but the junk traffic "
                                             f"still saturates {link}.",
                action=f"Quarantine {src}: shut its switch port or move it to an isolated VLAN, then investigate.",
                confidence="High")
        return Finding(
            "unauthorized_access", src,
            problem=f"{dept(src)} device {src} tried to reach systems it is not allowed to.",
            likely_cause=f"Unauthorized access attempt from {src} ({len(violations)} blocked connections).",
            evidence=[v.detail for v in violations],
            impact="No impact: the segmentation policy blocked every attempt.",
            action=f"Identify who is using {src}; confirm guest isolation; keep the deny rules in place.",
            confidence="High")

    # Rule 3: loss that congestion can't explain means hardware.
    if lossy := _of(symptoms, "loss_without_load"):
        link = lossy[0].target
        return Finding(
            "physical_fault", link,
            problem=f"Users behind {link} are losing packets.",
            likely_cause=f"Faulty cable or optic on {link}: loss is present without congestion.",
            evidence=evidence_for(link),
            impact=_impact_text(users),
            action=f"Check interface error counters on {link}; replace the optic or cable.",
            confidence="High")

    # Rule 4: latency that load can't explain, on the WAN, means the provider.
    if slow := _of(symptoms, "latency_without_load"):
        link = slow[0].target
        wan = "INTERNET" in link
        return Finding(
            "provider_issue" if wan else "latency_fault", link,
            problem="Internet access is slow for everyone; internal applications are normal."
            if wan else f"High latency on {link}.",
            likely_cause="A problem inside the internet provider's network." if wan
            else f"Unexplained delay on {link}.",
            evidence=evidence_for(link),
            impact=_impact_text(users),
            action="Open a ticket with the internet provider; share the latency measurements."
            if wan else f"Investigate {link}.",
            confidence="Medium")

    # Rule 5: congestion. Who is the top talker, and is it the victim or a neighbor?
    if hot := _of(symptoms, "congestion"):
        worst = max(hot, key=lambda s: float(s.detail.split("%")[0]))
        link = worst.target
        top, share = _top_talker(result, link)
        neighbor = [u for u in users if dept(u) != dept(top.src)]
        return Finding(
            "congestion", link,
            problem=f"{_groups(users)} users are experiencing degraded connectivity.",
            likely_cause=f"{link} is saturated; the top flow is {top.src} -> {top.dst} "
                         f"({top.app}, {top.mbps} Mbps, {share:.0%} of the load).",
            evidence=evidence_for(link) + [s.detail for s in _of(symptoms, "user_impact")],
            impact=_impact_text(users) + (f" {_groups(neighbor)} users are hit by another group's traffic."
                                          if neighbor else ""),
            action=f"Rate-limit or reschedule the {top.app} flow from {top.src}; "
                   f"review capacity on {link} if this repeats.",
            confidence="High" if share >= 0.4 else "Medium")

    return None


def diagnose(name: str) -> Finding | None:
    result, normal = run(name), run("normal")
    return correlate(result, detect(result, normal))


def show(f: Finding | None, name: str) -> None:
    print(f"===== {name} =====")
    if f is None:
        print("No problems detected.\n")
        return
    print(f"PROBLEM:            {f.problem}")
    print(f"LIKELY CAUSE:       {f.likely_cause}")
    print("EVIDENCE:           " + "\n                    ".join(f.evidence))
    print(f"BUSINESS IMPACT:    {f.impact}")
    print(f"RECOMMENDED ACTION: {f.action}")
    print(f"CONFIDENCE:         {f.confidence}\n")


# Ground truth: what really broke in each scenario (category, culprit).
EXPECTED = {
    "normal": None,
    "link_failure": ("link_down", "ACCESS-2<->DIST-1"),
    "congested_uplink": ("congestion", "ACCESS-2<->DIST-1"),
    "abnormal_traffic": ("congestion", "ACCESS-2<->DIST-1"),
    "unauthorized_access": ("unauthorized_access", "guest-1"),
    "rogue_iot": ("compromised_device", "iot-cam-1"),
    "packet_loss": ("physical_fault", "ACCESS-1<->DIST-1"),
    "high_latency": ("provider_issue", "EDGE<->INTERNET"),
}


def accuracy() -> tuple[int, int]:
    """How many scenarios does the engine diagnose correctly? (a real product metric)"""
    correct = 0
    for name, expected in EXPECTED.items():
        f = diagnose(name)
        got = None if f is None else (f.category, f.culprit)
        correct += got == expected
    return correct, len(EXPECTED)


if __name__ == "__main__":
    for name in SCENARIOS:
        show(diagnose(name), name)
    ok, total = accuracy()
    print(f"Diagnosis accuracy: {ok}/{total} scenarios correct")