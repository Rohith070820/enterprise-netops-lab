from netops.addressing import VLANS
from netops.inventory import arp_resolve, build_inventory, gateway_mac, port_mode, vlans_on_link
from netops.topology import build_campus


def setup():
    g = build_campus()
    return g, build_inventory(g)


def test_every_endpoint_and_server_has_an_identity():
    g, inv = setup()
    users_and_servers = [n for n, d in g.nodes(data=True) if d["layer"] in ("endpoint", "server")]
    assert sorted(inv) == sorted(users_and_servers)


def test_every_ip_sits_inside_its_vlan_subnet_with_the_right_gateway():
    _, inv = setup()
    for d in inv.values():
        assert d.ip in VLANS[d.vlan].subnet
        assert d.gateway == VLANS[d.vlan].gateway
        assert d.ip != d.gateway


def test_ips_and_macs_are_unique():
    _, inv = setup()
    assert len({d.ip for d in inv.values()}) == len(inv)
    assert len({d.mac for d in inv.values()}) == len(inv)


def test_endpoint_ports_are_access_and_switch_links_are_trunks():
    g, _ = setup()
    assert port_mode(g, "ACCESS-1", "fin-pc-1") == "access"
    assert port_mode(g, "ACCESS-1", "DIST-1") == "trunk"


def test_links_to_the_router_are_routed_ports_that_carry_no_vlans():
    g, inv = setup()
    for a, b in (("CORE", "EDGE"), ("EDGE", "INTERNET")):
        assert port_mode(g, a, b) == "routed" and vlans_on_link(g, inv, a, b) == []


def test_access_port_carries_one_vlan_uplink_carries_only_its_switchs_vlans():
    g, inv = setup()
    assert vlans_on_link(g, inv, "ACCESS-1", "fin-pc-1") == [20]
    assert vlans_on_link(g, inv, "ACCESS-2", "DIST-1") == [10, 40, 50]


def test_arp_same_subnet_resolves_the_host_other_subnet_resolves_the_gateway():
    _, inv = setup()
    assert arp_resolve(inv, "fin-pc-1", "10.10.60.20") == ("10.10.20.1", gateway_mac(20))
    assert arp_resolve(inv, "eng-srv", "10.10.60.20") == ("10.10.60.20", inv["fin-srv"].mac)


def test_arp_for_a_missing_host_gets_no_reply():
    _, inv = setup()
    assert arp_resolve(inv, "guest-1", "10.10.40.99") == ("10.10.40.99", None)