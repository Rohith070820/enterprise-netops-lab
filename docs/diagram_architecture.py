"""Draws docs/architecture.png. Run from the project root: python docs/diagram_architecture.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BG, INK, MUTED = "#f7f8fa", "#1f2933", "#5f6b7a"
COLUMNS = [  # title, subtitle, tint, border, boxes (title, detail)
    ("1  SIMULATE", "what happens on the network", "#eaf1fb", "#3d7dd8", [
        ("Scenario injector", "link cut · congestion · rogue IoT\nbad optic · slow ISP"),
        ("Network model", "NetworkX graph · 7 VLANs\nMAC/IP · spanning tree"),
        ("Traffic + policy", "flows follow real paths\nfirst-match ACL"),
    ]),
    ("2  ANALYZE", "deterministic and tested", "#e8f5ef", "#2a9d5c", [
        ("Telemetry", "utilization · latency · loss\n20-sample baseline"),
        ("Detection", "thresholds + deviation\nfrom baseline"),
        ("Root-cause engine", "ordered correlation rules\ntop talker · noisy neighbor"),
        ("Structured finding", "problem · cause · evidence\nimpact · action · confidence"),
    ]),
    ("3  PRESENT", "explains, never decides", "#f3eefb", "#7a5ea8", [
        ("Explanation layer", "template by default\noptional LLM + grounding check"),
        ("Streamlit dashboard", "topology · root cause\nhealth · security"),
    ]),
]

fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
fig.patch.set_facecolor(BG)
ax.set_xlim(0, 160); ax.set_ylim(0, 90); ax.axis("off")
ax.text(4, 85, "Enterprise NetOps Lab · architecture", fontsize=20, weight="bold", color=INK, va="center")
ax.text(4, 80.5, "The analytics decide. The explanation layer and dashboard only present the finding.",
        fontsize=12, color=MUTED, va="center")

col_x, col_w, box_w, box_h = [4, 56, 108], 48, 40, 11
centers = {}
for (title, sub, tint, border, boxes), x in zip(COLUMNS, col_x):
    ax.add_patch(FancyBboxPatch((x, 5), col_w, 69, boxstyle="round,pad=0,rounding_size=2.5",
                                fc=tint, ec="none"))
    ax.text(x + 3, 70, title, fontsize=13, weight="bold", color=border, va="center")
    ax.text(x + 3, 66.3, sub, fontsize=10.5, color=MUTED, va="center", style="italic")
    top, gap = 62, 3.8
    for i, (name, detail) in enumerate(boxes):
        y = top - i * (box_h + gap) - box_h
        bx = x + (col_w - box_w) / 2
        ax.add_patch(FancyBboxPatch((bx, y), box_w, box_h, boxstyle="round,pad=0,rounding_size=1.5",
                                    fc="white", ec=border, lw=1.6))
        ax.text(bx + box_w / 2, y + box_h - 3.1, name, ha="center", va="center", fontsize=12.5,
                weight="bold", color=INK)
        ax.text(bx + box_w / 2, y + 3.8, detail, ha="center", va="center", fontsize=9.6, color=MUTED,
                linespacing=1.35)
        centers[name] = (bx, y, box_w, box_h)


def arrow(a, b, rad=0.0, side=("bottom", "top")):
    ax_, ay, aw, ah = centers[a]
    bx_, by, bw, bh = centers[b]
    start = {"bottom": (ax_ + aw / 2, ay), "right": (ax_ + aw, ay + ah / 2)}[side[0]]
    end = {"top": (bx_ + bw / 2, by + bh), "left": (bx_, by + bh / 2)}[side[1]]
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, lw=1.6,
                                 color="#44505e", connectionstyle=f"arc3,rad={rad}",
                                 shrinkA=2, shrinkB=2))


for a, b in [("Scenario injector", "Network model"), ("Network model", "Traffic + policy"),
             ("Telemetry", "Detection"), ("Detection", "Root-cause engine"),
             ("Root-cause engine", "Structured finding"), ("Explanation layer", "Streamlit dashboard")]:
    arrow(a, b)
arrow("Traffic + policy", "Telemetry", side=("right", "left"))
arrow("Structured finding", "Explanation layer", side=("right", "left"))

ax.text(80, 1.5, "Remove the LLM and the diagnosis is identical.", ha="center", fontsize=10.5,
        color=MUTED, style="italic")
fig.savefig("docs/architecture.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
print("Saved docs/architecture.png")
