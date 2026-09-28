from netops.paths import fail_device, fail_link, find_path
from netops.topology import build_campus


def test_normal_path_goes_access_distribution_core():
    path = find_path(build_campus(), "fin-pc-1", "fin-srv")
    assert path[0] == "fin-pc-1" and path[-1] == "fin-srv"
    assert path[1] == "ACCESS-1"
    assert path[2] in ("DIST-1", "DIST-2")
    assert path[3] == "CORE"


def test_one_uplink_cut_traffic_fails_over():
    g = fail_link(build_campus(), "ACCESS-1", "DIST-1")
    path = find_path(g, "fin-pc-1", "fin-srv")
    assert path is not None
    assert "DIST-2" in path


def test_distribution_switch_dies_traffic_fails_over():
    g = fail_device(build_campus(), "DIST-1")
    assert find_path(g, "eng-pc-1", "eng-srv") is not None


def test_both_uplinks_cut_user_is_cut_off():
    g = fail_link(fail_link(build_campus(), "ACCESS-1", "DIST-1"), "ACCESS-1", "DIST-2")
    assert find_path(g, "fin-pc-1", "fin-srv") is None


def test_failures_do_not_change_the_original_network():
    g = build_campus()
    fail_link(g, "ACCESS-1", "DIST-1")
    assert g.has_edge("ACCESS-1", "DIST-1")