import pytest

from netops.resilience import blast_radius
from netops.scenarios import CATEGORIES, SCENARIOS, Scenario, run, storm_links
from netops.stp import active_topology
from netops.topology import build_campus

EVERYONE = ["eng-pc-1", "fin-pc-1", "guest-1", "hr-pc-1"]   # every user who has traffic


def link(out, name):
    return out.links.set_index("link").loc[name]


def flow(out, src, dst):
    f = out.flows
    return f[(f["src"] == src) & (f["dst"] == dst)].iloc[0]


def statuses(out):
    return out.links.set_index("link")["status"].sort_index()


def test_normal_day_is_clean_nobody_hurt_no_security_events_only_stp_blocks_links():
    out = run("normal")
    assert out.affected_users == [] and set(out.flows["impact"]) == {"none"}
    assert out.security_events.empty
    blocked = out.links.loc[out.links["state"] == "BLOCKED", "link"]
    assert sorted(blocked) == ["ACCESS-1<->DIST-2", "ACCESS-2<->DIST-2", "DIST-1<->DIST-2"]
    assert (out.links.loc[out.links["state"] == "UP", "status"] == "OK").all()


def test_every_scenario_records_ground_truth_culprit_and_category():
    for s in SCENARIOS.values():
        assert (s.culprit is None) == (s.name == "normal")
        assert s.category in CATEGORIES
        assert (s.category == "none") == (s.name == "normal")


@pytest.mark.parametrize("name", [n for n in SCENARIOS if n != "normal"])
def test_every_fault_leaves_a_symptom_a_bad_link_or_a_security_event(name):
    out, usual = run(name), statuses(run("normal"))
    now = statuses(out)
    worse = now[(now != "OK") & (now != usual.reindex(now.index))]
    assert len(worse) > 0 or len(out.security_events) > 0


def test_every_scenario_accounts_for_every_cable_exactly_once():
    cables = sorted("<->".join(sorted(e)) for e in build_campus().edges)
    for name in SCENARIOS:
        assert sorted(run(name).links["link"]) == cables


def test_traffic_only_ever_crosses_cables_that_are_up():
    for name in SCENARIOS:
        out = run(name)
        up = set(out.links.loc[out.links["state"] == "UP", "link"])
        for path in out.flows["path"]:
            hops = path.split(" > ")
            assert all("<->".join(sorted(hop)) in up for hop in zip(hops, hops[1:]))


def test_uplink_cut_stp_unblocks_the_backup_and_nobody_notices():
    normal, out = run("normal"), run("uplink-cut")
    assert link(out, "ACCESS-2<->DIST-1")["state"] == "DOWN"
    assert link(out, "ACCESS-2<->DIST-2")["state"] == "UP"
    assert link(out, "ACCESS-2<->DIST-2")["load_mbps"] == link(normal, "ACCESS-2<->DIST-1")["load_mbps"]
    assert out.affected_users == []


def test_losing_one_distribution_switch_is_absorbed_by_the_other():
    out = run("dist-down")
    assert all("DIST-2" in path for path in out.flows["path"])
    assert set(out.links.loc[out.links["link"].str.contains("DIST-1"), "state"]) == {"DOWN"}
    assert out.affected_users == []


def test_access_switch_failure_cuts_off_only_its_own_users():
    out = run("access-down")
    assert out.affected_users == ["fin-pc-1", "hr-pc-1"]
    theirs = out.flows[out.flows["src"].isin(["fin-pc-1", "hr-pc-1"])]
    assert set(theirs["status"]) == {"UNREACHABLE"} and set(theirs["impact"]) == {"lost"}


def test_core_failure_cuts_everyone_off_from_everything():
    out = run("core-down")
    assert set(out.flows["impact"]) == {"lost"}
    assert out.affected_users == EVERYONE


def test_isp_outage_costs_the_internet_but_internal_apps_keep_working():
    f = run("isp-down").flows
    assert set(f.loc[f["dst"] == "internet", "impact"]) == {"lost"}
    assert set(f.loc[f["dst"] != "internet", "impact"]) == {"none"}


def test_server_crash_is_not_a_network_problem():
    out = run("server-down")
    assert out.affected_users == ["fin-pc-1"]
    assert flow(out, "fin-pc-1", "fin-srv")["impact"] == "lost"
    assert flow(out, "fin-pc-1", "internet")["impact"] == "none"
    assert (out.links.loc[out.links["state"] == "UP", "status"] == "OK").all()   # every working cable is fine


def test_big_download_congests_the_shared_uplink_and_hurts_the_neighbors():
    out = run("big-download")
    uplink = link(out, "ACCESS-2<->DIST-1")
    assert 94 <= uplink["utilization_pct"] <= 98 and uplink["status"] == "CRITICAL"
    assert out.affected_users == ["eng-pc-1", "guest-1"]          # guest-1 shares ACCESS-2's uplink
    assert "fin-pc-1" not in out.affected_users                   # Finance is on the other access switch
    assert out.flows.loc[out.flows["app"] == "huge-download", "impact"].item() == "new"


def test_abnormal_guest_traffic_fills_the_internet_link_and_hurts_its_noisy_neighbor():
    out = run("guest-surge")
    wan = link(out, "EDGE<->INTERNET")
    assert wan["utilization_pct"] >= 90 and wan["status"] == "CRITICAL"
    assert flow(out, "eng-pc-1", "eng-srv")["impact"] == "degraded"   # internal traffic, hurt via ACCESS-2's uplink
    assert flow(out, "fin-pc-1", "fin-srv")["impact"] == "none"
    assert out.security_events.empty                                   # allowed traffic, just far too much of it


def test_guest_probing_finance_is_blocked_and_logged_but_is_no_performance_problem():
    out = run("guest-probe")
    events = out.security_events
    assert sorted(events["port"]) == [22, 443, 445, 3389]
    assert set(zip(events["src"], events["dst"], events["rule"])) == {("guest-1", "fin-srv", "guest-no-internal")}
    assert statuses(out).equals(statuses(run("normal")))                # no link changes status
    assert out.affected_users == []


def test_misbehaving_camera_is_blocked_yet_its_denied_traffic_still_floods_the_uplink():
    out, normal = run("iot-anomaly"), run("normal")
    events = out.security_events
    assert len(events) == 3 and set(events["src"]) == {"iot-cam-1"}
    assert set(events["rule"]) == {"iot-no-internal", "implicit deny"}
    assert link(out, "ACCESS-2<->DIST-1")["utilization_pct"] > 100      # dropped only at the gateway
    for core_link in ("CORE<->DIST-1", "CORE<->DIST-2"):
        assert link(out, core_link)["load_mbps"] == link(normal, core_link)["load_mbps"]
    assert out.affected_users == ["eng-pc-1", "guest-1"]


def test_loss_without_congestion_points_to_a_physical_fault():
    out = run("bad-optic")
    uplink = link(out, "ACCESS-1<->DIST-1")
    assert uplink["utilization_pct"] < 20 and uplink["loss_pct"] == 8.0
    assert uplink["status"] == "CRITICAL"
    assert out.affected_users == ["fin-pc-1", "hr-pc-1"]              # everyone behind that uplink


def test_provider_delay_slows_the_internet_but_not_internal_apps():
    out, normal = run("isp-slow"), run("normal")
    wan = link(out, "EDGE<->INTERNET")
    assert wan["utilization_pct"] == link(normal, "EDGE<->INTERNET")["utilization_pct"]
    assert wan["latency_ms"] >= 150 and wan["status"] == "CRITICAL"
    f = out.flows
    assert set(f.loc[f["dst"] == "internet", "impact"]) == {"degraded"}
    assert flow(out, "fin-pc-1", "fin-srv")["latency_ms"] < 5


def test_deleted_acl_rule_drops_finance_traffic_at_its_gateway():
    out = run("acl-mistake")
    fin = flow(out, "fin-pc-1", "fin-srv")
    assert (fin["status"], fin["impact"]) == ("DENIED", "lost")
    assert fin["path"].endswith("DIST-1")
    assert link(out, "CORE<->fin-srv")["load_mbps"] == 0            # the finance server goes quiet
    assert out.affected_users == ["fin-pc-1"]
    assert out.security_events["rule"].tolist() == ["implicit deny"]   # yesterday allowed, today a deny log


def test_wiped_stp_priorities_move_the_root_but_nobody_notices_yet():
    out = run("stp-wrong-root")
    assert out.stp["root"] == "ACCESS-1"
    assert link(out, "CORE<->DIST-2")["state"] == "BLOCKED"        # DIST-2 reaches the core only via ACCESS-1
    assert out.affected_users == []


def test_without_stp_a_broadcast_storm_floods_every_switch_port():
    out = run("stp-off")
    assert out.stp is None and "BLOCKED" not in set(out.links["state"])
    flooded = out.links[out.links["link"].isin(storm_links(build_campus()))]
    assert len(flooded) == 16 and (flooded["utilization_pct"] >= 100).all()
    assert set(flooded["status"]) == {"CRITICAL"}
    assert link(out, "EDGE<->INTERNET")["status"] == "OK"           # routers do not forward broadcasts
    assert out.affected_users == EVERYONE


def test_a_storm_needs_a_loop():
    g = build_campus()
    assert "DIST-1<->DIST-2" in storm_links(g) and "CORE<->EDGE" not in storm_links(g)
    assert storm_links(active_topology(g)) == []                    # STP already cut every loop


def test_same_seed_gives_the_same_outcome():
    a, b = run("big-download", seed=7), run("big-download", seed=7)
    assert a.links.equals(b.links) and a.flows.equals(b.flows)
    assert not a.links.equals(run("big-download", seed=8).links)


def test_scenario_impact_never_exceeds_the_blast_radius():
    g = build_campus()
    for name in ("dist-down", "access-down", "core-down"):
        device = SCENARIOS[name].failed_devices[0]
        assert set(run(name).affected_users) <= set(blast_radius(g, device))


def test_custom_double_failure_leaves_access_2_on_its_own_island():
    double = Scenario("double", "DIST-1 dies while ACCESS-2's other uplink is unplugged", "device failure",
                      "DIST-1", failed_links=(("ACCESS-2", "DIST-2"),), failed_devices=("DIST-1",))
    out = run(double)
    assert out.stp["cut_off"] == ["ACCESS-2"]
    assert out.affected_users == ["eng-pc-1", "guest-1"]
