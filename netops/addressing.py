"""Phase 3, Task 1: VLANs, subnets and gateways.

Each VLAN is one department's private network segment. Each VLAN N gets
the subnet 10.10.N.0/24, and its default gateway is the first usable address (.1).
"""
import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class Vlan:
    id: int
    name: str
    subnet: ipaddress.IPv4Network

    @property
    def gateway(self) -> ipaddress.IPv4Address:
        return next(self.subnet.hosts())          # first usable address, .1

    @property
    def broadcast(self) -> ipaddress.IPv4Address:
        return self.subnet.broadcast_address      # last address, .255

    @property
    def usable_hosts(self) -> int:
        return self.subnet.num_addresses - 2      # minus network and broadcast


def _vlan(vid: int, name: str) -> Vlan:
    return Vlan(vid, name, ipaddress.ip_network(f"10.10.{vid}.0/24"))


VLANS = {v.id: v for v in [
    _vlan(10, "Engineering"),
    _vlan(20, "Finance"),
    _vlan(30, "HR"),
    _vlan(40, "Guest"),
    _vlan(50, "IoT"),
    _vlan(60, "Servers"),
    _vlan(99, "Management"),   # the network's own gear: switches, Wi-Fi access points
]}


def vlan_for_ip(ip: str) -> Vlan | None:
    """Which VLAN does this IP address belong to?"""
    addr = ipaddress.ip_address(ip)
    return next((v for v in VLANS.values() if addr in v.subnet), None)


def needs_router(src_ip: str, dst_ip: str) -> bool:
    """Different subnets can't talk directly; traffic must go through the gateway."""
    return vlan_for_ip(src_ip) != vlan_for_ip(dst_ip)


if __name__ == "__main__":
    print(f"{'VLAN':<5} {'Name':<12} {'Subnet':<16} {'Gateway':<12} {'Broadcast':<14} Usable")
    for v in VLANS.values():
        print(f"{v.id:<5} {v.name:<12} {str(v.subnet):<16} {str(v.gateway):<12} "
              f"{str(v.broadcast):<14} {v.usable_hosts}")

    print("\nCan these two talk directly, or do they need the router?")
    for src, dst in [("10.10.10.25", "10.10.10.40"), ("10.10.10.25", "10.10.20.5"),
                     ("10.10.40.7", "10.10.60.20")]:
        a, b = vlan_for_ip(src), vlan_for_ip(dst)
        if needs_router(src, dst):
            verdict = f"different subnets -> send to gateway {a.gateway}"
        else:
            verdict = "same subnet -> deliver directly through the switch"
        print(f"  {src} ({a.name}) -> {dst} ({b.name}): {verdict}")