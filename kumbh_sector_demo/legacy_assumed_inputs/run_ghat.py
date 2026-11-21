#!/usr/bin/env python3
"""
SYNTHETIC scenario: 5000 pilgrims enter through THREE gates and walk to ONE
bathing ghat. Measures density, travel time, queue formation, bottleneck.

!! Layout and all numbers marked ASSUMPTION are placeholders, not measured data.

Layout (metres, x to the right):

            N gate (8 m)
              |
  W gate -->  PLAZA 80x50  ==> NECK (5 m x 20 m) ==> GHAT BASIN 25x30 | water
              |
            S gate (8 m)

Usage:  python run_ghat.py [neck_width_m]   (default 5.0)
"""
import json
import pathlib
import random
import sys
import time

import jupedsim as jps
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shapely
from matplotlib.patches import Polygon as MplPolygon

# ----------------------------------------------------------------------------
# ASSUMPTIONS -----------------------------------------------------------------
# ----------------------------------------------------------------------------
SEED = 7
DT = 0.05
MAX_TIME = 2400.0  # s hard stop
SAMPLE = 2.0  # s between measurements

NECK_W = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0  # m   (bottleneck)
GATE_W = 8.0  # m
# gate -> (number of pilgrims, release rate persons/min)
GATES = {"west": (2000, 240), "north": (1500, 180), "south": (1500, 180)}
SPEED_MEAN, SPEED_SD = 1.1, 0.25  # m/s
RADIUS_MEAN, RADIUS_SD = 0.22, 0.03  # m
SLOW_SPEED = 0.25  # m/s: below this an agent counts as "queuing"

# ----------------------------------------------------------------------------
# GEOMETRY --------------------------------------------------------------------
# ----------------------------------------------------------------------------
g = GATE_W / 2
n = NECK_W / 2
parts = [
    shapely.box(0, -25, 80, 25),  # plaza
    shapely.box(-30, -g, 0, g),  # west gate corridor
    shapely.box(20, 25, 20 + GATE_W, 55),  # north gate corridor
    shapely.box(20, -55, 20 + GATE_W, -25),  # south gate corridor
    shapely.box(80, -n, 100, n),  # neck (bottleneck)
    shapely.box(100, -15, 125, 15),  # ghat basin
]
walkable = shapely.unary_union(parts)
assert walkable.is_valid and walkable.geom_type == "Polygon"

PLAZA = (0, -25, 80, 25)
NECK = (80, -n, 100, n)
BASIN = (100, -15, 125, 15)
MEASURE_X = 90.0  # measurement line across the neck

# spawn boxes at the outer end of each gate corridor
SPAWN = {
    "west": (-29.5, -g + 0.4, -26.0, g - 0.4),
    "north": (20.4, 52.0, 20 + GATE_W - 0.4, 54.6),
    "south": (20.4, -54.6, 20 + GATE_W - 0.4, -52.0),
}

# ----------------------------------------------------------------------------
# SIMULATION SETUP ------------------------------------------------------------
# ----------------------------------------------------------------------------
jps.set_warning_callback(print)
jps.set_error_callback(print)

sim = jps.Simulation(
    model=jps.CollisionFreeSpeedModel(), geometry=walkable, dt=DT
)
# Single exit at the water's edge. No intermediate waypoints: waypoints inside
# a crowd make agents pile up around them (deadlock), routing handles the path.
exit_stage = sim.add_exit_stage([(124, -15), (124, 15), (125, 15), (125, -15)])
journey = jps.JourneyDescription([exit_stage])
journey_id = sim.add_journey(journey)

rng = random.Random(SEED)
sched = {}  # gate -> sorted list of scheduled arrival times
for name, (count, per_min) in GATES.items():
    dtv = 60.0 / per_min
    sched[name] = [i * dtv for i in range(count)]
spawned = {k: 0 for k in GATES}
gate_of: dict[int, str] = {}
sched_time: dict[int, float] = {}
spawn_time: dict[int, float] = {}


def try_spawn(gate: str, t: float) -> bool:
    x0, y0, x1, y1 = SPAWN[gate]
    for _ in range(25):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if any(True for _ in sim.agents_in_range((x, y), 0.85)):
            continue
        v0 = max(0.4, rng.gauss(SPEED_MEAN, SPEED_SD))
        r = min(0.35, max(0.15, rng.gauss(RADIUS_MEAN, RADIUS_SD)))
        try:
            aid = sim.add_agent(
                jps.CollisionFreeSpeedModelAgentParameters(
                    journey_id=journey_id,
                    stage_id=exit_stage,
                    position=(x, y),
                    desired_speed=v0,
                    radius=r,
                )
            )
        except RuntimeError:  # too close to a neighbour/wall: try another spot
            continue
        gate_of[aid] = gate
        sched_time[aid] = sched[gate][spawned[gate]]
        spawn_time[aid] = t
        spawned[gate] += 1
        return True
    return False


# ----------------------------------------------------------------------------
# DENSITY GRID (2 m cells, normalised by walkable area inside each cell) ------
# ----------------------------------------------------------------------------
CELL = 2.0
XE = np.arange(-30, 125 + CELL, CELL)
YE = np.arange(-55, 55 + CELL, CELL)
cell_area = np.zeros((len(XE) - 1, len(YE) - 1))
for i in range(len(XE) - 1):
    for j in range(len(YE) - 1):
        cell_area[i, j] = walkable.intersection(
            shapely.box(XE[i], YE[j], XE[i + 1], YE[j + 1])
        ).area
valid = cell_area >= 0.5 * CELL * CELL  # ignore cells mostly outside
peak_map = np.zeros_like(cell_area)


def in_box(xy, b):
    return (xy[:, 0] >= b[0]) & (xy[:, 0] < b[2]) & (xy[:, 1] >= b[1]) & (xy[:, 1] < b[3])


def box_area(b):
    return walkable.intersection(shapely.box(*b)).area


A_PLAZA, A_NECK, A_BASIN = box_area(PLAZA), box_area(NECK), box_area(BASIN)

# ----------------------------------------------------------------------------
# RUN -------------------------------------------------------------------------
# ----------------------------------------------------------------------------
ts = {k: [] for k in [
    "t", "in_sector", "outside_gates", "dens_plaza", "dens_neck", "dens_basin",
    "dens_max_cell", "queue_n", "queue_len_p95", "neck_speed", "cum_spawned",
    "cum_neck", "cum_exited",
]}
frames_t, frames_n, frames_xy, frames_sp = [], [], [], []  # for animation
prev_pos: dict[int, tuple[float, float]] = {}
crossed: set[int] = set()
cross_times: list[float] = []
exit_info: dict[int, float] = {}  # agent -> exit time
snapshot = {"t": -1, "queue": -1, "xy": None, "speed": None}
total = sum(c for c, _ in GATES.values())
next_sample = 0.0
wall0 = time.time()

while sim.elapsed_time() < MAX_TIME:
    t = sim.elapsed_time()

    # release due agents; those that cannot enter wait OUTSIDE the gate
    for gate in GATES:
        for _ in range(4):  # at most 4 spawns per gate per step
            k = spawned[gate]
            if k < len(sched[gate]) and sched[gate][k] <= t:
                if not try_spawn(gate, t):
                    break
            else:
                break

    sim.iterate()
    t = sim.elapsed_time()

    for aid in sim.removed_agents():
        exit_info[aid] = t

    if t >= next_sample:
        next_sample += SAMPLE
        ags = list(sim.agents())
        n_ag = len(ags)
        ids = [a.id for a in ags]
        xy = np.array([a.position for a in ags]).reshape(-1, 2)

        # speed estimate from displacement since previous sample
        spd = np.full(n_ag, np.nan)
        for k, a in enumerate(ags):
            p = prev_pos.get(a.id)
            if p is not None:
                spd[k] = np.hypot(xy[k, 0] - p[0], xy[k, 1] - p[1]) / SAMPLE
            # bottleneck crossing detection at the measurement line
            if p is not None and p[0] < MEASURE_X <= xy[k, 0] and a.id not in crossed:
                crossed.add(a.id)
                cross_times.append(t)
        prev_pos = {a.id: tuple(xy[k]) for k, a in enumerate(ags)}

        # density
        if n_ag:
            H, _, _ = np.histogram2d(xy[:, 0], xy[:, 1], bins=[XE, YE])
        else:
            H = np.zeros_like(cell_area)
        dens = np.where(valid, H / np.maximum(cell_area, 1e-9), 0.0)
        peak_map = np.maximum(peak_map, dens)

        m_plaza, m_neck, m_basin = in_box(xy, PLAZA), in_box(xy, NECK), in_box(xy, BASIN)
        slow = np.nan_to_num(spd, nan=9.9) < SLOW_SPEED
        qmask = slow & m_plaza
        if qmask.any():
            d = np.hypot(xy[qmask, 0] - 80.0, xy[qmask, 1])
            qlen = float(np.percentile(d, 95))
        else:
            qlen = 0.0
        outside = sum(
            1 for gt in GATES for s in sched[gt][spawned[gt]:] if s <= t
        )
        neck_v = np.nanmean(spd[m_neck]) if m_neck.any() and np.isfinite(spd[m_neck]).any() else np.nan

        ts["t"].append(t)
        ts["in_sector"].append(n_ag)
        ts["outside_gates"].append(outside)
        ts["dens_plaza"].append(m_plaza.sum() / A_PLAZA)
        ts["dens_neck"].append(m_neck.sum() / A_NECK)
        ts["dens_basin"].append(m_basin.sum() / A_BASIN)
        ts["dens_max_cell"].append(float(dens.max()))
        ts["queue_n"].append(int(qmask.sum()))
        ts["queue_len_p95"].append(qlen)
        ts["neck_speed"].append(float(neck_v))
        ts["cum_spawned"].append(sum(spawned.values()))
        ts["cum_neck"].append(len(crossed))
        ts["cum_exited"].append(len(exit_info))

        frames_t.append(t)
        frames_n.append(n_ag)
        frames_xy.append(xy.astype(np.float32))
        frames_sp.append(np.nan_to_num(spd, nan=0.0).astype(np.float32))

        if qmask.sum() > snapshot["queue"]:
            snapshot.update(t=t, queue=int(qmask.sum()), xy=xy.copy(), speed=np.nan_to_num(spd, nan=0.0))

        if int(t) % 120 == 0 and abs(t - round(t)) < SAMPLE:
            print(f"t={t:6.0f}s  in={n_ag:4d}  waiting outside={outside:4d}  exited={len(exit_info):4d}/{total}  maxdens={dens.max():.2f}  wall={time.time()-wall0:.0f}s", flush=True)

    if sum(spawned.values()) == total and sim.agent_count() == 0:
        break

# ----------------------------------------------------------------------------
# METRICS ---------------------------------------------------------------------
# ----------------------------------------------------------------------------
T = {k: np.array(v, dtype=float) for k, v in ts.items()}
out = pathlib.Path(__file__).parent / f"out_ghat_neck{NECK_W:g}m"
out.mkdir(exist_ok=True)

done = [a for a in exit_info if a in spawn_time]
tt_sector = np.array([exit_info[a] - spawn_time[a] for a in done])
tt_total = np.array([exit_info[a] - sched_time[a] for a in done])
wait_out = np.array([spawn_time[a] - sched_time[a] for a in done])
gates_arr = np.array([gate_of[a] for a in done])


def stats(x):
    if len(x) == 0:
        return {}
    return {"mean": float(x.mean()), "median": float(np.median(x)),
            "p95": float(np.percentile(x, 95)), "max": float(x.max())}


# bottleneck flow: crossings in sliding 30 s windows
ct = np.array(sorted(cross_times))
win = 30.0
if len(ct):
    edges = np.arange(0, ct.max() + win, win)
    cnt, _ = np.histogram(ct, bins=edges)
    flow_win = cnt / win / NECK_W  # p/(m*s)
    flow_t = edges[:-1] + win / 2
    sat = flow_win >= 0.8 * flow_win.max()
    sustained = float(np.mean(flow_win[sat]))
else:
    flow_win = flow_t = np.array([])
    sustained = float("nan")

demand_flow = sum(r for _, r in GATES.values()) / 60.0 / NECK_W
peak_i = int(np.argmax(T["queue_n"]))
metrics = {
    "scenario": {"pilgrims": total, "gates": {k: {"n": c, "rate_per_min": r} for k, (c, r) in GATES.items()},
                 "neck_width_m": NECK_W, "synthetic": True},
    "completed": f"{len(exit_info)}/{total}",
    "simulated_time_s": float(sim.elapsed_time()),
    "wall_time_s": round(time.time() - wall0),
    "density": {
        "peak_local_2m_cell_p_m2": float(T["dens_max_cell"].max()),
        "time_above_4_p_m2_s": float((T["dens_max_cell"] > 4).sum() * SAMPLE),
        "time_above_6_p_m2_s": float((T["dens_max_cell"] > 6).sum() * SAMPLE),
        "peak_plaza_avg": float(T["dens_plaza"].max()),
        "peak_neck_avg": float(T["dens_neck"].max()),
        "peak_basin_avg": float(T["dens_basin"].max()),
    },
    "travel_time_s": {
        "in_sector": stats(tt_sector),
        "incl_wait_outside_gates": stats(tt_total),
        "by_gate_in_sector_mean": {g_: float(tt_sector[gates_arr == g_].mean()) for g_ in GATES if (gates_arr == g_).any()},
    },
    "queue": {
        "max_slow_agents_in_plaza": int(T["queue_n"].max()),
        "time_of_max_queue_s": float(T["t"][peak_i]),
        "max_queue_length_p95_m": float(T["queue_len_p95"].max()),
        "max_waiting_outside_gates": int(T["outside_gates"].max()),
        "wait_outside_gates_s": stats(wait_out),
        "queue_dissolved_at_s": float(T["t"][np.where(T["queue_n"] > 20)[0][-1]]) if (T["queue_n"] > 20).any() else 0.0,
    },
    "bottleneck": {
        "neck_width_m": NECK_W,
        "demand_flow_p_m_s": demand_flow,
        "sustained_flow_p_m_s_(windows>=80%_of_peak)": sustained,
        "peak_30s_flow_p_m_s": float(flow_win.max()) if len(flow_win) else None,
        "sustained_throughput_p_per_min": sustained * NECK_W * 60 if len(ct) else None,
        "mean_speed_in_neck_m_s": float(np.nanmean(T["neck_speed"])),
        "min_speed_in_neck_m_s": float(np.nanmin(T["neck_speed"])) if np.isfinite(T["neck_speed"]).any() else None,
    },
}
np.savez_compressed(
    out / "frames.npz", t=np.array(frames_t), n=np.array(frames_n),
    xy=np.concatenate(frames_xy), sp=np.concatenate(frames_sp),
    boundary=np.array(list(walkable.exterior.coords)),
    sched_cum=T["cum_spawned"], queue=T["queue_n"], dens_max=T["dens_max_cell"],
)
(out / "metrics.json").write_text(json.dumps(metrics, indent=2))
np.savetxt(out / "timeseries.csv", np.column_stack([T[k] for k in ts]),
           delimiter=",", header=",".join(ts), comments="")

# ----------------------------------------------------------------------------
# FIGURES ---------------------------------------------------------------------
# ----------------------------------------------------------------------------
bnd = list(walkable.exterior.coords)

# 1. density over time
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(T["t"], T["dens_max_cell"], label="peak local (2 m cell)", color="k")
ax.plot(T["t"], T["dens_plaza"], label="plaza average")
ax.plot(T["t"], T["dens_neck"], label="neck average")
ax.plot(T["t"], T["dens_basin"], label="ghat basin average")
ax.axhline(4, color="orange", ls="--", lw=1, label="4 p/m² warning")
ax.axhline(6, color="red", ls="--", lw=1, label="6 p/m² critical")
ax.set(xlabel="time [s]", ylabel="density [p/m²]", title="Density over time (synthetic)")
ax.legend(ncol=2, fontsize=8)
fig.tight_layout(); fig.savefig(out / "1_density_timeseries.png", dpi=130); plt.close(fig)

# 2. peak density map
fig, ax = plt.subplots(figsize=(11, 6))
pm = np.ma.masked_where(~valid, peak_map).T
im = ax.pcolormesh(XE, YE, pm, cmap="inferno", vmin=0, vmax=max(6, np.nanmax(pm)))
ax.add_patch(MplPolygon(bnd, closed=True, fill=False, ec="w", lw=0.8))
fig.colorbar(im, label="peak density over run [p/m²]")
ax.set(aspect="equal", title="Where density peaks (2 m cells)", xlabel="x [m]", ylabel="y [m]")
fig.tight_layout(); fig.savefig(out / "2_peak_density_map.png", dpi=130); plt.close(fig)

# 3. travel time
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for g_ in GATES:
    m = gates_arr == g_
    if m.any():
        ax[0].hist(tt_sector[m], bins=40, alpha=0.55, label=f"{g_} gate")
ax[0].set(xlabel="travel time in sector [s]", ylabel="pilgrims", title="Travel time by gate")
ax[0].legend()
ax[1].hist(tt_total, bins=40, color="tab:red", alpha=0.7, label="incl. wait outside gates")
ax[1].hist(tt_sector, bins=40, color="tab:blue", alpha=0.6, label="in sector only")
ax[1].set(xlabel="time [s]", title="Effect of waiting outside the gates")
ax[1].legend()
fig.tight_layout(); fig.savefig(out / "3_travel_time.png", dpi=130); plt.close(fig)

# 4. queue formation
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
ax[0].plot(T["t"], T["queue_n"], label="slow agents in plaza (<0.25 m/s)")
ax[0].plot(T["t"], T["outside_gates"], label="waiting outside gates", color="tab:red")
ax[0].set(xlabel="time [s]", ylabel="people", title="Queue formation")
ax[0].legend(fontsize=8)
if snapshot["xy"] is not None:
    ax[1].add_patch(MplPolygon(bnd, closed=True, fc="#f2f2f2", ec="k"))
    sc = ax[1].scatter(snapshot["xy"][:, 0], snapshot["xy"][:, 1], c=snapshot["speed"],
                       s=4, cmap="RdYlGn", vmin=0, vmax=1.3)
    fig.colorbar(sc, ax=ax[1], label="speed [m/s]")
    ax[1].set(aspect="equal", xlim=(-32, 127), ylim=(-57, 57),
              title=f"Snapshot at max queue (t={snapshot['t']:.0f}s)")
fig.tight_layout(); fig.savefig(out / "4_queue.png", dpi=130); plt.close(fig)

# 5. bottleneck
fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))
ax[0].plot(T["t"], T["cum_spawned"], label="entered sector")
ax[0].plot(T["t"], T["cum_neck"], label="passed neck")
ax[0].plot(T["t"], T["cum_exited"], label="reached ghat")
ax[0].set(xlabel="time [s]", ylabel="cumulative pilgrims", title="Cumulative curves")
ax[0].legend(fontsize=8)
ax[1].plot(flow_t, flow_win, marker="o", ms=3, label="measured (30 s windows)")
ax[1].axhline(demand_flow, color="r", ls="--", label=f"demand {demand_flow:.2f}")
ax[1].set(xlabel="time [s]", ylabel="specific flow [p/(m·s)]", title=f"Flow across neck ({NECK_W:g} m)")
ax[1].legend(fontsize=8)
ax[2].plot(T["t"], T["neck_speed"], label="mean speed in neck")
ax2 = ax[2].twinx(); ax2.plot(T["t"], T["dens_neck"], color="tab:red", label="neck density")
ax[2].set(xlabel="time [s]", ylabel="speed [m/s]", title="Neck speed vs density")
ax2.set_ylabel("density [p/m²]")
fig.tight_layout(); fig.savefig(out / "5_bottleneck.png", dpi=130); plt.close(fig)

# 6. geometry
fig, ax = plt.subplots(figsize=(11, 6))
ax.add_patch(MplPolygon(bnd, closed=True, fc="#eeeeee", ec="k"))
for name, (x0, y0, x1, y1) in SPAWN.items():
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"{name} gate", ha="center", fontsize=8, color="tab:blue")
ax.axvline(MEASURE_X, ymin=0.4, ymax=0.6, color="r")
ax.text(MEASURE_X, n + 1, "measure line", color="r", ha="center", fontsize=8)
ax.text(112, 0, "GHAT\nbasin", ha="center")
ax.set(aspect="equal", xlim=(-32, 127), ylim=(-57, 57), title="Synthetic layout")
fig.tight_layout(); fig.savefig(out / "0_layout.png", dpi=130); plt.close(fig)

print(json.dumps(metrics, indent=2))
print("Outputs:", out)
