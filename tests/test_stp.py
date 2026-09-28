import networkx as nx

from netops.paths import fail_link, find_path
from netops.stp import active_topology, compute_stp, switch_graph
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


def test_nothing_is_cut_off_in_the_designed_network():
    assert compute_stp(build_campus())["cut_off"] == []


def test_switch_cut_off_from_the_root_becomes_its_own_island():
    r = compute_stp(build_campus(), failed=(("ACCESS-1", "DIST-1"), ("ACCESS-1", "DIST-2")))
    assert r["root"] == "CORE" and r["cut_off"] == ["ACCESS-1"]
    assert "ACCESS-1" not in r["root_ports"]


def test_active_topology_removes_exactly_the_blocked_links():
    g = build_campus()
    active = active_topology(g)
    removed = {tuple(sorted(e)) for e in g.edges} - {tuple(sorted(e)) for e in active.edges}
    assert sorted(removed) == compute_stp(g)["blocked"]
    assert nx.is_tree(switch_graph(active))


def test_wrong_root_sends_failover_traffic_the_long_way_through_an_access_switch():
    g = fail_link(build_campus(), "ACCESS-2", "DIST-1")
    assert find_path(active_topology(g), "ACCESS-2", "CORE") == ["ACCESS-2", "DIST-2", "CORE"]
    detour = find_path(active_topology(g, priorities={}), "ACCESS-2", "CORE")
    assert detour == ["ACCESS-2", "DIST-2", "ACCESS-1", "DIST-1", "CORE"]
