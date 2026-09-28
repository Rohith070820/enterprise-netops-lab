import ipaddress
from itertools import combinations

from netops.addressing import VLANS, needs_router, vlan_for_ip


def test_every_vlan_follows_the_addressing_plan():
    for vid, v in VLANS.items():
        assert str(v.subnet) == f"10.10.{vid}.0/24"
        assert str(v.gateway) == f"10.10.{vid}.1"
        assert str(v.broadcast) == f"10.10.{vid}.255"
        assert v.usable_hosts == 254


def test_vlan_ids_are_valid_802_1q_ids():
    assert all(1 <= vid <= 4094 for vid in VLANS)


def test_subnets_never_overlap():
    for a, b in combinations(VLANS.values(), 2):
        assert not a.subnet.overlaps(b.subnet)


def test_every_subnet_is_private_address_space():
    assert all(v.subnet.is_private for v in VLANS.values())


def test_ip_maps_to_the_right_vlan():
    assert vlan_for_ip("10.10.20.5").name == "Finance"
    assert vlan_for_ip("10.10.50.33").name == "IoT"
    assert vlan_for_ip("8.8.8.8") is None


def test_same_subnet_goes_direct_different_subnet_needs_router():
    assert needs_router("10.10.10.25", "10.10.10.40") is False
    assert needs_router("10.10.10.25", "10.10.20.5") is True