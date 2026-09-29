import pytest

from netops.scenarios import SCENARIOS, run


def row(result, link):
    h = result["health"]
    return h[h["link"] == link].iloc[0]


def test_there_are_seven_scenarios_plus_normal():
    assert len(SCENARIOS) == 8 and "normal" in SCENARIOS


def test_normal_is_a_clean_reset_state():
    r = run("normal")
    assert (r["health"]["status"] == "OK").all()
    assert r["security_events"] == []


@pytest.mark.parametrize("name", [n for n in SCENARIOS if n != "normal"])
def test_every_scenario_changes_something(name):
    r = run(name)
    assert (r["health"]["status"] != "OK").any() or r["security_events"]


def test_link_failure_reroutes_without_hurting_users():
    r, normal = run("link_failure"), run("normal")
    assert row(r, "ACCESS-2<->DIST-1")["status"] == "DOWN"
    assert row(r, "ACCESS-2<->DIST-2")["load_mbps"] > 0              # the standby took over
    assert r["user_experience"]["eng-pc-1"] == normal["user_experience"]["eng-pc-1"]


def test_congested_uplink_hurts_engineering_only():
    r = run("congested_uplink")
    assert row(r, "ACCESS-2<->DIST-1")["status"] == "CRITICAL"
    assert r["user_experience"]["eng-pc-1"]["loss_pct"] > 5
    assert r["user_experience"]["fin-pc-1"]["loss_pct"] == 0


def test_abnormal_guest_traffic_saturates_the_internet_link():
    assert row(run("abnormal_traffic"), "EDGE<->INTERNET")["status"] == "CRITICAL"


def test_unauthorized_access_is_logged_but_harmless_to_performance():
    r = run("unauthorized_access")
    assert len(r["security_events"]) == 4
    assert all(e["rule"] == "guest-no-internal" for e in r["security_events"])
    assert (r["health"]["status"] == "OK").all()


def test_rogue_iot_is_blocked_but_still_congests_its_uplink():
    r = run("rogue_iot")
    assert len(r["security_events"]) == 3
    assert row(r, "ACCESS-2<->DIST-1")["utilization_pct"] > 100          # denied traffic still costs bandwidth
    assert row(r, "CORE<->DIST-1")["load_mbps"] == row(run("normal"), "CORE<->DIST-1")["load_mbps"]


def test_packet_loss_without_congestion_points_to_a_physical_fault():
    x = row(run("packet_loss"), "ACCESS-1<->DIST-1")
    assert x["loss_pct"] >= 8 and x["utilization_pct"] < 50


def test_high_latency_on_the_wan_leaves_internal_apps_fast():
    r = run("high_latency")
    assert r["user_experience"]["guest-1"]["latency_ms"] > 150
    assert r["user_experience"]["fin-pc-1"]["latency_ms"] < 5