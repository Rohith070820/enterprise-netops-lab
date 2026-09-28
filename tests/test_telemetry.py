from netops.policy import ACL
from netops.telemetry import Flow, flow_path, generate_flows, link_utilization
from netops.topology import build_campus


def util(df, link):
    return df.loc[df["link"] == link, "utilization_pct"].item()


def test_same_seed_gives_identical_telemetry():
    g = build_campus()
    a = link_utilization(g, generate_flows(seed=7))
    b = link_utilization(g, generate_flows(seed=7))
    assert a.equals(b)


def test_different_seed_gives_different_traffic():
    assert generate_flows(seed=1) != generate_flows(seed=2)


def test_utilization_is_sum_of_flows_over_capacity():
    g = build_campus()
    flows = [Flow("eng-pc-1", "eng-srv", "test", 250.0), Flow("guest-1", "internet", "test", 250.0)]
    df = link_utilization(g, flows)
    assert util(df, "ACCESS-2<->eng-pc-1") == 25.0          # 250 of 1000
    assert util(df, "ACCESS-2<->DIST-1") == 50.0            # both flows share the uplink
    assert util(df, "EDGE<->INTERNET") == 25.0              # only the guest flow leaves


def test_denied_flow_loads_links_only_up_to_the_gateway():
    g = build_campus()
    path, status = flow_path(g, Flow("iot-cam-1", "fin-srv", "probe", 100.0, port=445))
    assert status == "DENIED"
    assert path[-1] == "DIST-1" and "CORE" not in path


def test_no_traffic_means_zero_utilization():
    df = link_utilization(build_campus(), [])
    assert df["utilization_pct"].sum() == 0


def test_deleting_a_rule_turns_allowed_traffic_into_denied():
    g = build_campus()
    erp = Flow("fin-pc-1", "fin-srv", "erp", 80.0)
    without_finance_rule = [r for r in ACL if r.name != "fin-to-fin-server"]
    assert flow_path(g, erp)[1] == "ALLOWED"
    assert flow_path(g, erp, without_finance_rule)[1] == "DENIED"


def test_denied_server_flow_is_dropped_at_its_first_layer_3_hop():
    path, status = flow_path(build_campus(), Flow("eng-srv", "internet", "update", 10.0))   # servers: implicit deny
    assert (status, path) == ("DENIED", ["eng-srv", "CORE"])                             # no distribution hop
