from netops.health import build_baseline, latency_ms, link_health, loss_pct, path_experience, status
from netops.telemetry import Flow, generate_flows
from netops.topology import build_campus


def test_latency_grows_as_the_link_fills():
    assert latency_ms("uplink", 0) == 0.5
    assert latency_ms("uplink", 50) == 1.0            # half full -> twice the delay
    assert latency_ms("uplink", 90) > latency_ms("uplink", 50) * 4


def test_no_loss_until_80_percent_then_loss_rises():
    assert loss_pct(79) == 0.0
    assert 0 < loss_pct(90) < loss_pct(96) < 15
    assert loss_pct(150) > 30                          # a third of the traffic cannot fit


def test_status_thresholds():
    assert status(50, 0) == "OK"
    assert status(75, 0) == "WARNING"
    assert status(96, 9.6) == "CRITICAL"


def test_big_download_turns_engineering_uplink_critical():
    g = build_campus()
    big = Flow("eng-pc-1", "eng-srv", "huge-download", 450.0)
    df = link_health(g, generate_flows(seed=42, extra=[big]))
    row = df[df["link"] == "ACCESS-2<->DIST-1"].iloc[0]
    assert row["status"] == "CRITICAL" and row["loss_pct"] > 0


def test_user_experience_gets_worse_under_congestion():
    g = build_campus()
    normal = path_experience(g, link_health(g, generate_flows(seed=42)), "eng-pc-1", "eng-srv")
    big = Flow("eng-pc-1", "eng-srv", "huge-download", 450.0)
    busy = path_experience(g, link_health(g, generate_flows(seed=42, extra=[big])), "eng-pc-1", "eng-srv")
    assert busy["latency_ms"] > normal["latency_ms"] and busy["loss_pct"] > normal["loss_pct"]


def test_baseline_captures_normal_range():
    base = build_baseline(build_campus()).set_index("link")
    assert 40 < base.loc["ACCESS-2<->DIST-1", "normal_util_pct"] < 60
    assert base.loc["ACCESS-2<->DIST-1", "normal_spread"] > 0