from netops.topology import build_campus, nodes_in_layer


def test_campus_has_every_layer():
    g = build_campus()
    assert nodes_in_layer(g, "core") == ["CORE"]
    assert nodes_in_layer(g, "distribution") == ["DIST-1", "DIST-2"]
    assert nodes_in_layer(g, "access") == ["ACCESS-1", "ACCESS-2"]
    assert len(nodes_in_layer(g, "endpoint")) == 6
    assert len(nodes_in_layer(g, "server")) == 3


def test_access_switches_are_dual_homed():
    g = build_campus()
    for access in nodes_in_layer(g, "access"):
        uplinks = [n for n in g.neighbors(access) if g.nodes[n]["layer"] == "distribution"]
        assert sorted(uplinks) == ["DIST-1", "DIST-2"]


def test_every_device_is_reachable():
    import networkx as nx
    assert nx.is_connected(build_campus())
