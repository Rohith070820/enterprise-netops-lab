import pytest

from netops.rca import EXPECTED, accuracy, detect, diagnose
from netops.scenarios import SCENARIOS, run


def test_healthy_network_produces_no_finding():
    assert diagnose("normal") is None
    assert detect(run("normal"), run("normal")) == []


@pytest.mark.parametrize("name", [n for n in EXPECTED if n != "normal"])
def test_engine_names_the_right_culprit(name):
    f = diagnose(name)
    assert (f.category, f.culprit) == EXPECTED[name]


@pytest.mark.parametrize("name", [n for n in SCENARIOS if n != "normal"])
def test_every_finding_is_complete(name):
    f = diagnose(name)
    for part in (f.problem, f.likely_cause, f.impact, f.action):
        assert part
    assert f.evidence and f.confidence in ("High", "Medium", "Low")


def test_every_scenario_has_a_ground_truth():
    assert set(EXPECTED) == set(SCENARIOS)


def test_congestion_evidence_is_compared_with_the_baseline():
    f = diagnose("congested_uplink")
    assert any("vs normal" in e for e in f.evidence)


def test_noisy_neighbor_is_named():
    f = diagnose("abnormal_traffic")
    assert "guest-1" in f.likely_cause and "Engineering" in f.impact


def test_blocked_but_congesting_device_is_flagged_as_compromised_not_just_blocked():
    f = diagnose("rogue_iot")
    assert f.category == "compromised_device" and "Quarantine" in f.action


def test_link_down_with_working_failover_still_warns_about_lost_redundancy():
    f = diagnose("link_failure")
    assert "Redundancy is lost" in f.impact


def test_overall_diagnosis_accuracy_is_100_percent():
    assert accuracy() == (8, 8)