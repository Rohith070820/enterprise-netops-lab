# Mini PRD: AI-Assisted Network Troubleshooting

*Status: MVP built as a vendor-neutral lab. Targets marked "hypothesis" are assumptions to validate with customers, not measured results.*

## 1. Problem
Network administrators spend too long working out **why** something is wrong. Monitoring tools report symptoms (a busy link, a slow app, a blocked connection) across separate performance and security views. One incident can raise dozens of alerts, and most problems are still discovered by user complaints.

## 2. Personas
| Persona | Role | Needs | Pain today |
|---|---|---|---|
| **Priya, network administrator** (primary) | Runs the campus network for ~2,000 employees with a team of 3 | Know what broke, where, and what to do, fast | Correlates alerts by hand across tools; 2 a.m. pages with no context |
| **Marcus, IT director** | Owns uptime and budget | Business impact in plain language; evidence for upgrade decisions | Gets technical alerts he can't act on |
| **Dana, security analyst** | Watches for threats | See blocked and suspicious traffic with network context | Security events arrive without knowing who is affected |

## 3. Hypothesis
If telemetry is automatically correlated into a probable cause with evidence, impact and a recommended action, administrators will identify problems faster (lower MTTI) and trust the tool enough to act on it.

## 4. Goals and non-goals
**Goals (MVP):** detect and explain the most common campus failure types; show evidence for every conclusion; separate diagnosis from AI phrasing; work without an AI API.
**Non-goals (MVP):** automatic remediation; real device integration; wireless, QoS and routing-protocol analysis; ML-based anomaly detection.

## 5. User stories
1. As **Priya**, when users complain about slowness, I want the probable cause and the top offending flow, so I can fix it without manual investigation.
2. As **Priya**, when a link fails but users are fine, I still want to be told, so I restore redundancy before a second failure causes an outage.
3. As **Priya**, when loss appears without congestion, I want to be told it is likely hardware, so I don't waste time rate-limiting traffic.
4. As **Dana**, when a device is repeatedly blocked by policy, I want to know if it is also harming other users, so I can decide to quarantine it.
5. As **Marcus**, I want each incident in plain language with who is affected, so I can communicate and prioritize.
6. As **Priya**, I want to see why the tool reached its conclusion, so I can trust it or overrule it.

## 6. Requirements
**Functional**
| # | Requirement | Priority | Status |
|---|---|---|---|
| F1 | Model topology, VLANs, addressing and segmentation policy | Must | Done |
| F2 | Derive utilization, latency and loss from traffic, not random data | Must | Done |
| F3 | Maintain a baseline of normal behavior per link | Must | Done |
| F4 | Detect threshold, baseline, loss-without-load and latency-without-load symptoms | Must | Done |
| F5 | Correlate symptoms into one finding with cause, evidence, impact, action, confidence | Must | Done |
| F6 | Include security events (blocked flows) in the diagnosis | Must | Done |
| F7 | Dashboard: topology status, root cause, health, security | Must | Done |
| F8 | Optional plain-language summary by an LLM, grounded in the finding | Should | Done |
| F9 | Trend-based capacity forecasting | Could | Roadmap |
| F10 | One-click remediation with approval | Won't (MVP) | Roadmap |

**Non-functional:** deterministic diagnosis (same input, same output); every claim traceable to evidence; works offline with no API key; LLM output never changes the diagnosis; automated tests for every rule.

## 7. Prioritization
Scored with RICE (reach × impact × confidence ÷ effort) using assumed values for a mid-size enterprise:

| Capability | Reach | Impact | Confidence | Effort | Score | Decision |
|---|---|---|---|---|---|---|
| Congestion root cause + top talker | High (3) | High (3) | 80% | 2 | 3.6 | MVP |
| Link-down with lost-redundancy warning | High (3) | Med (2) | 90% | 1 | 5.4 | MVP |
| Compromised-device correlation | Med (2) | High (3) | 70% | 2 | 2.1 | MVP |
| LLM plain-language summary | Med (2) | Med (2) | 60% | 1 | 2.4 | MVP (optional) |
| Capacity forecasting | Med (2) | Med (2) | 50% | 3 | 0.7 | Next |
| Automated remediation | High (3) | High (3) | 30% | 5 | 0.5 | Later |

## 8. Success metrics
| Metric | Definition | Current (lab) | Target (hypothesis) |
|---|---|---|---|
| **MTTI** (north star) | Detection → cause identified | Instant for modeled scenarios | 50% lower than manual triage |
| MTTD | Problem start → detection | Baseline flags anomalies before critical thresholds | Detect before first user ticket in most incidents |
| MTTR | Cause identified → resolved | Action provided with every finding | 30% lower |
| Diagnosis accuracy | Correct culprit vs ground truth | 8/8 scenarios | ≥ 90% on real incidents |
| False-positive rate | Findings on a healthy network | 0 on `normal` | < 5% of alerts |
| Admin trust | Findings acted on without re-investigation | not measurable in lab | > 70% |
| Availability impact | Minutes of user-impacting outage | n/a | trending down quarter over quarter |

## 9. Trade-offs
- **Rules vs ML:** rules are explainable and testable from day one but only catch known patterns. ML finds new patterns but is harder to trust. Choice: rules for diagnosis, ML later for anomaly detection.
- **LLM for diagnosis vs explanation:** using an LLM to diagnose risks invented causes. Choice: LLM only rephrases, with a numeric grounding check and template fallback.
- **One finding vs many:** showing only the top cause reduces noise but can hide a second problem. Mitigation: evidence list and all-links view remain available.
- **Simulation vs real devices:** a simulation is reproducible and safe but not proof of real-world accuracy. Next step is validating on real telemetry.

## 10. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Wrong diagnosis erodes trust | Show evidence and confidence; measure accuracy against labeled incidents |
| Alert fatigue from baselines on noisy links | Minimum spread and minimum utilization before alerting |
| LLM hallucination | Grounding check, template fallback, LLM never decides |
| Multiple simultaneous faults | Roadmap: rank several findings instead of one |
| Data privacy (flows reveal user activity) | Aggregate by group; role-based access to flow details |

## 11. Roadmap
| Now (MVP, built) | Next | Later |
|---|---|---|
| Model, telemetry, baseline, 7 scenarios, root-cause engine, dashboard, optional LLM summary | Time-series telemetry and capacity forecasts; multi-fault ranking; per-VLAN spanning tree | Real telemetry ingestion; identity/group-based policy; natural-language Q&A over incidents; approved closed-loop remediation |

## 12. Open questions
- Which incident types cost customers the most time today? (validate the rule priorities)
- How much evidence do admins want before acting: a summary, or the full path and flow list?
- Would customers accept automated quarantine of a device, or only a recommendation?