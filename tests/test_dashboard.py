from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from netops.scenarios import SCENARIOS


def app():
    dashboard = Path(__file__).resolve().parents[1] / "app" / "dashboard.py"
    return AppTest.from_file(str(dashboard), default_timeout=30)


def test_dashboard_starts_without_errors():
    at = app().run()
    assert not at.exception
    assert at.title[0].value == "Enterprise NetOps Lab"


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_every_scenario_renders(name):
    at = app().run()
    at.sidebar.radio[0].set_value(name).run()
    assert not at.exception


def test_congestion_scenario_shows_the_finding():
    at = app().run()
    at.sidebar.radio[0].set_value("congested_uplink").run()
    text = " ".join(m.value for m in at.markdown)
    assert "ACCESS-2<->DIST-1 is saturated" in text


def test_reset_returns_to_normal():
    at = app().run()
    at.sidebar.radio[0].set_value("rogue_iot").run()
    at.sidebar.button[0].click().run()
    assert at.sidebar.radio[0].value == "normal"