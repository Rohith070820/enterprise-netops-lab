# Enterprise NetOps Lab

## Purpose
A vendor-neutral "digital twin" of an enterprise campus network, built phase by phase to
prepare for an early-career Product Manager interview on enterprise networking and switching.
Every module teaches one networking concept and is small enough to explain out loud.

## Architecture (keep this layering)
```
Network model -> Traffic/Events -> Telemetry -> Detection -> Root-cause analysis
  -> Recommended action -> Optional LLM explanation -> Dashboard
```
- The analytics are **deterministic**: same seed, same numbers, same findings.
- The LLM layer (Phase 9) may only **rephrase** findings that the deterministic code produced.

## Run it
```
.venv/bin/python -m pytest -q              # full suite (must stay green)
.venv/bin/python -m netops.<module>        # every module has a teaching demo
.venv/bin/python -m netops.scenarios [name]  # all scenarios, or one in detail
```

## Module map
| Layer | Module | What it models |
|---|---|---|
| Model | `topology.py` | Campus graph: INTERNET-EDGE-CORE-DIST-1/2-ACCESS-1/2, endpoints, servers on CORE |
| Model | `addressing.py` | VLANs 10,20,30,40,50,60,99 = 10.10.N.0/24, gateway .1 |
| Model | `inventory.py` | IP/MAC/gateway per device, access/trunk/routed ports, VLAN pruning, ARP |
| Model | `paths.py` | Shortest path, `fail_link`, `fail_device`, `degrade_link` (extra loss/delay) |
| Model | `resilience.py` | Single points of failure, critical links, blast radius |
| Model | `switching.py` | MAC learning, flood/forward/filter/drop per VLAN |
| Model | `packet_walk.py` | One packet hop by hop: DNS, ARP, L2/L3, TTL, NAT |
| Model | `policy.py` | First-match ACL with implicit deny, enforced at the gateway |
| Model | `stp.py` | Root election, root ports, blocked links, islands, `active_topology()` |
| Traffic/Telemetry | `telemetry.py` | Seeded flows pushed along real paths -> link utilization |
| Telemetry | `health.py` | Latency/loss/status derived from load (+ physical faults); baseline |
| Events | `scenarios.py` | Failure/anomaly scenarios with ground truth (see below) |
| Detection/RCA | `rca.py` | *Phase 7, not built yet* |
| Explanation | `explain.py` | *Phase 9, not built yet* |
| Dashboard | `app/dashboard.py` | *Phase 8, not built yet* |

## Phase roadmap
| Phase | Scope | Status |
|---|---|---|
| P1 | Repo skeleton, config, smoke tests | Done |
| P2 | `topology.py`, `paths.py`, `resilience.py` | Done |
| P3 | `addressing.py`, `inventory.py` | Done |
| P4 | `switching.py`, `packet_walk.py`, `policy.py` | Done |
| P5 | `telemetry.py`, `health.py` | Done |
| P6 | Task 1 `stp.py`; Task 2 `scenarios.py` (failure and anomaly scenarios) | Done |
| P7 | `rca.py`: detection + root cause | Next |
| P8 | `app/dashboard.py` | Planned |
| P9 | `explain.py` | Planned |
| P10 | Fresh-clone test pass, README, PRD, metrics | Planned |

### Phase 6 scenarios (the contract Phase 7 builds on)
`scenarios.run(name, seed=42)` returns an `Outcome` with `links` (every cable: state
UP/BLOCKED/DOWN, utilization, latency, loss, status), `flows` (ACL result, matched rule,
path, experience, impact vs a normal day), `security_events` (every DENIED flow:
src, dst, port, rule), `affected_users`, and the `stp` result. Each `Scenario` records its
ground truth: `culprit` (a link, device, flow source or rule) and `category`, one of
`CATEGORIES` = none, failure, congestion, abnormal-traffic, security, physical-fault,
provider, config. `"normal"` is the reset state.

Scenarios cover the 7 required types: switch/link failure (`uplink-cut`, `dist-down`,
`access-down`, `core-down`, `isp-down`, `server-down`), congested uplink (`big-download`),
abnormal high traffic (`guest-surge`), unauthorized VLAN access (`guest-probe`), IoT
behaving abnormally (`iot-anomaly`), packet loss (`bad-optic`), high latency (`isp-slow`);
plus config mistakes (`acl-mistake`, `stp-wrong-root`, `stp-off`).

### Next phases
- **P7 `rca.py`**: detection (thresholds + deviation from the `health.build_baseline`
  baseline), topology correlation to find the shared cause, and a structured finding:
  problem, likely cause, evidence, business impact, recommended action, confidence.
  Validate it against each scenario's ground-truth culprit (without reading it during analysis).
- **P8 `app/dashboard.py`**: Streamlit + Plotly topology view (VLAN colors, DOWN/BLOCKED
  links), health metrics, scenario picker with reset, findings and security panels.
- **P9 `explain.py`**: a template explanation by default; optional LLM behind a flag or
  env var; must work with no API key.
- **P10**: full test pass from a fresh clone. Then README (Mermaid diagram), mini PRD,
  roadmap and metrics (MTTD, MTTI, MTTR, false-positive rate).

## Conventions
- Every module has a `python -m netops.<module>` demo in its `if __name__ == "__main__":` block.
- Tests live in `tests/test_<module>.py`, are named after the rule they prove, and are
  seeded and deterministic (seed 42 unless the test is about seeds).
- **No invented metrics**: every number is derived from the model (topology, flows, ACL,
  injected faults). Scenarios change the model and recompute; they never type in results.
- Plain-English docstrings that teach the networking concept, not just the code.
- Python 3.10+ syntax (`X | None`, built-in generics). Match the surrounding style.
- No new dependencies without asking (current: networkx, pandas, plotly, streamlit, pytest).
- Do not change behavior that existing tests assert; add tests for every fix.

## Do not
- Do not use Cisco, Catalyst, ISE, SD-Access (or any vendor) branding in code, and do not
  claim to implement those products. The lab is vendor-neutral.
- The LLM layer never adds facts: it may only rephrase the deterministic findings.
- Do not push or change git history without being asked.

## Known open items
- `packet_walk` ignores the ACL (it shows denied traffic being delivered).
- `resilience.blast_radius` ignores the ACL, and crashes if the failed device is an endpoint or INTERNET.
- STP is one tree for all VLANs while ACCESS trunks are pruned per switch, so "wrong root +
  failure" detours are only modeled as STP paths, not as VLAN traffic.
- The broadcast storm (`stp-off`) is simplified: each flooded link is filled to capacity.
- `README.md` is empty; `pyproject.toml` has no `[project]` metadata or `requires-python`.
