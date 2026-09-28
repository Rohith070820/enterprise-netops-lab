import networkx as nx

from netops.paths import find_path
from netops.stp import compute_stp, switch_graph
from netops.topology import build_campus


def forwarding_tree(g, result):
    return nx.Graph(result["forwarding"])


def test_redundant_switch_links_form_loops():
    assert len(nx.cycle_basis(switch_graph(build_campus()))) == 3


def test_core_is_root_when_configured():
    assert compute_stp(build_campus())["root"] == "CORE"


def test_stp_leaves_a_loop_free_tree_that_reaches_every_switch():
    g = build_campus()
    r = compute_stp(g)
    tree = forwarding_tree(g, r)
    assert nx.is_tree(tree) and set(tree) == set(switch_graph(g))
    assert len(r["blocked"]) == 3


def test_each_access_switch_forwards_on_exactly_one_uplink():
    r = compute_stp(build_campus())
    for access in ("ACCESS-1", "ACCESS-2"):
        uplinks = [l for l in r["forwarding"] if access in l]
        assert len(uplinks) == 1


def test_default_priorities_elect_the_wrong_root():
    assert compute_stp(build_campus(), priorities={})["root"] == "ACCESS-1"


def test_blocked_link_takes_over_after_a_failure():
    g = build_campus()
    before = compute_stp(g)
    after = compute_stp(g, failed=(("ACCESS-2", "DIST-1"),))
    assert ("ACCESS-2", "DIST-2") in before["blocked"]
    assert ("ACCESS-2", "DIST-2") in after["forwarding"]
    assert nx.is_tree(forwarding_tree(g, after))


def test_traffic_paths_follow_the_spanning_tree():
    g = build_campus()
    r = compute_stp(g)
    path = find_path(g, "ACCESS-2", "CORE")
    for a, b in zip(path, path[1:]):
        assert tuple(sorted((a, b))) in r["forwarding"]