from types import SimpleNamespace

from netops.explain import build_prompt, explain, numbers_are_grounded, template_explanation
from netops.rca import diagnose


class FakeLLM:
    """Stands in for the real API, so tests never need a key or a network."""
    def __init__(self, reply):
        self.reply, self.prompts = reply, []
        self.messages = self

    def create(self, **kwargs):
        self.prompts.append(kwargs["messages"][0]["content"])
        if isinstance(self.reply, Exception):
            raise self.reply
        return SimpleNamespace(content=[SimpleNamespace(text=self.reply)])


def test_template_works_without_any_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, source = explain(diagnose("congested_uplink"))
    assert source == "template"
    assert "Engineering" in text and "Rate-limit" not in text and "rate-limit" in text


def test_healthy_network_has_a_calm_summary():
    assert "healthy" in template_explanation(None)


def test_prompt_contains_the_facts_and_the_rules():
    prompt = build_prompt(diagnose("packet_loss"))
    assert "ACCESS-1<->DIST-1" in prompt and "Use ONLY the facts" in prompt


def test_grounded_llm_answer_is_used():
    f = diagnose("congested_uplink")
    llm = FakeLLM("The Engineering uplink is at 95.8%, so builds are slow. We will rate-limit the transfer.")
    text, source = explain(f, client=llm)
    assert source == "llm" and "95.8" in text
    assert len(llm.prompts) == 1


def test_llm_that_invents_a_number_is_rejected():
    f = diagnose("congested_uplink")
    llm = FakeLLM("The uplink is at 99% and 300 users are down.")
    text, source = explain(f, client=llm)
    assert source == "template"


def test_llm_failure_falls_back_to_template():
    text, source = explain(diagnose("rogue_iot"), client=FakeLLM(TimeoutError("no network")))
    assert source == "template" and "iot-cam-1" in text


def test_grounding_check():
    f = diagnose("packet_loss")
    assert numbers_are_grounded("8.0% loss at 17.5% load", f)
    assert not numbers_are_grounded("12% loss", f)