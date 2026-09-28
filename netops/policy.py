"""Phase 4, Task 3: segmentation with an access control list (ACL).

The ACL lives on the gateway (distribution switch), because every packet that
crosses VLANs has to pass through it. Rules are checked top to bottom:
the FIRST rule that matches decides. If nothing matches, the packet is DENIED
(the "implicit deny" at the end of every ACL). That's least privilege:
anything not explicitly allowed is blocked.
"""
from dataclasses import dataclass

from netops.addressing import VLANS
from netops.inventory import build_inventory
from netops.topology import build_campus

CORPORATE = ("Engineering", "Finance", "HR")


@dataclass(frozen=True)
class Rule:
    name: str
    action: str                      # "ALLOW" or "DENY"
    src: tuple[str, ...]             # VLAN names, or ("any",)
    dst: str                         # "internet", "internal", a device name, or "any"
    port: int | None = None          # None = any port


# Order matters: first match wins.
ACL = [
    Rule("eng-to-eng-server",  "ALLOW", ("Engineering",), "eng-srv", 443),
    Rule("fin-to-fin-server",  "ALLOW", ("Finance",),     "fin-srv", 443),
    Rule("hr-to-hr-server",    "ALLOW", ("HR",),          "hr-srv",  443),
    Rule("guest-no-internal",  "DENY",  ("Guest",),       "internal"),
    Rule("iot-no-internal",    "DENY",  ("IoT",),         "internal"),
    Rule("guest-to-internet",  "ALLOW", ("Guest",),       "internet"),
    Rule("corp-to-internet",   "ALLOW", CORPORATE,        "internet"),
]


@dataclass(frozen=True)
class Verdict:
    action: str
    rule: str
    enforced_at: str


def _matches(rule: Rule, src_vlan: str, dst: str, dst_is_internal: bool, port: int) -> bool:
    src_ok = "any" in rule.src or src_vlan in rule.src
    dst_ok = (rule.dst == "any" or rule.dst == dst
              or (rule.dst == "internal" and dst_is_internal)
              or (rule.dst == "internet" and not dst_is_internal))
    port_ok = rule.port is None or rule.port == port
    return src_ok and dst_ok and port_ok


def evaluate(src: str, dst: str, port: int, acl: list[Rule] = ACL) -> Verdict:
    """Decide one flow. src is a device; dst is a device name or 'internet'."""
    inv = build_inventory(build_campus())
    me = inv[src]
    src_vlan = VLANS[me.vlan].name
    dst_is_internal = dst != "internet"

    # Traffic that never leaves its VLAN is switched, not routed: the gateway ACL never sees it.
    if dst_is_internal and inv[dst].vlan == me.vlan:
        return Verdict("ALLOW", "none (same VLAN)", "NOT INSPECTED: never reaches the gateway")

    for rule in acl:
        if _matches(rule, src_vlan, dst, dst_is_internal, port):
            return Verdict(rule.action, rule.name, f"gateway ACL for VLAN {me.vlan}")
    return Verdict("DENY", "implicit deny", f"gateway ACL for VLAN {me.vlan}")


DEMO_FLOWS = [
    ("fin-pc-1",  "fin-srv",  443, "Finance user opens the finance app"),
    ("eng-pc-1",  "eng-srv",  443, "Engineer opens the build server"),
    ("hr-pc-1",   "hr-srv",   443, "HR opens the HR system"),
    ("eng-pc-1",  "fin-srv",  443, "Engineer tries the finance app"),
    ("guest-1",   "fin-srv",  443, "Guest tries the finance app"),
    ("guest-1",   "internet", 443, "Guest browses the web"),
    ("iot-cam-1", "fin-srv",  445, "Camera probes finance file shares"),
    ("iot-cam-1", "internet", 443, "Camera calls out to the internet"),
    ("eng-srv",   "fin-srv",  445, "Engineering server reaches finance server"),
]


if __name__ == "__main__":
    print(f"{'Flow':<42} {'Result':<6} {'Matched rule':<19} Enforced at")
    for src, dst, port, label in DEMO_FLOWS:
        v = evaluate(src, dst, port)
        print(f"{label:<42} {v.action:<6} {v.rule:<19} {v.enforced_at}")