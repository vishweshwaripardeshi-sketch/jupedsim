#!/usr/bin/env python3
"""Render MP4 + GIF from out_ghat_neck5m/frames.npz and collect PNGs in results/.
SYNTHETIC scenario - see run_ghat.py."""
import pathlib
import shutil
import sys

import imageio_ffmpeg
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import animation
from matplotlib.patches import Polygon as MplPolygon

matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()

root = pathlib.Path(__file__).parent
neck = sys.argv[1] if len(sys.argv) > 1 else "5"
src = root / f"out_ghat_neck{neck}m"
res = root / "results"
res.mkdir(exist_ok=True)

d = np.load(src / "frames.npz")
t, n, xy, sp = d["t"], d["n"], d["xy"], d["sp"]
off = np.concatenate([[0], np.cumsum(n)])
bnd = d["boundary"]
dens_max, queue = d["dens_max"], d["queue"]
total = 5000


def render(path, step, fps, figsize, dpi, writer):
    idx = np.arange(0, len(t), step)
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.4, 1], hspace=0.22)
    ax = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax.add_patch(MplPolygon(bnd, closed=True, fc="#f2f2f2", ec="k"))
    ax.set(aspect="equal", xlim=(-32, 127), ylim=(-64, 64))
    ax.set_xticks([]); ax.set_yticks([])
    for label, (x, y) in {"WEST gate": (-15, 7), "NORTH gate": (24, 58), "SOUTH gate": (24, -62), "bottleneck (5 m)": (90, -8), "GHAT": (112, 18)}.items():
        ax.text(x, y, label, fontsize=7, ha="center", color="tab:blue")
    sc = ax.scatter([], [], s=3, c=[], cmap="RdYlGn", vmin=0, vmax=1.3)
    cb = fig.colorbar(sc, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("speed [m/s]", fontsize=8)
    title = ax.set_title("", fontsize=10)
    ax2.plot(t, queue, color="tab:red", label="queuing in plaza")
    ax2.plot(t, d["sched_cum"] / total * queue.max(), color="gray", lw=0.8, ls=":", label="entered (scaled)")
    ax2.set(xlabel="time [s]", ylabel="people", xlim=(0, t[-1]))
    ax2.legend(fontsize=7, loc="upper right")
    cur = ax2.axvline(0, color="k", lw=1)
    fig.text(0.5, 0.005, "SYNTHETIC scenario - assumed inputs, not real Prayagraj data",
             ha="center", fontsize=7, color="gray")

    def update(k):
        i = idx[k]
        a, b = off[i], off[i + 1]
        sc.set_offsets(xy[a:b])
        sc.set_array(sp[a:b])
        title.set_text(f"5000 pilgrims, 3 gates -> 1 ghat   t = {t[i]:5.0f} s   in sector: {n[i]}   max local density: {dens_max[i]:.1f} p/m²")
        cur.set_xdata([t[i], t[i]])
        return sc, title, cur

    ani = animation.FuncAnimation(fig, update, frames=len(idx), blit=False)
    ani.save(path, writer=writer, dpi=dpi)
    plt.close(fig)
    print("wrote", path, f"{path.stat().st_size/1e6:.1f} MB, {len(idx)} frames")


# MP4: every sample (2 sim-s per frame) at 25 fps -> 50x real time
render(res / "simulation.mp4", 1, 25, (9.5, 8.6), 110,
       animation.FFMpegWriter(fps=25, bitrate=2500))
# GIF: every 3rd sample (6 sim-s per frame) at 12 fps -> 72x, smaller
render(res / "simulation.gif", 3, 12, (7, 6.4), 75,
       animation.PillowWriter(fps=12))

# collect PNG graphs
names = {
    "0_layout.png": "layout.png",
    "1_density_timeseries.png": "density_timeseries.png",
    "2_peak_density_map.png": "peak_density_map.png",
    "3_travel_time.png": "travel_time.png",
    "4_queue.png": "queue_formation.png",
    "5_bottleneck.png": "bottleneck.png",
}
for a, b in names.items():
    shutil.copy(src / a, res / b)
shutil.copy(src / "metrics.json", res / "metrics.json")
shutil.copy(src / "timeseries.csv", res / "timeseries.csv")
print("results/ contains:", sorted(p.name for p in res.iterdir()))
