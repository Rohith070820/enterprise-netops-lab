"""Phase 4, Task 1: how a switch learns and forwards.

A switch keeps a MAC address table: "MAC X (in VLAN V) lives behind port P".
- It LEARNS from the SOURCE MAC of every frame that arrives.
- It FORWARDS by looking up the DESTINATION MAC.
- If the destination is unknown or broadcast, it FLOODS out every port in that VLAN
  (except the one the frame came in on). It never floods into other VLANs.
"""
from dataclasses import dataclass

import networkx as nx

from netops.inventory import Device, build_inventory, gateway_mac, vlans_on_link
from netops.topology import build_campus

BROADCAST = "ff:ff:ff:ff:ff:ff"


@dataclass(frozen=True)
class Frame:
    src_mac: str
    dst_mac: str
    vlan: int


class Switch:
    def __init__(self, g: nx.Graph, inventory: dict[str, Device], name: str):
        self.name = name
        # Each port is named after the device on the other end; value = VLANs allowed on it.
        self.ports = {nbr: set(vlans_on_link(g, inventory, name, nbr)) for nbr in sorted(g.neighbors(name))}
        self.mac_table: dict[tuple[int, str], str] = {}  # (vlan, mac) -> port

    def receive(self, frame: Frame, in_port: str) -> tuple[str, list[str]]:
        """Process one frame. Returns (decision, ports it goes out of)."""
        if frame.vlan not in self.ports[in_port]:
            return "dropped (VLAN not allowed on this port)", []

        self.mac_table[(frame.vlan, frame.src_mac)] = in_port          # 1. learn the sender

        known_port = self.mac_table.get((frame.vlan, frame.dst_mac))    # 2. look up the receiver
        if frame.dst_mac != BROADCAST and known_port:
            if known_port == in_port:
                return "filtered (destination is on the same port)", []
            return "forwarded", [known_port]

        same_vlan = [p for p, vlans in self.ports.items() if p != in_port and frame.vlan in vlans]
        return "flooded", same_vlan                                     # 3. unknown: flood in VLAN only


if __name__ == "__main__":
    g = build_campus()
    inv = build_inventory(g)
    sw = Switch(g, inv, "ACCESS-1")
    fin, hr = inv["fin-pc-1"], inv["hr-pc-1"]
    gw20 = gateway_mac(20)

    steps = [
        ("fin-pc-1 ARP broadcast 'who has 10.10.20.1?'", Frame(fin.mac, BROADCAST, 20), "fin-pc-1"),
        ("Gateway replies to fin-pc-1",                  Frame(gw20, fin.mac, 20),      "DIST-1"),
        ("fin-pc-1 sends data to the gateway",           Frame(fin.mac, gw20, 20),      "fin-pc-1"),
        ("hr-pc-1 sends to an unknown MAC",              Frame(hr.mac, "02:00:00:1e:00:99", 30), "hr-pc-1"),
        ("A Guest (VLAN 40) frame arrives on the uplink", Frame("02:00:00:28:00:15", BROADCAST, 40), "DIST-1"),
    ]
    print(f"Switch {sw.name}, ports: " + ", ".join(f"{p}{sorted(v)}" for p, v in sw.ports.items()) + "\n")
    for i, (label, frame, port) in enumerate(steps, 1):
        decision, out = sw.receive(frame, port)
        print(f"{i}. {label}")
        print(f"   in on {port:<8} -> {decision}{': ' + ', '.join(out) if out else ''}")

    print("\nMAC address table:")
    print(f"  {'VLAN':<5} {'MAC':<18} Port")
    for (vlan, mac), port in sorted(sw.mac_table.items()):
        print(f"  {vlan:<5} {mac:<18} {port}")