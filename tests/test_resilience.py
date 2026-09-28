from netops.resilience import blast_radius, critical_links, single_points_of_failure
from netops.topology import build_campus


def test_redundant_distribution_switches_are_not_spofs():
    spofs = single_points_of_failure(build_campus())
    assert "DIST-1" not in spofs and "DIST-2" not in spofs


def test_core_edge_and_access_switches_are_spofs():
    assert single_points_of_failure(build_campus()) == ["ACCESS-1", "ACCESS-2", "CORE", "EDGE"]


def test_losing_one_distribution_switch_affects_nobody():
    assert blast_radius(build_campus(), "DIST-1") == {}


def test_losing_an_access_switch_affects_only_its_users():
    impact = blast_radius(build_campus(), "ACCESS-2")
    assert sorted(impact) == ["eng-pc-1", "guest-1", "iot-cam-1"]


def test_losing_the_core_affects_everyone():
    assert len(blast_radius(build_campus(), "CORE")) == 6


def test_edge_router_failure_only_costs_internet():
    impact = blast_radius(build_campus(), "EDGE")
    assert all(lost == ["internet"] for lost in impact.values())


def test_uplinks_are_not_critical_links():
    links = critical_links(build_campus())
    assert ("ACCESS-1", "DIST-1") not in links
    assert ("CORE", "EDGE") in links