#!/usr/bin/env python3
"""MP4 per run: colour = pilgrim type; grey = static langar queuers; black ring = bathing.
usage: python bn_video.py run_name [run_name ...]"""
import json
import pathlib
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
OUT = root / "kumbh_bottleneck_study" / "videos"
OUT.mkdir(parents=True, exist_ok=True)
CC = {0: "#1f77b4", 1: "#ff7f0e", 2: "#d62728", 3: "#2ca02c", 4: "#17becf"}
LAB = {0: "adult (single)", 1: "elderly", 2: "child (with group)", 3: "adult, rural group", 4: "adult, urban group"}
TITLE = {"B3": "B3 width cascade: 50 m route -> 10 m bridge -> 3 m alley", "B4": "B4 Akhara thoroughfare (50 m) with langar queue",
         "B5": "B5 Sangam shoreline front (barricade strip)", "B6": "B6 river-exit control"}

for name in sys.argv[1:]:
    d = root / "bn_runs" / name
    M = json.loads((d / "metrics.json").read_text())
    ts = np.genfromtxt(d / "timeseries.csv", delimiter=",", names=True)
    fr = np.load(d / "frames.npz")
    t, n, xy, cls, st, bnd = fr["t"], fr["n"], fr["xy"], fr["cls"], fr["st"], fr["boundary"]
    off = np.concatenate([[0], np.cumsum(n)])
    step = max(1, int(np.ceil(len(t) / 420)))
    idx = np.arange(0, len(t), step)
    x0, y0, x1, y1 = bnd[:, 0].min(), bnd[:, 1].min(), bnd[:, 0].max(), bnd[:, 1].max()
    asp = (y1 - y0 + 6) / (x1 - x0 + 6)
    fw = 9.0
    fh = min(10.0, max(3.2, fw * asp)) + 2.4
    fig = plt.figure(figsize=(fw, fh))
    gs = fig.add_gridspec(2, 1, height_ratios=[fh - 2.4, 2.0], hspace=0.18)
    ax = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1])
    ax.add_patch(MplPolygon(bnd, closed=True, fc="#f4f4f4", ec="k", lw=0.9))
    ax.set(xlim=(x0 - 3, x1 + 3), ylim=(y0 - 3, y1 + 3), aspect="equal"); ax.set_xticks([]); ax.set_yticks([])
    sc = ax.scatter([], [], s=6)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=CC[k], label=LAB[k]) for k in range(5)] +
              [Line2D([], [], marker="o", ls="", color="#999", label="static queuer")], loc="upper left", fontsize=6.5, framealpha=0.9, ncol=2)
    ttl = ax.set_title("", fontsize=9)
    if M["bottleneck"] in ("B5", "B6"):
        ax2.plot(ts["t"], ts["n_hold"], c="#d62728", label="waiting"); ax2.plot(ts["t"], ts["n_bath"], c="#1d4ed8", label="bathing")
    else:
        ax2.plot(ts["t"], ts["n_walk"], c="#1f77b4", label="walking"); ax2.plot(ts["t"], ts["slow_n"], c="#d62728", label="slow (<0.25 m/s)")
    ax2.set(xlabel="time [s]", ylabel="people", xlim=(0, t[-1])); ax2.legend(fontsize=7, loc="upper right")
    cur = ax2.axvline(0, c="k", lw=1)
    fig.text(0.5, 0.004, "Synthetic geometry - book widths, assumed lengths; crowd mix per Rai et al. + assumptions", ha="center", fontsize=6.5, color="gray")

    def update(k):
        i = idx[k]; a, b = off[i], off[i + 1]
        c = [("#999999" if s == 4 else CC[int(q)]) for q, s in zip(cls[a:b], st[a:b])]
        sc.set_offsets(xy[a:b]); sc.set_color(c)
        sc.set_edgecolors(["k" if s == 2 else "none" for s in st[a:b]]); sc.set_linewidths(0.6)
        ttl.set_text(f"{TITLE[M['bottleneck']]}   start {M['rho0']} p/m²   {M['population']}   t = {t[i]:5.0f} s   n = {n[i]}")
        cur.set_xdata([t[i], t[i]])
        return sc, ttl, cur

    ani = animation.FuncAnimation(fig, update, frames=len(idx), blit=False)
    path = OUT / f"{name}.mp4"
    ani.save(path, writer=animation.FFMpegWriter(fps=20, bitrate=1800), dpi=85)
    plt.close(fig)
    print("wrote", path, f"{path.stat().st_size/1e6:.1f} MB, {len(idx)} frames", flush=True)
