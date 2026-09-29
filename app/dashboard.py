"""Phase 8: the network operations dashboard.

Run from the project root:   streamlit run app/dashboard.py

The dashboard only DISPLAYS what the engine computes. Pick a scenario on the
left; every number, color and finding is recalculated from the model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # so "netops" imports work

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from netops.addressing import VLANS
from netops.inventory import build_inventory
from netops.policy import ACL, DEMO_FLOWS, evaluate
from netops.rca import EXPECTED, correlate, detect
from netops.scenarios import SCENARIOS, run
from netops.stp import compute_stp
from netops.topology import build_campus

st.set_page_config(page_title="Enterprise NetOps Lab", layout="wide")

POS = {  # fixed layered layout: internet at the top, users at the bottom
    "INTERNET": (0, 6), "EDGE": (0, 5), "CORE": (0, 4),
    "eng-srv": (2.6, 5.0), "fin-srv": (3.2, 4.4), "hr-srv": (3.6, 3.8),
    "DIST-1": (-2, 3), "DIST-2": (2, 3),
    "ACCESS-1": (-3, 2), "ACCESS-2": (3, 2),
    "hr-pc-1": (-4.5, 1), "fin-pc-1": (-3, 1), "ap-1": (-1.5, 1),
    "eng-pc-1": (1.5, 1), "iot-cam-1": (3, 1), "guest-1": (4.5, 1),
}
LABEL_SIDE = {"INTERNET": "middle right", "EDGE": "middle right", "CORE": "middle left",
              "DIST-1": "middle left", "DIST-2": "middle right", "ACCESS-1": "middle left",
              "ACCESS-2": "middle right", "eng-srv": "middle right", "fin-srv": "middle right",
              "hr-srv": "middle right"}
LINK_COLOR = {"OK": "#4c9a6a", "WARNING": "#d19a22", "CRITICAL": "#d64545", "DOWN": "#d64545"}
LAYER_COLOR = {"wan": "#8a8f98", "edge": "#5b6bbf", "core": "#3b4a9e", "distribution": "#2f7fb5",
               "access": "#2aa198", "endpoint": "#9aa5b1", "server": "#7a5ea8"}


@st.cache_data(show_spinner=False)
def load(name: str):
    result, normal = run(name), run("normal")
    finding = correlate(result, detect(result, normal))
    blocked = compute_stp(result["graph"])["blocked"]
    return result, finding, blocked


def topology_figure(result: dict, blocked: list[tuple[str, str]]) -> go.Figure:
    g_full = build_campus()
    inv = build_inventory(g_full)
    health = result["health"].set_index("link")
    fig = go.Figure()

    for a, b in g_full.edges:
        link = "<->".join(sorted((a, b)))
        row = health.loc[link] if link in health.index else None
        status = row["status"] if row is not None else "OK"
        is_blocked = tuple(sorted((a, b))) in blocked
        color = "#b8bec6" if is_blocked else LINK_COLOR[status]
        dash = "dot" if is_blocked else ("dash" if status == "DOWN" else "solid")
        width = 5 if status in ("CRITICAL", "DOWN") else 3
        (x0, y0), (x1, y1) = POS[a], POS[b]
        fig.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines", hoverinfo="skip",
                                 line=dict(color=color, width=width, dash=dash), showlegend=False))
        label = "STP BLOCKED (standby)" if is_blocked else status
        detail = "" if row is None or status == "DOWN" else (
            f"<br>{row['utilization_pct']}% util · {row['latency_ms']} ms · {row['loss_pct']}% loss")
        fig.add_trace(go.Scatter(x=[(x0 + x1) / 2], y=[(y0 + y1) / 2], mode="markers",
                                 marker=dict(size=10, color=color, opacity=0.01), showlegend=False,
                                 hovertemplate=f"<b>{link}</b><br>{label}{detail}<extra></extra>"))

    for node, (x, y) in POS.items():
        layer = g_full.nodes[node]["layer"]
        extra = ""
        if node in inv:
            d = inv[node]
            extra = f"<br>VLAN {d.vlan} {VLANS[d.vlan].name}<br>{d.ip}<br>{d.mac}"
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", text=[node], textposition=LABEL_SIDE.get(node, "bottom center"),
            marker=dict(size=26 if layer in ("core", "distribution", "access", "edge") else 18,
                        color=LAYER_COLOR[layer], line=dict(color="white", width=1.5)),
            hovertemplate=f"<b>{node}</b><br>{layer}{extra}<extra></extra>", showlegend=False))

    fig.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False, range=[-5.3, 5.3]), yaxis=dict(visible=False, range=[0.5, 6.4]))
    return fig


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Scenario")
names = list(SCENARIOS)
choice = st.sidebar.radio("Trigger an event", names, format_func=lambda n: n.replace("_", " "),
                          key="scenario")
st.sidebar.caption(SCENARIOS[choice].description)
st.sidebar.button("Reset to normal", width="stretch",
                  on_click=lambda: st.session_state.update(scenario="normal"))
st.sidebar.divider()
st.sidebar.caption("Vendor-neutral simulation. The inputs are simulated; the reasoning is real.")

result, finding, blocked = load(choice)
health = result["health"]

# ---------------------------------------------------------------- header + KPIs
st.title("Enterprise NetOps Lab")
st.caption("Campus digital twin: topology → traffic → telemetry → detection → root cause → action")

critical = int((health["status"].isin(["CRITICAL", "DOWN"])).sum())
warning = int((health["status"] == "WARNING").sum())
affected = sum(1 for u in result["user_experience"].values() if u["loss_pct"] >= 1)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Critical / down links", critical)
k2.metric("Warning links", warning)
k3.metric("Users with packet loss", affected)
k4.metric("Blocked flows (ACL)", len(result["security_events"]))

tab_topo, tab_rca, tab_health, tab_sec = st.tabs(["Topology", "Root cause", "Network health", "Security"])

# ---------------------------------------------------------------- topology
with tab_topo:
    st.plotly_chart(topology_figure(result, blocked), width="stretch")
    st.caption("Green = OK · amber = warning · red = critical · red dashed = down · "
               "grey dotted = blocked by spanning tree (standby). Hover links and devices for details.")

# ---------------------------------------------------------------- root cause
with tab_rca:
    if finding is None:
        st.success("No problems detected. All links are within their normal range.")
    else:
        box = st.error if finding.confidence == "High" and finding.category != "link_down" else st.warning
        box(f"**PROBLEM:** {finding.problem}")
        st.markdown(f"**LIKELY CAUSE:** {finding.likely_cause}")
        st.markdown("**EVIDENCE:**\n" + "\n".join(f"- {e}" for e in finding.evidence))
        st.markdown(f"**BUSINESS IMPACT:** {finding.impact}")
        st.markdown(f"**RECOMMENDED ACTION:** {finding.action}")
        st.markdown(f"**CONFIDENCE:** {finding.confidence}")
        expected = EXPECTED.get(choice)
        if expected:
            ok = (finding.category, finding.culprit) == expected
            st.caption(("✅ Matches" if ok else "❌ Does not match") +
                       f" the scenario's known cause: {expected[0]} at {expected[1]}")
    st.caption("Deterministic rule-based engine (netops/rca.py). No AI is used to reach this diagnosis.")

# ---------------------------------------------------------------- health
with tab_health:
    core_links = health[health["kind"].isin(["uplink", "backbone", "wan"])]
    fig = go.Figure(go.Bar(
        x=core_links["utilization_pct"], y=core_links["link"], orientation="h",
        marker_color=[LINK_COLOR.get(s, "#4c9a6a") for s in core_links["status"]],
        hovertemplate="%{y}: %{x}%<extra></extra>"))
    fig.add_vline(x=90, line_dash="dash", line_color="#d64545", annotation_text="critical 90%")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="utilization %",
                      yaxis=dict(autorange="reversed"))
    st.subheader("Inter-switch and internet links")
    st.plotly_chart(fig, width="stretch")

    st.subheader("What users feel (end to end)")
    ux = pd.DataFrame([{"user": u, "latency_ms": v["latency_ms"], "loss_pct": v["loss_pct"]}
                       for u, v in result["user_experience"].items()])
    st.dataframe(ux, hide_index=True, width="stretch")

    st.subheader("All links")
    st.dataframe(health[["link", "kind", "utilization_pct", "latency_ms", "loss_pct", "status"]],
                 hide_index=True, width="stretch")

# ---------------------------------------------------------------- security
with tab_sec:
    st.subheader("Blocked flows in this scenario")
    if result["security_events"]:
        st.dataframe(pd.DataFrame(result["security_events"]), hide_index=True, width="stretch")
    else:
        st.info("No blocked flows.")

    st.subheader("Segmentation policy check")
    rows = []
    for src, dst, port, label in DEMO_FLOWS:
        v = evaluate(src, dst, port)
        rows.append({"flow": label, "result": v.action, "matched rule": v.rule, "enforced at": v.enforced_at})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.subheader("ACL (first match wins, implicit deny at the end)")
    st.dataframe(pd.DataFrame([{"#": i + 1, "rule": r.name, "action": r.action, "from": ", ".join(r.src),
                                "to": r.dst, "port": str(r.port) if r.port else "any"} for i, r in enumerate(ACL)]),
                 hide_index=True, width="stretch")