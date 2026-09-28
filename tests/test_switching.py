from netops.inventory import build_inventory, gateway_mac
from netops.switching import BROADCAST, Frame, Switch
from netops.topology import build_campus


def access1():
    g = build_campus()
    inv = build_inventory(g)
    return Switch(g, inv, "ACCESS-1"), inv


def test_broadcast_floods_only_within_its_vlan():
    sw, inv = access1()
    decision, out = sw.receive(Frame(inv["fin-pc-1"].mac, BROADCAST, 20), "fin-pc-1")
    assert decision == "flooded"
    assert sorted(out) == ["DIST-1", "DIST-2"]          # not hr-pc-1 (VLAN 30), not ap-1 (VLAN 99)


def test_switch_learns_the_source_mac():
    sw, inv = access1()
    sw.receive(Frame(inv["fin-pc-1"].mac, BROADCAST, 20), "fin-pc-1")
    assert sw.mac_table[(20, inv["fin-pc-1"].mac)] == "fin-pc-1"


def test_known_destination_is_forwarded_out_one_port():
    sw, inv = access1()
    sw.receive(Frame(gateway_mac(20), BROADCAST, 20), "DIST-1")           # switch learns the gateway
    decision, out = sw.receive(Frame(inv["fin-pc-1"].mac, gateway_mac(20), 20), "fin-pc-1")
    assert (decision, out) == ("forwarded", ["DIST-1"])


def test_unknown_unicast_never_leaks_into_another_vlan():
    sw, inv = access1()
    _, out = sw.receive(Frame(inv["hr-pc-1"].mac, "02:00:00:1e:00:99", 30), "hr-pc-1")
    assert "fin-pc-1" not in out and "ap-1" not in out


def test_vlan_not_allowed_on_trunk_is_dropped():
    sw, _ = access1()
    decision, out = sw.receive(Frame("02:00:00:28:00:15", BROADCAST, 40), "DIST-1")
    assert decision.startswith("dropped") and out == []


def test_same_mac_in_different_vlans_is_tracked_separately():
    sw, _ = access1()
    sw.receive(Frame("02:aa:aa:aa:aa:aa", BROADCAST, 20), "fin-pc-1")
    sw.receive(Frame("02:aa:aa:aa:aa:aa", BROADCAST, 30), "hr-pc-1")
    assert sw.mac_table[(20, "02:aa:aa:aa:aa:aa")] == "fin-pc-1"
    assert sw.mac_table[(30, "02:aa:aa:aa:aa:aa")] == "hr-pc-1"