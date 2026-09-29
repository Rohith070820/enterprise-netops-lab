"""Draws docs/topology.png. Run from the project root: python docs/diagram_topology.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

BG, INK, MUTED, LINK = "#f7f8fa", "#1f2933", "#5f6b7a", "#44505e"
LAYER = {"wan": "#8a94a6", "edge": "#5b6bbf", "core": "#34409a", "dist": "#2f7fb5", "access": "#2a9d8f"}
VLAN = {10: ("Engineering", "#3d7dd8"), 20: ("Finance", "#2a9d5c"), 30: ("HR", "#c77d2a"),
        40: ("Guest", "#8a63d2"), 50: ("IoT", "#d64550"), 60: ("Servers", "#7a5ea8"), 99: ("Mgmt", "#6b7280")}

# name: (x, y, layer, label under name)
INFRA = {
    "INTERNET": (70, 92, "wan", ""), "EDGE": (70, 79, "edge", "router · NAT"),
    "CORE": (70, 64, "core", "root bridge"), "DIST-1": (45, 47, "dist", "L3 gateway · ACL"),
    "DIST-2": (95, 47, "dist", "L3 gateway · ACL"), "ACCESS-1": (32, 29, "access", ""),
    "ACCESS-2": (108, 29, "access", ""),
}
HOSTS = {  # name: (x, y, vlan, ip, switch)
    "hr-pc-1": (14, 10, 30, "10.10.30.21", "ACCESS-1"), "fin-pc-1": (32, 10, 20, "10.10.20.21", "ACCESS-1"),
    "ap-1": (50, 10, 99, "10.10.99.11", "ACCESS-1"), "eng-pc-1": (90, 10, 10, "10.10.10.21", "ACCESS-2"),
    "iot-cam-1": (108, 10, 50, "10.10.50.33", "ACCESS-2"), "guest-1": (126, 10, 40, "10.10.40.21", "ACCESS-2"),
    "eng-srv": (116, 71, 60, "10.10.60.10", "CORE"), "fin-srv": (123, 64, 60, "10.10.60.20", "CORE"),
    "hr-srv": (116, 57, 60, "10.10.60.30", "CORE"),
}
LINKS = [  # a, b, style: wan | backbone | uplink | blocked
    ("INTERNET", "EDGE", "wan"), ("EDGE", "CORE", "backbone"), ("CORE", "DIST-1", "backbone"),
    ("CORE", "DIST-2", "backbone"), ("DIST-1", "DIST-2", "blocked"), ("ACCESS-1", "DIST-1", "uplink"),
    ("ACCESS-1", "DIST-2", "blocked"), ("ACCESS-2", "DIST-1", "uplink"), ("ACCESS-2", "DIST-2", "blocked"),
]
STYLE = {"wan": dict(lw=2.2, ls="-", c=LINK), "backbone": dict(lw=4.2, ls="-", c=LINK),
         "uplink": dict(lw=2.2, ls="-", c=LINK), "blocked": dict(lw=2.0, ls=(0, (2, 2.2)), c="#a6aeb9"),
         "port": dict(lw=1.3, ls="-", c="#9aa3ae")}

fig, ax = plt.subplots(figsize=(16, 11), dpi=150)
fig.patch.set_facecolor(BG)
ax.set_xlim(0, 160); ax.set_ylim(-6, 104); ax.axis("off")
ax.text(4, 101, "Campus topology", fontsize=20, weight="bold", color=INK, va="center")
ax.text(4, 97, "Access / distribution / core with dual-homed access switches. Spanning tree blocks the dashed links.",
        fontsize=11.5, color=MUTED, va="center")

pos = {n: (x, y) for n, (x, y, *_) in INFRA.items()} | {n: (x, y) for n, (x, y, *_) in HOSTS.items()}
for a, b, style in LINKS:
    (x0, y0), (x1, y1) = pos[a], pos[b]
    ax.plot([x0, x1], [y0, y1], zorder=1, solid_capstyle="round", **STYLE[style])
for h, (x, y, vlan, ip, sw) in HOSTS.items():
    (x0, y0) = pos[sw]
    ax.plot([x0, x], [y0, y], zorder=1, **STYLE["port"])

for name, (x, y, layer, sub) in INFRA.items():
    w, h = (16, 6.4) if name != "INTERNET" else (15, 5.6)
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=1.6",
                                fc=LAYER[layer], ec="white", lw=2, zorder=3))
    ax.text(x, y, name, ha="center", va="center", color="white", fontsize=12, weight="bold", zorder=4)
    if sub:
        side = -1 if x <= 70 else 1
        ax.text(x + side * 9.2, y, sub, ha="right" if side < 0 else "left", va="center",
                fontsize=9.5, color=MUTED, zorder=4)

for name, (x, y, vlan, ip, sw) in HOSTS.items():
    vname, color = VLAN[vlan]
    w, h = 12.5, 5.4
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                fc="white", ec=color, lw=2, zorder=3))
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), 1.6, h, boxstyle="round,pad=0,rounding_size=0.6",
                                fc=color, ec="none", zorder=4))
    ax.text(x + 0.6, y + 0.9, name, ha="center", va="center", fontsize=10, weight="bold", color=INK, zorder=5)
    ax.text(x + 0.6, y - 1.3, ip, ha="center", va="center", fontsize=8.3, color=MUTED, zorder=5)
    if vlan != 60:
        ax.text(x + 0.6, y - 5.4, f"VLAN {vlan}\n{vname}", ha="center", va="center", fontsize=8.8,
                color=color, weight="bold", linespacing=1.2)
ax.text(131, 64, "VLAN 60\nServers", ha="left", va="center", fontsize=9.5, color=VLAN[60][1], weight="bold")

for y, label in [(92, "WAN"), (79, "EDGE"), (64, "CORE"), (47, "DISTRIBUTION"), (29, "ACCESS"), (10, "ENDPOINTS")]:
    ax.text(156, y, label, ha="right", va="center", fontsize=9.5, color="#a0a8b3", weight="bold")

legend = [Line2D([0], [0], color=LINK, lw=4.2, label="10 Gbps backbone"),
          Line2D([0], [0], color=LINK, lw=2.2, label="1 Gbps uplink / WAN"),
          Line2D([0], [0], color="#a6aeb9", lw=2, ls=(0, (2, 2.2)), label="blocked by spanning tree (standby)"),
          Line2D([0], [0], color="#9aa3ae", lw=1.3, label="access port (one VLAN)")]
ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=4, frameon=False,
          fontsize=10, labelcolor=MUTED)
fig.savefig("docs/topology.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
print("Saved docs/topology.png")
