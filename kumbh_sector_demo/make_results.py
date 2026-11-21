#!/usr/bin/env python3
"""Graphs (PNG), MP4 and GIF for out_kumbh_<N>. Writes into results/.
Layout is schematic; see INPUTS_AND_SOURCES.md for which inputs are sourced."""
import json
import pathlib
import shutil
import sys

import imageio_ffmpeg
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import animation
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as MplPolygon

matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
root = pathlib.Path(__file__).parent
N = sys.argv[1] if len(sys.argv) > 1 else "5000"
src = root / f"out_kumbh_{N}"
res = root / "results"
if res.exists():  # keep the earlier assumption-only run
    old = root / "results_v1_assumed_inputs"
    if not old.exists():
        shutil.move(str(res), str(old))
res.mkdir(exist_ok=True)

M = json.loads((src / "metrics.json").read_text())
ts = np.genfromtxt(src / "timeseries.csv", delimiter=",", names=True)
pk = np.load(src / "peakmaps.npz")
fr = np.load(src / "frames.npz")
snap = np.load(src / "snapshot.npz") if (src / "snapshot.npz").exists() else None
bnd = pk["boundary"]
GG = M["bottleneck"]["green_guide_flow_p_m_s"]
COL = {0: "#2a9d8f", 1: "#e63946", 2: "#1d4ed8", 3: "#8d99ae"}
LAB = {0: "walking to ghat", 1: "waiting in holding queue", 2: "bathing (5 min dip)", 3: "leaving"}
NOTE = "Schematic layout; widths, dwell, speed & limits from papers, rest assumed (see INPUTS_AND_SOURCES.md)"


def draw_geom(ax, lw=0.8):
    ax.add_patch(MplPolygon(bnd, closed=True, fc="#f4f4f4", ec="k", lw=lw))
    ax.set_aspect("equal")


# ---- 1 density over time ------------------------------------------------------
fig, ax = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
ax[0].plot(ts["t"], ts["dens_move_max"], "k", label="peak local density, moving crowd (2 m cell)")
ax[0].plot(ts["t"], ts["dens_plaza_avg"], label="plaza average (moving)")
ax[0].axhline(1.5, color="gold", ls="--", label="1.5 p/m² acceptable (moving)")
ax[0].axhline(2.0, color="red", ls="--", label="2 p/m² critical (moving)")
ax[0].set(ylabel="p/m²", title="Moving crowd vs limits (Oberhagemann 2012, via Haridwar paper)")
ax[0].legend(fontsize=8)
ax[1].plot(ts["t"], ts["dens_static_max"], "k", label="peak local density, bathers (2 m cell)")
ax[1].plot(ts["t"], ts["dens_strip_avg"], label="bathing strip average")
ax[1].axhline(5, color="gold", ls="--", label="5 p/m² max (static)")
ax[1].axhline(6, color="red", ls="--", label="6 p/m² high risk (static)")
ax[1].set(xlabel="time [s]", ylabel="p/m²", title="Standing bathers vs limits (Still 2014, via Haridwar paper)")
ax[1].legend(fontsize=8)
fig.text(0.5, 0.005, NOTE, ha="center", fontsize=7, color="gray")
fig.tight_layout(); fig.savefig(res / "density_timeseries.png", dpi=130); plt.close(fig)

# ---- 2 peak density maps ------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(13, 8))
for a, key, ttl, vmax in ((ax[0], "move", "Peak density - MOVING crowd", 4), (ax[1], "static", "Peak density - BATHERS", 4)):
    pm = np.ma.masked_where(~pk["valid"], pk[key]).T
    im = a.pcolormesh(pk["XE"], pk["YE"], pm, cmap="inferno", vmin=0, vmax=vmax)
    a.add_patch(MplPolygon(bnd, closed=True, fill=False, ec="w", lw=0.6))
    a.set(aspect="equal", title=ttl, xlabel="x [m]")
    fig.colorbar(im, ax=a, shrink=0.6, label="p/m²")
fig.tight_layout(); fig.savefig(res / "peak_density_map.png", dpi=130); plt.close(fig)

# ---- 3 travel time ------------------------------------------------------------
tt = M["travel_time_s"]
labels = ["wait in\nholding", "walk to\nslot", "dip", "exit"]
means = [tt["wait_in_holding_before_slot"]["mean"], tt["walk_to_slot"]["mean"], 300.0, tt["exit_after_dip"]["mean"]]
p95 = [tt["wait_in_holding_before_slot"]["p95"], tt["walk_to_slot"]["p95"], 300.0, tt["exit_after_dip"]["p95"]]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
ax[0].barh(["mean"], [means[0]], color="#e63946", label=labels[0].replace("\n", " "))
left = means[0]
for v, c, l in zip(means[1:], ["#2a9d8f", "#1d4ed8", "#8d99ae"], labels[1:]):
    ax[0].barh(["mean"], [v], left=left, color=c, label=l.replace("\n", " ")); left += v
ax[0].barh(["p95 each"], [sum(p95)], color="#cccccc", label="sum of p95s (upper bound)")
ax[0].set(xlabel="seconds", title=f"Where the time goes (mean total {tt['total_entry_to_exit']['mean']:.0f} s)")
ax[0].legend(fontsize=7)
g = tt["mean_entry_to_dip_by_gate"]
ax[1].bar(list(g.keys()), list(g.values()), color="#457b9d")
ax[1].set(ylabel="seconds", title="Mean time from entering to starting the dip, by gate")
fig.text(0.5, 0.005, NOTE, ha="center", fontsize=7, color="gray")
fig.tight_layout(); fig.savefig(res / "travel_time.png", dpi=130); plt.close(fig)

# ---- 4 queue formation --------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(13, 5.4), gridspec_kw={"width_ratios": [1, 1.1]})
ax[0].stackplot(ts["t"], ts["n_walk"], ts["n_hold"], ts["n_bath"], ts["n_exit"],
                colors=[COL[0], COL[1], COL[2], COL[3]], labels=[LAB[i] for i in range(4)])
ax[0].plot(ts["t"], ts["outside"], "k:", label="waiting outside gates")
ax[0].set(xlabel="time [s]", ylabel="people in sector", title="Who is where")
ax[0].legend(fontsize=7, loc="upper right")
if snap is not None:
    draw_geom(ax[1])
    for k in range(4):
        m = snap["st"] == k
        ax[1].scatter(snap["xy"][m, 0], snap["xy"][m, 1], s=3, c=COL[k])
    ax[1].set_title(f"Snapshot at largest queue, t = {float(snap['t']):.0f} s")
    ax[1].set_xticks([]); ax[1].set_yticks([])
fig.text(0.5, 0.005, NOTE, ha="center", fontsize=7, color="gray")
fig.tight_layout(); fig.savefig(res / "queue_formation.png", dpi=130); plt.close(fig)

# ---- 5 bottlenecks --------------------------------------------------------------
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
b = M["bottleneck"]["bridges"]
names = list(b.keys())
ax[0].bar(names, [b[n]["peak_30s_specific_flow_p_m_s"] for n in names], color="#457b9d", label="peak (30 s)")
ax[0].bar(names, [b[n]["mean_specific_flow_p_m_s"] for n in names], color="#a8dadc", label="mean")
ax[0].axhline(GG, color="r", ls="--", label=f"Green Guide {GG:.2f} p/(m·s)")
ax[0].set(ylabel="specific flow p/(m·s)", title="Flow through each 10 m bridge"); ax[0].legend(fontsize=8)
dips = ts["dips_started"]
ax[1].plot(ts["t"], dips, label="dips started (cumulative)")
ax[1].plot(ts["t"], ts["cum_out"], label="left the ghat")
ax[1].plot(ts["t"], ts["cum_spawned"], label="entered the sector")
ax[1].set(xlabel="time [s]", title="Cumulative curves"); ax[1].legend(fontsize=8)
cap = M["bottleneck"]["ghat_capacity_dips_per_min"]; sus = M["bottleneck"]["ghat_sustained_dip_starts_per_min"]
ax[2].bar(["theoretical\ncapacity", "sustained\nmeasured", "demand"], [cap, sus, M["scenario"]["gates"]["west"]["rate_per_min"] / 0.4],
          color=["#999999", "#1d4ed8", "#e63946"])
ax[2].set(ylabel="people / min", title="Ghat throughput vs demand")
fig.text(0.5, 0.005, NOTE, ha="center", fontsize=7, color="gray")
fig.tight_layout(); fig.savefig(res / "bottleneck.png", dpi=130); plt.close(fig)

# ---- 0 layout --------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 9))
draw_geom(ax)
for txt, x, y in (("WEST bridge\n10 m", -20, 8), ("NORTH bridge\n10 m", 56, 70), ("SOUTH bridge\n10 m", 56, -70),
                  ("PLAZA 90 x 100 m\n(holding queue near the shore)", 40, 0), ("BATHING\nSTRIP", 95, 0),
                  ("exit", 95, 62), ("exit", 95, -62)):
    ax.text(x, y, txt, ha="center", va="center", fontsize=8, color="tab:blue")
ax.axvline(100, color="c", lw=3); ax.text(103, 0, "water", rotation=90, va="center", color="c")
ax.set(xlim=(-45, 110), ylim=(-95, 95), title="Schematic layout used in the simulation")
fig.tight_layout(); fig.savefig(res / "layout.png", dpi=130); plt.close(fig)

# ---- video ------------------------------------------------------------------------
t_f, n_f, xy_f, st_f = fr["t"], fr["n"], fr["xy"], fr["st"]
off = np.concatenate([[0], np.cumsum(n_f)])
t_all, nh, nb = fr["t_all"], fr["n_hold"], fr["n_bath"]


def render(path, step, fps, figsize, dpi, writer):
    idx = np.arange(0, len(t_f), step)
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.6, 1], hspace=0.2)
    ax = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1])
    draw_geom(ax); ax.set(xlim=(-45, 110), ylim=(-95, 95)); ax.set_xticks([]); ax.set_yticks([])
    ax.axvline(100, color="c", lw=3)
    sc = ax.scatter([], [], s=3.5)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=COL[k], label=LAB[k]) for k in range(4)],
              loc="lower left", fontsize=7, framealpha=0.9)
    title = ax.set_title("", fontsize=10)
    ax2.plot(t_all, nh, color=COL[1], label="waiting"); ax2.plot(t_all, nb, color=COL[2], label="bathing")
    ax2.set(xlabel="time [s]", ylabel="people", xlim=(0, t_f[-1])); ax2.legend(fontsize=7, loc="upper right")
    cur = ax2.axvline(0, color="k", lw=1)
    fig.text(0.5, 0.004, NOTE, ha="center", fontsize=6.5, color="gray")

    def update(k):
        i = idx[k]; a, b_ = off[i], off[i + 1]
        sc.set_offsets(xy_f[a:b_]); sc.set_color([COL[int(s)] for s in st_f[a:b_]])
        title.set_text(f"{M['scenario']['pilgrims']} pilgrims, 3 bridges -> 1 ghat   t = {t_f[i]:5.0f} s   in sector: {n_f[i]}")
        cur.set_xdata([t_f[i], t_f[i]])
        return sc, title, cur
    ani = animation.FuncAnimation(fig, update, frames=len(idx), blit=False)
    ani.save(path, writer=writer, dpi=dpi); plt.close(fig)
    print("wrote", path, f"{path.stat().st_size/1e6:.1f} MB, {len(idx)} frames")


render(res / "simulation.mp4", 1, 25, (9, 9.4), 100, animation.FFMpegWriter(fps=25, bitrate=2500))
render(res / "simulation.gif", 3, 12, (6.4, 6.8), 75, animation.PillowWriter(fps=12))

shutil.copy(src / "metrics.json", res / "metrics.json")
shutil.copy(src / "timeseries.csv", res / "timeseries.csv")
print("results/:", sorted(p.name for p in res.iterdir()))
