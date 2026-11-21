#!/usr/bin/env python3
"""
Kumbh ghat sector: 5000 pilgrims, THREE gates (pontoon bridges) -> ONE bathing ghat,
with a 5-minute dip, holding queue and exit flow. JuPedSim 1.4.2.

Every input is tagged  [SRC: ...]  (taken from a supplied paper)  or  [ASSUMED]
(my choice - NOT from a source). Geometry is schematic: the papers give widths and
lengths but no coordinates/drawings, so the layout is a stylised sector.

Layout (m):
   west bridge (10 wide) ->|                     |
   north bridge (10 wide, from +y) ->  PLAZA 90x100  -> BATHING STRIP 10 deep x 100 frontage | water
   south bridge (10 wide, from -y) ->|                     |
   bathers leave along the shore through two exit passages (north end / south end)

Usage: python run_kumbh.py [n_pilgrims=5000]
"""
import json
import pathlib
import random
import sys
import time

import jupedsim as jps
import numpy as np
import shapely

# =============================================================================
# INPUTS
# =============================================================================
N_TOTAL = int(sys.argv[1]) if len(sys.argv) > 1 else 5000  # [USER REQUEST]
SEED = 11
DT = 0.05
MAX_TIME = 5000.0
SAMPLE = 1.0  # s between measurements [ASSUMED]
FRAME_EVERY = 2  # keep every 2nd sample for the animation

# ---- from the papers --------------------------------------------------------
BRIDGE_W = 10.0  # m  [SRC: Mehrotra & Vera, Prayagraj PDF p.49 infographic "Width of the pontoon bridges 10 m"]
DWELL = 300.0  # s  [SRC: Haridwar paper 3.4: avg 5 min per holy dip]
SPEED_MEAN = 1.3  # m/s [SRC: Still PhD thesis 3.1.3: fast steady walk ~1.3 m/s]
BODY_WIDTH = 0.5  # m  [SRC: Still 2019 (50x30 cm ellipse); Haridwar paper (0.5 m)]
STRIP_DEPTH = 10.0  # m  [SRC: Prayagraj PDF p.42: shore strip 2-10 m wide; upper bound used]
GREEN_GUIDE_FLOW = 109 / 60.0  # p/(m s) [SRC: Still PhD thesis 3.1.6 Green Guide 109 p/m/min]
LIM_MOVING_OK, LIM_MOVING_CRIT = 1.5, 2.0  # p/m2 [SRC: Haridwar paper citing Oberhagemann 2012]
LIM_STATIC_HIGH, LIM_STATIC_RISK = 5.0, 6.0  # p/m2 [SRC: Haridwar paper citing Still 2014]
LIM_GREEN_GUIDE = 4.0  # p/m2 [SRC: Still PhD thesis 3.2 Green Guide limit]
FLAT_ARRIVAL = True  # [SRC: Still 2019 Fig.2 "transport limited" = flat arrival profile]

# ---- assumed (not in any supplied paper) ------------------------------------
SPEED_SD = 0.25  # m/s  [ASSUMED]
RADIUS_SD = 0.02  # m   [ASSUMED]
BRIDGE_L = 40.0  # m    [ASSUMED]
PLAZA_W, PLAZA_H = 90.0, 100.0  # m [ASSUMED]; strip frontage = PLAZA_H
SLOT_SPACING = 0.7  # m -> ~2 bathers/m2 static [ASSUMED]
EXIT_W, EXIT_L = 10.0, 20.0  # m [ASSUMED]
# gate: (pilgrims, release rate per min). Split 40/30/30 [ASSUMED]; flat profile [SRC above]
SPLIT = {"west": 0.4, "north": 0.3, "south": 0.3}
TOTAL_RATE = 600.0  # persons/min across all gates [ASSUMED]
HOLD_SPACING = 4.0  # m between holding waypoints [ASSUMED]

R_MEAN = BODY_WIDTH / 2

# =============================================================================
# GEOMETRY
# =============================================================================
H2 = PLAZA_H / 2
parts = [
    shapely.box(0, -H2, PLAZA_W, H2),  # plaza
    shapely.box(PLAZA_W, -H2, PLAZA_W + STRIP_DEPTH, H2),  # bathing strip
    shapely.box(-BRIDGE_L, -BRIDGE_W / 2, 0, BRIDGE_W / 2),  # west bridge
    shapely.box(40, H2, 40 + BRIDGE_W, H2 + BRIDGE_L),  # north bridge
    shapely.box(40, -H2 - BRIDGE_L, 40 + BRIDGE_W, -H2),  # south bridge
    shapely.box(PLAZA_W, H2, PLAZA_W + EXIT_W, H2 + EXIT_L),  # north exit passage
    shapely.box(PLAZA_W, -H2 - EXIT_L, PLAZA_W + EXIT_W, -H2),  # south exit passage
]
walkable = shapely.unary_union(parts)
assert walkable.is_valid and walkable.geom_type == "Polygon"
X_WATER = PLAZA_W + STRIP_DEPTH

jps.set_warning_callback(print)
jps.set_error_callback(print)
sim = jps.Simulation(model=jps.CollisionFreeSpeedModel(), geometry=walkable, dt=DT)

# ---- exits ------------------------------------------------------------------
ex_n = sim.add_exit_stage([(PLAZA_W + 1, H2 + EXIT_L - 1), (PLAZA_W + EXIT_W - 1, H2 + EXIT_L - 1),
                           (PLAZA_W + EXIT_W - 1, H2 + EXIT_L), (PLAZA_W + 1, H2 + EXIT_L)])
ex_s = sim.add_exit_stage([(PLAZA_W + 1, -H2 - EXIT_L), (PLAZA_W + EXIT_W - 1, -H2 - EXIT_L),
                           (PLAZA_W + EXIT_W - 1, -H2 - EXIT_L + 1), (PLAZA_W + 1, -H2 - EXIT_L + 1)])
jr_exit_n = sim.add_journey(jps.JourneyDescription([ex_n]))
jr_exit_s = sim.add_journey(jps.JourneyDescription([ex_s]))

# ---- bathing slots: grid in the strip, filled from the water edge back -------
xs = np.arange(X_WATER - 0.6, PLAZA_W + 0.5, -SLOT_SPACING)
ys = np.arange(-H2 + 0.6, H2 - 0.5, SLOT_SPACING)
# v2 layout (fix for the v1 jam): slots only in the water-side 10 columns, a clear
# walkway on the plaza side for leavers, and a 1.7 m aisle after every 3 slot rows.
# [ASSUMED] walkway/aisle widths; they stop people being boxed in.
SLOT_COLS, ROW_GROUP, AISLE = 10, 3, 1.7
xs = X_WATER - 0.6 - SLOT_SPACING * np.arange(SLOT_COLS)
ys, _y = [], -H2 + 0.6
while _y + (ROW_GROUP - 1) * SLOT_SPACING <= H2 - 0.6:
    ys += [_y + k * SLOT_SPACING for k in range(ROW_GROUP)]
    _y += (ROW_GROUP - 1) * SLOT_SPACING + AISLE
slot_xy = np.array([(x, y) for x in xs for y in ys])
N_SLOTS = len(slot_xy)
slot_stage, slot_journey = [], []
for (x, y) in slot_xy:
    st = sim.add_waypoint_stage((float(x), float(y)), 0.3)
    slot_stage.append(st)
    slot_journey.append(sim.add_journey(jps.JourneyDescription([st])))
free_slot = np.ones(N_SLOTS, dtype=bool)
GHAT_CAP_PER_MIN = N_SLOTS / DWELL * 60.0

# ---- holding waypoints (queue area in front of the strip) ---------------------
hold_y = np.arange(-H2 + 4, H2 - 3, HOLD_SPACING)
HOLD_X = PLAZA_W - 6.0
hold_stage, hold_journey = [], []
for y in hold_y:
    st = sim.add_waypoint_stage((HOLD_X, float(y)), 2.0)
    hold_stage.append(st)
    hold_journey.append(sim.add_journey(jps.JourneyDescription([st])))
GATE_HOLD = {  # which holding points each gate's pilgrims queue at
    "west": [i for i, y in enumerate(hold_y) if -H2 / 3 <= y <= H2 / 3],
    "north": [i for i, y in enumerate(hold_y) if y > H2 / 3],
    "south": [i for i, y in enumerate(hold_y) if y < -H2 / 3],
}

# ---- arrival schedule (flat = transport-limited) ----------------------------
counts = {g: int(round(N_TOTAL * s)) for g, s in SPLIT.items()}
counts["west"] += N_TOTAL - sum(counts.values())
rates = {g: TOTAL_RATE * s for g, s in SPLIT.items()}
sched = {g: [i * 60.0 / rates[g] for i in range(counts[g])] for g in SPLIT}
SPAWN = {
    "west": (-BRIDGE_L + 0.6, -BRIDGE_W / 2 + 0.6, -BRIDGE_L + 3.5, BRIDGE_W / 2 - 0.6),
    "north": (40.6, H2 + BRIDGE_L - 3.5, 40 + BRIDGE_W - 0.6, H2 + BRIDGE_L - 0.6),
    "south": (40.6, -H2 - BRIDGE_L + 0.6, 40 + BRIDGE_W - 0.6, -H2 - BRIDGE_L + 3.5),
}
# measurement lines at the bridge mouths: (axis, coord, direction)
LINES = {"west": ("x", 0.0, +1), "north": ("y", H2, -1), "south": ("y", -H2, +1)}

rng = random.Random(SEED)
spawned = {g: 0 for g in SPLIT}

# per-agent bookkeeping
A: dict[int, dict] = {}
spawn_fail = 0


def pick_slot(ax, ay):
    idx = np.flatnonzero(free_slot)
    if len(idx) == 0:
        return None
    cost = (X_WATER - slot_xy[idx, 0]) + 0.3 * np.abs(slot_xy[idx, 1] - ay)
    return int(idx[np.argmin(cost)])


def try_spawn(gate, t):
    x0, y0, x1, y1 = SPAWN[gate]
    for _ in range(25):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if any(True for _ in sim.agents_in_range((x, y), 0.9)):
            continue
        v0 = min(1.8, max(0.5, rng.gauss(SPEED_MEAN, SPEED_SD)))
        r = min(0.3, max(0.2, rng.gauss(R_MEAN, RADIUS_SD)))
        sl = pick_slot(x, y)
        if sl is not None:
            jid, sid, state = slot_journey[sl], slot_stage[sl], "toslot"
        else:
            k = rng.choice(GATE_HOLD[gate])
            jid, sid, state = hold_journey[k], hold_stage[k], "hold"
        try:
            aid = sim.add_agent(jps.CollisionFreeSpeedModelAgentParameters(
                journey_id=jid, stage_id=sid, position=(x, y), desired_speed=v0, radius=r))
        except RuntimeError:
            continue
        if sl is not None:
            free_slot[sl] = False
        A[aid] = dict(gate=gate, state=state, slot=sl, t_spawn=t,
                      t_assign=t if sl is not None else None, t_bath=None,
                      t_bath_end=None, t_exit=None, timeout=False, crossed=False)
        spawned[gate] += 1
        return True
    return False


# =============================================================================
# DENSITY GRID
# =============================================================================
CELL = 2.0
XE = np.arange(-BRIDGE_L, X_WATER + CELL, CELL)
YE = np.arange(-H2 - BRIDGE_L, H2 + BRIDGE_L + CELL, CELL)
cell_area = np.zeros((len(XE) - 1, len(YE) - 1))
for i in range(len(XE) - 1):
    for j in range(len(YE) - 1):
        cell_area[i, j] = walkable.intersection(shapely.box(XE[i], YE[j], XE[i + 1], YE[j + 1])).area
valid = cell_area >= 0.5 * CELL * CELL
peak_move = np.zeros_like(cell_area)
peak_static = np.zeros_like(cell_area)
STRIP_AREA = PLAZA_H * STRIP_DEPTH
PLAZA_AREA = PLAZA_W * PLAZA_H

STATE_ID = {"toslot": 0, "hold": 1, "bath": 2, "exit": 3}

# =============================================================================
# RUN
# =============================================================================
ts = {k: [] for k in ["t", "n_sector", "n_walk", "n_hold", "n_bath", "n_exit", "outside",
                      "dens_move_max", "dens_static_max", "dens_plaza_avg", "dens_strip_avg",
                      "dips_started", "cum_spawned", "cum_out"]}
fr_t, fr_n, fr_xy, fr_st = [], [], [], []
cross = {g: [] for g in SPLIT}
prev = {}
removed_n = 0
snap = {"hold": -1}
n_timeout = 0
wall0 = time.time()
next_sample = 0.0
sample_k = 0
print(f"slots={N_SLOTS} (ghat capacity {GHAT_CAP_PER_MIN:.0f} dips/min at {SLOT_SPACING} m spacing), holding pts={len(hold_y)}", flush=True)

while sim.elapsed_time() < MAX_TIME:
    t = sim.elapsed_time()
    for gate in SPLIT:
        for _ in range(6):
            k = spawned[gate]
            if k < counts[gate] and sched[gate][k] <= t:
                if not try_spawn(gate, t):
                    break
            else:
                break
    sim.iterate()
    t = sim.elapsed_time()
    for aid in sim.removed_agents():
        if aid in A and A[aid]["state"] == "exit":
            A[aid]["t_exit"] = t
            A[aid]["state"] = "done"
            removed_n += 1

    if t >= next_sample:
        next_sample += SAMPLE
        sample_k += 1
        ags = list(sim.agents())
        pos = {a.id: a.position for a in ags}

        # --- state transitions ---
        # 1) arrivals at slot -> start dip; dwell finished -> exit
        for aid, p in pos.items():
            s = A.get(aid)
            if s is None:
                continue
            if s["state"] == "toslot":
                sx, sy = slot_xy[s["slot"]]
                near = np.hypot(p[0] - sx, p[1] - sy) < 0.9
                late = t - s["t_assign"] > 400.0
                if near or late:
                    s["state"] = "bath"; s["t_bath"] = t; s["timeout"] = (not near)
                    n_timeout += (not near)
            elif s["state"] == "bath" and t - s["t_bath"] >= DWELL:
                s["state"] = "exit"; s["t_bath_end"] = t
                free_slot[s["slot"]] = True
                if p[1] >= 0:
                    sim.switch_agent_journey(aid, jr_exit_n, ex_n)
                else:
                    sim.switch_agent_journey(aid, jr_exit_s, ex_s)
        # 2) release holding agents to free slots (closest to the ghat first)
        n_free = int(free_slot.sum())
        if n_free:
            holders = sorted((aid for aid, s in A.items() if s["state"] == "hold" and aid in pos),
                             key=lambda a: -pos[a][0])
            for aid in holders[:n_free]:
                sl = pick_slot(pos[aid][0], pos[aid][1])
                if sl is None:
                    break
                free_slot[sl] = False
                s = A[aid]; s["slot"] = sl; s["state"] = "toslot"; s["t_assign"] = t
                sim.switch_agent_journey(aid, slot_journey[sl], slot_stage[sl])

        # --- crossings at bridge mouths ---
        for aid, p in pos.items():
            q = prev.get(aid)
            s = A.get(aid)
            if q is not None and s is not None and not s["crossed"]:
                ax, c, d = LINES[s["gate"]]
                i = 0 if ax == "x" else 1
                if (q[i] - c) * d < 0 <= (p[i] - c) * d:
                    s["crossed"] = True
                    cross[s["gate"]].append(t)
        prev = pos

        # --- measurements ---
        ids = list(pos.keys())
        xy = np.array([pos[i] for i in ids]).reshape(-1, 2)
        st = np.array([STATE_ID.get(A[i]["state"], 0) if i in A else 0 for i in ids], dtype=np.uint8)
        mv = st != 2
        for arr, mask, store in ((xy[mv], None, "m"), (xy[~mv], None, "s")):
            if len(arr):
                H, _, _ = np.histogram2d(arr[:, 0], arr[:, 1], bins=[XE, YE])
            else:
                H = np.zeros_like(cell_area)
            d_ = np.where(valid, H / np.maximum(cell_area, 1e-9), 0.0)
            if store == "m":
                dm = d_; peak_move = np.maximum(peak_move, d_)
            else:
                ds = d_; peak_static = np.maximum(peak_static, d_)
        in_plaza = (xy[:, 0] >= 0) & (xy[:, 0] < PLAZA_W) if len(xy) else np.array([], bool)
        in_strip = (xy[:, 0] >= PLAZA_W) & (np.abs(xy[:, 1]) <= H2) if len(xy) else np.array([], bool)
        outside = sum(1 for g in SPLIT for x_ in sched[g][spawned[g]:] if x_ <= t)
        ts["t"].append(t); ts["n_sector"].append(len(ids))
        ts["n_walk"].append(int((st == 0).sum())); ts["n_hold"].append(int((st == 1).sum()))
        ts["n_bath"].append(int((st == 2).sum())); ts["n_exit"].append(int((st == 3).sum()))
        ts["outside"].append(outside)
        ts["dens_move_max"].append(float(dm.max())); ts["dens_static_max"].append(float(ds.max()))
        ts["dens_plaza_avg"].append(float((mv & in_plaza).sum() / PLAZA_AREA) if len(xy) else 0.0)
        ts["dens_strip_avg"].append(float((in_strip).sum() / STRIP_AREA) if len(xy) else 0.0)
        ts["dips_started"].append(sum(1 for s_ in A.values() if s_["t_bath"] is not None))
        ts["cum_spawned"].append(sum(spawned.values())); ts["cum_out"].append(removed_n)
        if int((st == 1).sum()) > snap["hold"]:
            snap.update(hold=int((st == 1).sum()), t=t, xy=xy.copy(), st=st.copy())
        if sample_k % FRAME_EVERY == 0:
            fr_t.append(t); fr_n.append(len(ids)); fr_xy.append(xy.astype(np.float32)); fr_st.append(st)
        if int(t) % 120 == 0 and abs(t - round(t)) < SAMPLE:
            print(f"t={t:6.0f}s in={len(ids):4d} hold={ts['n_hold'][-1]:4d} bath={ts['n_bath'][-1]:4d} "
                  f"exited={removed_n:4d}/{N_TOTAL} movmax={dm.max():.2f} statmax={ds.max():.2f} wall={time.time()-wall0:.0f}s", flush=True)

    if sum(spawned.values()) == N_TOTAL and sim.agent_count() == 0:
        break

# =============================================================================
# METRICS
# =============================================================================
T = {k: np.array(v, dtype=float) for k, v in ts.items()}
out = pathlib.Path(__file__).parent / f"out_kumbh_{N_TOTAL}"
out.mkdir(exist_ok=True)
np.savez_compressed(out / "frames.npz", t=np.array(fr_t), n=np.array(fr_n),
                    xy=np.concatenate(fr_xy), st=np.concatenate(fr_st),
                    boundary=np.array(list(walkable.exterior.coords)),
                    n_hold=T["n_hold"], n_bath=T["n_bath"], t_all=T["t"])
np.savez_compressed(out / "peakmaps.npz", XE=XE, YE=YE, valid=valid, move=peak_move, static=peak_static,
                    boundary=np.array(list(walkable.exterior.coords)))
if snap.get("xy") is not None:
    np.savez_compressed(out / "snapshot.npz", xy=snap["xy"], st=snap["st"], t=snap["t"])
np.savetxt(out / "timeseries.csv", np.column_stack([T[k] for k in ts]), delimiter=",",
           header=",".join(ts), comments="")

done = [a for a, s in A.items() if s["t_exit"] is not None]


def arr(f):
    return np.array([f(A[a]) for a in done], dtype=float)


t_hold_wait = arr(lambda s: (s["t_assign"] - s["t_spawn"]))
t_to_slot = arr(lambda s: (s["t_bath"] - s["t_assign"]))
t_total = arr(lambda s: (s["t_exit"] - s["t_spawn"]))
t_in_exit = arr(lambda s: (s["t_exit"] - s["t_bath_end"]))
t_reach_ghat = arr(lambda s: (s["t_bath"] - s["t_spawn"]))
gates_arr = np.array([A[a]["gate"] for a in done])


def stats(x):
    return {} if len(x) == 0 else {"mean": float(x.mean()), "median": float(np.median(x)),
                                   "p95": float(np.percentile(x, 95)), "max": float(x.max())}


win = 30.0
bridge = {}
for g, tl in cross.items():
    tl = np.array(sorted(tl))
    if len(tl) > 5:
        edges = np.arange(0, tl.max() + win, win)
        cnt, _ = np.histogram(tl, bins=edges)
        fw = cnt / win / BRIDGE_W
        mid = fw[1:-1] if len(fw) > 3 else fw
        bridge[g] = {"pilgrims": int(len(tl)), "mean_specific_flow_p_m_s": float(np.mean(mid)),
                     "peak_30s_specific_flow_p_m_s": float(fw.max()),
                     "pct_of_green_guide": float(100 * fw.max() / GREEN_GUIDE_FLOW)}
# steady-state dip rate: after the first fill of empty slots, until the holding queue clears
_q = np.where(T["n_hold"] > 20)[0]
_t_clear = float(T["t"][_q[-1]]) if len(_q) else float(T["t"][-1])
_t0 = float(T["t"][0]) + DWELL + 150.0
_m = (T["t"] >= _t0) & (T["t"] <= _t_clear)
sustained_dips = (float((T["dips_started"][_m][-1] - T["dips_started"][_m][0]) / (T["t"][_m][-1] - T["t"][_m][0]) * 60)
                  if _m.sum() > 10 else float("nan"))

dm_, ds_ = T["dens_move_max"], T["dens_static_max"]
metrics = {
    "synthetic_layout": True,
    "scenario": {"pilgrims": N_TOTAL, "gates": {g: {"n": counts[g], "rate_per_min": rates[g]} for g in SPLIT},
                 "bridge_width_m": BRIDGE_W, "dwell_s": DWELL, "bathing_slots": N_SLOTS,
                 "ghat_capacity_dips_per_min": GHAT_CAP_PER_MIN},
    "completed": f"{removed_n}/{N_TOTAL}", "simulated_time_s": float(sim.elapsed_time()),
    "wall_time_s": round(time.time() - wall0), "slot_timeouts": int(n_timeout),
    "density": {
        "moving_peak_cell_p_m2": float(dm_.max()),
        "moving_time_above_1.5_s": float((dm_ > LIM_MOVING_OK).sum() * SAMPLE),
        "moving_time_above_2.0_s": float((dm_ > LIM_MOVING_CRIT).sum() * SAMPLE),
        "moving_time_above_4.0_s": float((dm_ > LIM_GREEN_GUIDE).sum() * SAMPLE),
        "static_bathing_peak_cell_p_m2": float(ds_.max()),
        "static_time_above_5_s": float((ds_ > LIM_STATIC_HIGH).sum() * SAMPLE),
        "static_time_above_6_s": float((ds_ > LIM_STATIC_RISK).sum() * SAMPLE),
        "strip_avg_peak_p_m2": float(T["dens_strip_avg"].max()),
        "plaza_moving_avg_peak_p_m2": float(T["dens_plaza_avg"].max()),
    },
    "travel_time_s": {
        "wait_in_holding_before_slot": stats(t_hold_wait), "walk_to_slot": stats(t_to_slot),
        "entry_to_start_of_dip": stats(t_reach_ghat), "exit_after_dip": stats(t_in_exit),
        "total_entry_to_exit": stats(t_total),
        "mean_entry_to_dip_by_gate": {g: float(t_reach_ghat[gates_arr == g].mean()) for g in SPLIT if (gates_arr == g).any()},
    },
    "queue": {
        "max_waiting_in_holding": int(T["n_hold"].max()), "time_of_max_s": float(T["t"][int(np.argmax(T["n_hold"]))]),
        "max_waiting_outside_gates": int(T["outside"].max()),
        "queue_cleared_at_s": float(T["t"][np.where(T["n_hold"] > 20)[0][-1]]) if (T["n_hold"] > 20).any() else 0.0,
        "fraction_agents_that_waited_over_60s": float((t_hold_wait > 60).mean()),
    },
    "bottleneck": {
        "green_guide_flow_p_m_s": GREEN_GUIDE_FLOW,
        "bridges": bridge,
        "ghat_capacity_dips_per_min": GHAT_CAP_PER_MIN,
        "ghat_sustained_dip_starts_per_min": sustained_dips,
        "peak_bathers_at_once": int(T["n_bath"].max()),
    },
}
(out / "metrics.json").write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
print("Outputs:", out)
