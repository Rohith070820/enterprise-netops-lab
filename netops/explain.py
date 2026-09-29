"""Phase 9: the explanation layer (optional LLM).

The root-cause engine (rca.py) DECIDES. This module only REPHRASES its finding
for a non-technical reader. Two ways to do it:

1. template  (default, free, always works): fills a fixed sentence pattern
2. LLM       (optional): only if ANTHROPIC_API_KEY is set and the `anthropic`
             package is installed. The model receives the finding as JSON and is
             told to use only those facts.

Guardrail: every number in the LLM's text must appear in the finding. If the
model invents a number, or anything fails, we fall back to the template.
The diagnosis never depends on the LLM.
"""
import json
import os
import re
from dataclasses import asdict

from netops.rca import Finding

DEFAULT_MODEL = os.environ.get("NETOPS_LLM_MODEL", "claude-haiku-4-5-20251001")

PROMPT = """You are helping a network administrator brief their manager.
Rewrite the diagnosis below in plain English, in at most 3 short sentences.
Rules:
- Use ONLY the facts in the JSON. Do not add causes, numbers, devices or advice that are not in it.
- Keep any numbers exactly as written.
- Say what is wrong, who is affected, and what will be done.

Diagnosis JSON:
{finding}"""


def _mid_sentence(s: str) -> str:
    """'Rate-limit ...' -> 'rate-limit ...', but leave names like 'ACCESS-2' alone."""
    return s[0].lower() + s[1:] if len(s) > 1 and s[1].islower() else s


def template_explanation(f: Finding | None) -> str:
    if f is None:
        return "The network is healthy. Nothing needs attention right now."
    cause = _mid_sentence(f.likely_cause.rstrip("."))
    return f"{f.problem} The most likely reason: {cause}. {f.impact} Next step: {_mid_sentence(f.action)}"


def build_prompt(f: Finding) -> str:
    return PROMPT.format(finding=json.dumps(asdict(f), indent=2))


def _numbers(text: str) -> set[str]:
    return {n.rstrip(".") for n in re.findall(r"\d+(?:\.\d+)?", text)}


def numbers_are_grounded(text: str, f: Finding) -> bool:
    """True if every number in `text` also appears somewhere in the finding."""
    return _numbers(text) <= _numbers(json.dumps(asdict(f)))


def llm_explanation(f: Finding, client=None, model: str = DEFAULT_MODEL) -> str | None:
    """Ask an LLM to rephrase the finding. Returns None if no LLM is available."""
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None
        try:
            import anthropic
        except ImportError:
            return None
        client = anthropic.Anthropic()
    reply = client.messages.create(model=model, max_tokens=300,
                                   messages=[{"role": "user", "content": build_prompt(f)}])
    return reply.content[0].text.strip()


def explain(f: Finding | None, client=None) -> tuple[str, str]:
    """Returns (text, source) where source is 'llm' or 'template'."""
    if f is None:
        return template_explanation(f), "template"
    try:
        text = llm_explanation(f, client)
    except Exception:                      # network error, bad key, rate limit...
        text = None
    if text and numbers_are_grounded(text, f):
        return text, "llm"
    return template_explanation(f), "template"


if __name__ == "__main__":
    from netops.rca import diagnose
    from netops.scenarios import SCENARIOS

    for name in SCENARIOS:
        text, source = explain(diagnose(name))
        print(f"[{name}] ({source})\n  {text}\n")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("No ANTHROPIC_API_KEY set, so every summary above came from the template.")