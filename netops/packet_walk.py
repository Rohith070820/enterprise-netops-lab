"""Phase 4, Task 2: follow one packet, hop by hop.

Laptop -> access switch -> distribution (gateway) -> core -> edge router (NAT) -> internet.
At each hop we show what that device looks at and what it changes:
- switches (Layer 2) read MAC addresses and VLAN tags
- routers (Layer 3) read IP addresses, decrement TTL and rewrite MAC addresses
- the edge router also rewrites the private source IP to a public one (NAT)
"""
from netops.addressing import vlan_for_ip
from netops.inventory import arp_resolve, build_inventory
from netops.paths import find_path
from netops.topology import build_campus

# Internal DNS for our servers, plus one public site.
# 203.0.113.x and 198.51.100.x are documentation-only ranges (RFC 5737), safe for examples.
DNS = {
    "eng.corp.local": "10.10.60.10",
    "finance.corp.local": "10.10.60.20",
    "hr.corp.local": "10.10.60.30",
    "www.example.com": "203.0.113.10",
}
PUBLIC_IP = "198.51.100.7"          # the one public address the whole campus shares
WELL_KNOWN_PORTS = {"https": ("TCP", 443), "dns": ("UDP", 53)}


def packet_walk(src: str, hostname: str, app: str = "https") -> list[str]:
    g = build_campus()
    inv = build_inventory(g)
    me = inv[src]
    proto, dport = WELL_KNOWN_PORTS[app]
    sport = 51514                   # a random-looking "ephemeral" source port the laptop picks
    ttl = 64
    steps = []

    # 1. DNS: turn the name into an IP address.
    dst_ip = DNS[hostname]
    steps.append(f"DNS      {hostname} resolves to {dst_ip} (asked over UDP port 53)")

    # 2. Same subnet or not? ARP for the destination or for the gateway.
    hop_ip, hop_mac = arp_resolve(inv, src, dst_ip)
    same_subnet = hop_ip == dst_ip
    steps.append(f"ARP      {src} needs a MAC for {hop_ip} -> {hop_mac}"
                 + ("" if same_subnet else " (the gateway, because the destination is in another subnet)"))
    steps.append(f"SEND     {proto} {me.ip}:{sport} -> {dst_ip}:{dport}  TTL={ttl}")

    # 3. Walk the physical path.
    is_internet = vlan_for_ip(dst_ip) is None     # not in any of our VLANs = outside the campus
    dst_node = "INTERNET" if is_internet else next(d.name for d in inv.values() if str(d.ip) == dst_ip)
    path = find_path(g, src, dst_node)
    src_ip, src_port = str(me.ip), sport

    for prev, hop, nxt in zip(path, path[1:], path[2:] + [None]):
        layer = g.nodes[hop]["layer"]
        if layer == "access":
            steps.append(f"{hop:<8} L2: learns {src}'s MAC, forwards by MAC, "
                         f"tags frame 802.1Q VLAN {me.vlan} onto trunk to {nxt}")
        elif layer in ("distribution", "core") and same_subnet:
            steps.append(f"{hop:<8} L2: same VLAN, just switches the frame to {nxt}")
        elif layer in ("distribution", "core"):
            ttl -= 1
            role = f"gateway for VLAN {me.vlan}, " if layer == "distribution" else ""
            steps.append(f"{hop:<8} L3: {role}routes on destination IP {dst_ip}, TTL -> {ttl}, "
                         f"new MACs for the hop to {nxt}")
        elif layer == "edge":
            ttl -= 1
            steps.append(f"{hop:<8} L3 + NAT: {src_ip}:{src_port} -> {PUBLIC_IP}:40001, TTL -> {ttl}")
            src_ip, src_port = PUBLIC_IP, 40001
        elif hop == "INTERNET":
            steps.append(f"INTERNET reaches {dst_ip}:{dport}; the site sees the sender as {src_ip}:{src_port}")
        else:
            steps.append(f"{hop:<8} delivered: {proto} port {dport} from {src_ip}:{src_port}")
    return steps


if __name__ == "__main__":
    for src, name in [("fin-pc-1", "www.example.com"), ("fin-pc-1", "finance.corp.local"),
                      ("eng-srv", "finance.corp.local")]:
        print(f"\n=== {src} opens https://{name} ===")
        for step in packet_walk(src, name):
            print("  " + step)