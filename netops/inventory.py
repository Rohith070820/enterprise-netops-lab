"""Phase 3, Task 2: give every device an identity.

Each endpoint and server gets a VLAN, an IP address inside that VLAN's subnet,
a MAC address, and a default gateway. Each switch port is either an ACCESS port
(one VLAN, for an end device) or a TRUNK port (many VLANs, 802.1Q-tagged, between switches).
"""
import ipaddress
from dataclasses import dataclass

import networkx as nx

from netops.addressing import VLANS
from netops.topology import build_campus

# host -> (VLAN id, last number of its IP address)
ADDRESS_PLAN = {
    "eng-pc-1": (10, 21),
    "fin-pc-1": (20, 21),
    "hr-pc-1": (30, 21),
    "guest-1": (40, 21),
    "iot-cam-1": (50, 33),
    "ap-1": (99, 11),       # Wi-Fi access point lives in the Management VLAN
    "eng-srv": (60, 10),
    "fin-srv": (60, 20),
    "hr-srv": (60, 30),
}


@dataclass(frozen=True)
class Device:
    name: str
    switch: str
    vlan: int
    ip: ipaddress.IPv4Address
    mac: str
    gateway: ipaddress.IPv4Address


def make_mac(vlan: int, host: int) -> str:
    # 02:... = "locally administered" MAC, the range labs and virtual machines use.
    # Real devices carry a manufacturer prefix (OUI) in the first 3 bytes instead.
    return f"02:00:00:{vlan:02x}:00:{host:02x}"


def gateway_mac(vlan: int) -> str:
    return make_mac(vlan, 1)


def build_inventory(g: nx.Graph) -> dict[str, Device]:
    inventory = {}
    for name, (vid, host) in ADDRESS_PLAN.items():
        vlan = VLANS[vid]
        switch = next(n for n in g.neighbors(name) if g.nodes[n]["role"] == "switch")
        inventory[name] = Device(
            name=name,
            switch=switch,
            vlan=vid,
            ip=vlan.subnet.network_address + host,
            mac=make_mac(vid, host),
            gateway=vlan.gateway,
        )
    return inventory


def port_mode(g: nx.Graph, a: str, b: str) -> str:
    """Links to end devices are access ports; links between switches are trunks.
    Links to the edge router (and beyond it) are ROUTED: plain IP, no VLAN tags."""
    if {g.nodes[a]["role"], g.nodes[b]["role"]} & {"router", "internet"}:
        return "routed"
    return "access" if g.edges[a, b]["kind"] in ("access-port", "server-port") else "trunk"


def vlans_on_link(g: nx.Graph, inventory: dict[str, Device], a: str, b: str) -> list[int]:
    if port_mode(g, a, b) == "routed":
        return []  # VLANs end at the router
    if port_mode(g, a, b) == "access":
        device = a if a in inventory else b
        return [inventory[device].vlan]
    access = next((n for n in (a, b) if g.nodes[n]["layer"] == "access"), None)
    if access:  # an uplink only needs the VLANs of devices on that access switch ("pruning")
        return sorted({d.vlan for d in inventory.values() if d.switch == access})
    return sorted(VLANS)  # backbone trunks carry every VLAN


def arp_resolve(inventory: dict[str, Device], src: str, dst_ip: str) -> tuple[str, str | None]:
    """Who does src actually send the frame to? Returns (next-hop IP, next-hop MAC or None)."""
    me = inventory[src]
    target = ipaddress.ip_address(dst_ip)
    if target in VLANS[me.vlan].subnet:  # same subnet: ARP for the destination itself
        dest = next((d for d in inventory.values() if d.ip == target), None)
        return str(target), dest.mac if dest else None  # None = nobody answered
    return str(me.gateway), gateway_mac(me.vlan)  # other subnet: ARP for the gateway


if __name__ == "__main__":
    g = build_campus()
    inv = build_inventory(g)

    print(f"{'Device':<10} {'Switch':<9} {'VLAN':<16} {'IP':<13} {'MAC':<18} Gateway")
    for d in inv.values():
        vlan = f"{d.vlan} {VLANS[d.vlan].name}"
        print(f"{d.name:<10} {d.switch:<9} {vlan:<16} {str(d.ip):<13} {d.mac:<18} {d.gateway}")

    print("\nPorts on ACCESS-1:")
    for nbr in sorted(g.neighbors("ACCESS-1")):
        mode = port_mode(g, "ACCESS-1", nbr)
        vlans = vlans_on_link(g, inv, "ACCESS-1", nbr)
        print(f"  to {nbr:<9} {mode:<7} VLANs {vlans}")

    print("\nARP: before sending, who does each device hand its frame to?")
    for src, dst in [("eng-srv", "10.10.60.20"), ("fin-pc-1", "10.10.60.20"), ("guest-1", "10.10.40.99")]:
        ip, mac = arp_resolve(inv, src, dst)
        answer = f"answered by MAC {mac}" if mac else "no reply (nobody has that IP)"
        print(f"  {src:<9} to reach {dst:<12} -> ARP for {ip:<12} {answer}")