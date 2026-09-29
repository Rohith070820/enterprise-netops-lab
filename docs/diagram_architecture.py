"""Draws docs/architecture.png. Run from the project root: python docs/diagram_architecture.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

INK, MUTED, BG = "#1d2430", "#4b5563", "#ffffff"
fig, ax = plt.subplots(figsize=(16, 11), dpi=160)
fig.patch.set_facecolor(BG)
ax.set_xlim(0, 160); ax.set_ylim(-2, 110); ax.axis("off")


def panel(x, y, w, h, color, tint, num, title):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1", fc=tint, ec=color, lw=1.6))
    ax.add_patch(Circle((x + 3.2, y + h - 3.2), 2.1, fc=color, ec="none", zorder=3))
    ax.text(x + 3.2, y + h - 3.25, str(num), ha="center", va="center", color="white", fontsize=13, weight="bold",
            zorder=4)
    ax.text(x + 6.6, y + h - 3.2, title, va="center", fontsize=13.5, weight="bold", color=INK, family="serif")


def box(x, y, w, h, ec="#cfd6df", dashed=False, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8", fc=fc, ec=ec, lw=1,
                                ls=(0, (3, 2)) if dashed else "-"))


def bullets(x, y, lines, size=9, step=2.3, color=MUTED):
    for i, line in enumerate(lines):
        ax.text(x, y - i * step, f"•  {line}", fontsize=size, color=color, va="center")


def arrow(p, q, label=None, lpos=None, dashed=False, ha="center"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=15, lw=1.5, color=INK,
                                 ls=(0, (4, 3)) if dashed else "-"))
    if label:
        ax.text(*(lpos or ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)), label, fontsize=9.5, color=INK, ha=ha,
                va="center", family="serif")


# ------------------------------------------------------------------ small icons
def i_link(x, y, c):
    for dx in (-1.1, 1.1):
        ax.add_patch(FancyBboxPatch((x + dx - 1.2, y - 0.6), 2.4, 1.2, boxstyle="round,pad=0,rounding_size=0.6",
                                    fc="none", ec=c, lw=2, transform=ax.transData,
                                    mutation_aspect=1))
    ax.plot([x - 0.3, x + 0.3], [y + 1.3, y - 1.3], c="#d64545", lw=2)


def i_bars(x, y, c):
    for k, hgt in enumerate([1.2, 2.2, 3.2]):
        ax.add_patch(Rectangle((x - 1.8 + k * 1.3, y - 1.6), 0.9, hgt, fc=c))


def i_people(x, y, c):
    for dx in (-0.9, 0.9):
        ax.add_patch(Circle((x + dx, y + 0.8), 0.6, fc=c))
        ax.add_patch(FancyBboxPatch((x + dx - 0.8, y - 1.5), 1.6, 1.4, boxstyle="round,pad=0,rounding_size=0.5",
                                    fc=c, ec="none"))


def i_lock(x, y, c):
    ax.add_patch(Arc((x, y + 0.6), 2, 2.4, theta1=0, theta2=180, ec=c, lw=2))
    ax.add_patch(Rectangle((x - 1.3, y - 1.4), 2.6, 2, fc=c))


def i_wifi(x, y, c):
    for r in (1, 2, 3):
        ax.add_patch(Arc((x, y - 1.2), r * 1.1, r * 1.1, theta1=45, theta2=135, ec=c, lw=2))
    ax.add_patch(Circle((x, y - 1.2), 0.35, fc=c))


def i_bolt(x, y, c):
    ax.add_patch(Polygon([(x + 0.4, y + 1.9), (x - 0.9, y - 0.1), (x + 0.1, y - 0.1), (x - 0.4, y - 1.9),
                          (x + 0.9, y + 0.3), (x - 0.1, y + 0.3)], fc="#e5484d"))


def i_globe(x, y, c):
    ax.add_patch(Circle((x, y), 1.7, fc="none", ec=c, lw=1.8))
    ax.add_patch(Arc((x, y), 1.5, 3.4, ec=c, lw=1.4))
    ax.plot([x - 1.7, x + 1.7], [y, y], c=c, lw=1.4)


def i_switch(x, y, c="#1f5fa8"):
    ax.add_patch(FancyBboxPatch((x - 1.9, y - 1.1), 3.8, 2.2, boxstyle="round,pad=0,rounding_size=0.9",
                                fc=c, ec="white", lw=1, zorder=4))
    ax.text(x, y, "⇄", ha="center", va="center", color="white", fontsize=9, zorder=5)


def i_db(x, y, c="#6b7280"):
    for k in range(3):
        ax.add_patch(FancyBboxPatch((x - 2.2, y - 2.6 + k * 1.8), 4.4, 1.5,
                                    boxstyle="round,pad=0,rounding_size=0.7", fc=c, ec="white", lw=1))


def i_nodes(x, y, c):
    for px, py in [(0, 1.3), (-1.2, -1), (1.2, -1)]:
        ax.plot([x, x + px], [y, y + py], c=c, lw=1.5)
        ax.add_patch(Circle((x + px, y + py), 0.55, fc="white", ec=c, lw=1.5))


def i_shield(x, y, c):
    ax.add_patch(Polygon([(x - 1.3, y + 1.2), (x, y + 1.8), (x + 1.3, y + 1.2), (x + 1.1, y - 0.7), (x, y - 1.8),
                          (x - 1.1, y - 0.7)], fc="none", ec=c, lw=1.8))
    ax.plot([x - 0.6, x - 0.1, x + 0.7], [y, y - 0.6, y + 0.6], c=c, lw=1.8)


def i_arrows(x, y, c):
    for dx, dy in [(1.6, 0), (-1.6, 0), (0, 1.6), (0, -1.6)]:
        ax.add_patch(FancyArrowPatch((x, y), (x + dx, y + dy), arrowstyle="-|>", mutation_scale=7, lw=1.4, color=c))


def i_search(x, y, c):
    ax.add_patch(Circle((x - 0.5, y + 0.5), 1.6, fc="none", ec=c, lw=2.2))
    ax.plot([x + 0.7, x + 2], [y - 0.7, y - 2], c=c, lw=3, solid_capstyle="round")


def i_doc(x, y, c):
    ax.add_patch(FancyBboxPatch((x - 1.8, y - 2.4), 3.6, 4.8, boxstyle="round,pad=0,rounding_size=0.4",
                                fc=c, ec="none"))
    for k in range(4):
        ax.plot([x - 1, x + 1], [y + 1.4 - k * 1.0] * 2, c="white", lw=1.2)


def i_brain(x, y, c):
    ax.add_patch(Circle((x - 0.8, y + 0.4), 1.3, fc=c))
    ax.add_patch(Circle((x + 0.8, y + 0.4), 1.3, fc=c))
    ax.add_patch(Circle((x, y - 0.8), 1.3, fc=c))
    ax.plot([x, x], [y - 1.8, y + 1.6], c="white", lw=1)


# ------------------------------------------------------------------ 1  scenario injector
panel(2, 94, 156, 14, "#1f5fa8", "#eef4fc", 1, "Scenario Injector  (7 failure and anomaly scenarios)")
ITEMS = [(i_link, "Link cut", "uplink goes down"), (i_bars, "Congestion", "450 Mbps transfer"),
         (i_people, "Noisy neighbor", "guest bulk download"), (i_lock, "Unauthorized", "guest probes finance"),
         (i_wifi, "Rogue IoT", "compromised camera"), (i_bolt, "Bad optic", "8% loss, low load"),
         (i_globe, "Slow ISP", "+150 ms latency")]
for k, (icon, name, sub) in enumerate(ITEMS):
    x = 6 + k * 21.9
    icon(x + 2, 98.6, "#1f4e89")
    ax.text(x + 5.2, 99.7, name, fontsize=9.6, weight="bold", color=INK, va="center", family="serif")
    ax.text(x + 5.2, 97.4, sub, fontsize=8, color=MUTED, va="center")
    if k:
        ax.plot([x - 1.4, x - 1.4], [96.2, 101], c="#c8d3e3", lw=1)
arrow((40, 93.8), (40, 88.4), "Inject faults into the model", lpos=(42, 91.2), ha="left")

# ------------------------------------------------------------------ 2  network model
panel(2, 67, 74, 21, "#d9822b", "#fdf3e7", 2, "Network Model  (NetworkX)")
NODES = {"C": (18, 80.5), "D1": (10, 76), "D2": (26, 76), "A1": (8, 70.6), "A2": (28, 70.6)}
for a, b, blocked in [("C", "D1", 0), ("C", "D2", 0), ("D1", "D2", 1), ("D1", "A1", 0), ("D2", "A1", 1),
                      ("D1", "A2", 0), ("D2", "A2", 1)]:
    (x0, y0), (x1, y1) = NODES[a], NODES[b]
    ax.plot([x0, x1], [y0, y1], c="#9aa3ae" if blocked else INK, lw=1.3, ls=(0, (2, 2)) if blocked else "-", zorder=2)
for n, (x, y) in NODES.items():
    i_switch(x, y)
ax.text(18, 68.3, "dashed = blocked by spanning tree", fontsize=7.6, color=MUTED, ha="center")
box(36, 68.8, 38, 13.4, dashed=True)
bullets(38, 80.4, ["7 VLANs · 10.10.N.0/24 subnets", "MAC / IP / gateway per device", "access vs trunk ports (802.1Q)",
                 "spanning tree (root = CORE)", "failover paths · single points of failure"], size=8.6, step=2.5)
arrow((76.3, 77.5), (87.7, 77.5), "topology\n+ policy", lpos=(82, 81.3))

# ------------------------------------------------------------------ 3  traffic and policy
panel(88, 67, 70, 21, "#2e8b57", "#eef8f1", 3, "Traffic & Policy Processing")
ROWS3 = [(i_arrows, "Traffic flows", "seeded demand, routed on the real (STP) paths"),
         (i_shield, "Policy enforcement", "first-match ACL · implicit deny at the end"),
         (i_nodes, "Denied traffic", "travels up to the gateway, then is dropped")]
for k, (icon, name, sub) in enumerate(ROWS3):
    y = 80 - k * 4.6
    box(91, y - 2.0, 64, 4.0)
    icon(94.5, y + 0.1, INK)
    ax.text(99, y + 0.9, name, fontsize=9.6, weight="bold", color=INK, va="center", family="serif")
    ax.text(99, y - 1.0, sub, fontsize=8.2, color=MUTED, va="center")
arrow((123, 66.8), (123, 62.4), "Push flows through every link", lpos=(125, 64.6), ha="left")

# ------------------------------------------------------------------ 4  telemetry
panel(90, 36, 68, 26, "#2f6fd1", "#edf3fd", 4, "Telemetry & Baseline")
box(92, 38, 64, 18.5)
i_db(97, 48.5)
ax.text(101.5, 53.6, "Network telemetry", fontsize=10, weight="bold", color=INK, va="center", family="serif")
bullets(101.5, 51, ["utilization = Σ flows ÷ capacity", "latency (queueing model)", "packet loss",
                    "20-sample normal baseline"], size=8.2, step=2.3)
cx0, cy0 = 132, 41
LINKS = [("ACC-2↑", 51, 95.8), ("ACC-1↑", 18, 17.5), ("WAN", 28, 26.4), ("CORE", 7, 11.3)]
for k, (lab, base, now) in enumerate(LINKS):
    x = cx0 + k * 5.6
    ax.add_patch(Rectangle((x, cy0), 2, base * 0.11, fc="#aab4c3"))
    ax.add_patch(Rectangle((x + 2.1, cy0), 2, now * 0.11, fc="#e5484d" if now >= 90 else "#2f6fd1"))
    ax.text(x + 2, cy0 - 1.2, lab, fontsize=6.6, color=MUTED, ha="center")
ax.plot([cx0 - 0.5, cx0 + 22.5], [cy0 + 9.9] * 2, c="#e5484d", lw=0.9, ls=(0, (3, 2)))
ax.text(cx0 + 22.6, cy0 + 9.9, "90%", fontsize=6.6, color="#e5484d", va="center")
ax.add_patch(Rectangle((cx0, 53.2), 1.4, 1, fc="#aab4c3"))
ax.text(cx0 + 1.9, 53.7, "baseline", fontsize=7, color=MUTED, va="center")
ax.add_patch(Rectangle((cx0 + 10, 53.2), 1.4, 1, fc="#2f6fd1"))
ax.text(cx0 + 11.9, 53.7, "now", fontsize=7, color=MUTED, va="center")
arrow((89.8, 49), (82.2, 49), "link\nhealth", lpos=(86, 45.4))

# ------------------------------------------------------------------ 5  detection
panel(49, 36, 33, 26, "#6f42c1", "#f4effb", 5, "Anomaly Detection")
box(51, 46.5, 29, 9.6)
bx, by = 53.5, 47.8
ax.add_patch(Rectangle((bx, by + 51 * 0.075 - 0.25), 24, 0.5 + 2.9 * 0.15, fc="#c9b8ef", alpha=0.7))
ax.plot([bx, bx + 24], [by + 90 * 0.075] * 2, c=INK, lw=1, ls=(0, (3, 2)))
t = np.linspace(0, 24, 90)
series = 51 + 2.5 * np.sin(t * 1.3) + np.where(t > 16, 44 * np.exp(-((t - 19) ** 2) / 2.5), 0)
ax.plot(bx + t, by + series * 0.075, c="#2f6fd1", lw=1.3)
ax.add_patch(Rectangle((bx + 15.5, by - 0.4), 7, 7.9, fc="#f8c9cb", alpha=0.7, zorder=1.5))
ax.text(bx + 24.3, by + 90 * 0.075, "90%", fontsize=6.5, color=INK, va="center")
bullets(51.5, 44, ["threshold breach (≥ 90%, loss)", "≥ 3σ above the baseline", "loss / latency without load",
                   "blocked flows · user impact"], size=8.1, step=2.1)
arrow((48.8, 49), (42.2, 49), "symptoms", lpos=(45.5, 51.3))

# ------------------------------------------------------------------ 6  root cause
panel(2, 30, 40, 32, "#d64545", "#fdeeee", 6, "Root-Cause Engine")
box(4, 41.5, 36, 15)
i_nodes(8, 49.5, "#1d2430")
ax.text(12, 54.6, "Ordered correlation rules", fontsize=9.6, weight="bold", color=INK, va="center", family="serif")
for k, rule in enumerate(["link down", "compromised device", "unauthorized access", "physical fault",
                          "provider issue", "congestion + top talker"]):
    ax.text(12.5, 52.4 - k * 1.75, f"{k + 1}. {rule}", fontsize=7.9, color=MUTED, va="center")
box(4, 31.8, 36, 8.6)
i_search(8, 36, "#1d2430")
ax.text(12, 38.4, "Structured finding", fontsize=9.6, weight="bold", color=INK, va="center", family="serif")
ax.text(12, 36.1, "problem · cause · evidence", fontsize=7.9, color=MUTED, va="center")
ax.text(12, 34.1, "impact · action · confidence", fontsize=7.9, color=MUTED, va="center")
arrow((20, 29.8), (20, 24.4), "finding  ·  8/8 scenarios diagnosed correctly", lpos=(22, 27.1), ha="left")

# ------------------------------------------------------------------ 7  explanation
panel(2, 2, 80, 22, "#1b7ea8", "#ecf6fb", 7, "Explanation Layer")
i_doc(7, 11.5, "#6b7280")
ax.text(11, 17, "Template summary (default)", fontsize=9.6, weight="bold", color=INK, va="center", family="serif")
bullets(11, 14.4, ["plain English, no API key", "problem → cause → action", "always available"], size=8.1, step=2.2)
box(41, 4, 39, 15.6, ec="#1b7ea8", dashed=True, fc="#f7fbfd")
i_brain(45, 13, "#1b4f72")
ax.text(48.5, 17.3, "Optional LLM + grounding check", fontsize=8.8, weight="bold", color=INK, va="center",
        family="serif")
bullets(48.5, 14.7, ["finding JSON is its only context", "every number checked vs evidence",
                     "rejected → template fallback", "never changes the diagnosis"], size=7.9, step=2.2)
arrow((82.3, 13), (89.7, 13), "summary", lpos=(86, 15.4))

# ------------------------------------------------------------------ 8  dashboard
panel(90, 2, 68, 30, "#2e8b57", "#eef8f1", 8, "Streamlit Dashboard")
box(92, 4, 26, 21.5)
for k, feat in enumerate(["Live topology & link status", "KPIs: critical / warning", "Root-cause finding",
                          "Health charts & user impact", "Security: blocked flows, ACL", "Scenario controls"]):
    y = 23 - k * 3.4
    ax.add_patch(Circle((94.5, y), 0.55, fc="#2e8b57"))
    ax.text(96, y, feat, fontsize=7.9, color=INK, va="center")
box(120, 14.8, 17, 10.7)
pts = [(124, 22), (128.5, 23.4), (133, 21.5), (126, 17.5), (131, 17)]
for a, b in [(0, 1), (1, 2), (0, 3), (1, 3), (1, 4), (2, 4)]:
    ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]], c="#e5484d" if (a, b) == (1, 4) else "#2f6fd1", lw=1.3)
for px, py in pts:
    ax.add_patch(Circle((px, py), 0.8, fc="white", ec="#2f6fd1", lw=1.3))
box(139, 14.8, 17, 10.7)
for k, (v, col) in enumerate([(3, "#2e8b57"), (5, "#2e8b57"), (8.5, "#e5484d"), (2.5, "#2e8b57")]):
    ax.add_patch(Rectangle((141, 23.5 - k * 2.2), v * 1.5, 1.4, fc=col))
box(120, 4, 36, 9.5)
ax.text(122, 11.2, "PROBLEM  Engineering users degraded", fontsize=7.4, color="#b42318", weight="bold", va="center")
ax.text(122, 8.8, "CAUSE  ACCESS-2 uplink saturated (top flow 47%)", fontsize=7.2, color=INK, va="center")
ax.text(122, 6.4, "ACTION  rate-limit the transfer · confidence High", fontsize=7.2, color=INK, va="center")

# feedback loop: dashboard sidebar re-runs any scenario
ax.plot([158.3, 159.4, 159.4, 158.6], [17, 17, 101, 101], c=INK, lw=1.3, ls=(0, (4, 3)))
ax.add_patch(FancyArrowPatch((159.4, 101), (158.4, 101), arrowstyle="-|>", mutation_scale=12, color=INK))
ax.text(159.8, 60, "pick a scenario in the dashboard", fontsize=8.5, color=INK, rotation=90, ha="left",
        va="center", family="serif")

# legend
ax.add_patch(FancyArrowPatch((92, -0.8), (97, -0.8), arrowstyle="-|>", mutation_scale=11, color=INK, lw=1.3))
ax.text(98, -0.8, "data flow", fontsize=8.2, color=INK, va="center")
ax.add_patch(FancyArrowPatch((108, -0.8), (113, -0.8), arrowstyle="-|>", mutation_scale=11, color=INK, lw=1.3,
                             ls=(0, (4, 3))))
ax.text(114, -0.8, "user-triggered loop", fontsize=8.2, color=INK, va="center")
ax.add_patch(Rectangle((131, -1.5), 3.4, 1.4, fc="#f8c9cb"))
ax.text(135.2, -0.8, "anomaly", fontsize=8.2, color=INK, va="center")
ax.add_patch(FancyBboxPatch((144, -1.5), 3.4, 1.4, boxstyle="round,pad=0,rounding_size=0.3", fc="white",
                            ec=INK, lw=0.9, ls=(0, (2, 1.5))))
ax.text(148.2, -0.8, "optional component", fontsize=8.2, color=INK, va="center")

fig.savefig("docs/architecture.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
print("Saved docs/architecture.png")
