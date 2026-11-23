#!/usr/bin/env python3
"""
Prayagraj bottleneck simulations (JuPedSim 1.4.2, Collision-Free Speed Model) with a mixed
Kumbh crowd: singles, rural/urban groups, elderly, children.

usage: python bn_sim.py '<json>'   keys: name, bn (B3|B4|B5|B6), rho0, pop (mixed|adults),
        strip_depth (B5/B6), langar (B4), policy (B6: controlled|free|free_long), seed, max_time

Tags in comments:  [BOOK] Mehrotra & Vera (Prayagraj)   [RAI] Rai, Verma, Chakroborty (Ujjain group study)
                   [STILL] Still thesis   [HARIDWAR] Haridwar paper   [ASSUMED] my choice, not from a source
"""
import json
import math
import pathlib
import random
import sys
import time

import jupedsim as jps
import numpy as np
import shapely

cfg = json.loads(sys.argv[1])
NAME, BN, RHO0 = cfg["name"], cfg["bn"], float(cfg["rho0"])
POP = cfg.get("pop", "mixed")
D = float(cfg.get("strip_depth", 6.0))
LANGAR = bool(cfg.get("langar", True))
POLICY = cfg.get("policy", "controlled")
SEED = int(cfg.get("seed", 5))
MAX_TIME = float(cfg.get("max_time", 4000))
OUT = pathlib.Path(cfg.get("outdir", "bn_runs")) / NAME
OUT.mkdir(parents=True, exist_ok=True)

DT = 0.05
SAMPLE = 1.0  # s
FRAME_EVERY = 2
rng = random.Random(SEED)
nrng = np.random.default_rng(SEED)

# ------------------------------- population parameters ------------------------------
SPEED_MEAN, SPEED_SD = 1.3, 0.25  # m/s  mean [STILL 3.1.3]; SD [ASSUMED]
ELDERLY_FACTOR, CHILD_FACTOR = 0.70, 0.80  # [ASSUMED] speed multipliers
RURAL_GROUP_FACTOR = 1.05  # [ASSUMED] RAI says rural groups walk faster (qualitative only)
R_ADULT, R_CHILD = 0.25, 0.18  # m; adult from 0.5 m body width [STILL 2019/HARIDWAR]; child [ASSUMED]
P_CHILD, P_ELDERLY = 0.08, 0.13  # 21% combined [HARIDWAR text]; split [ASSUMED, unverified]
SHARE_IN_GROUPS = 0.60  # share of people walking in groups [ASSUMED] (RAI cites 70% for non-Indian data)
P_RURAL_GROUP = 0.69  # [RAI: 69% of India is rural; majority of Kumbh pilgrims rural]
AREA_PP = {"rural": 0.60, "urban": 0.57}  # m2/person inside a group [RAI Table 6]
COH_LAG, COH_BOOST, COH_SLOW = 2.0, 1.25, 0.6  # cohesion rule: lag threshold m [ASSUMED], boost, leader slow-down


def group_size(kind):
    if kind == "rural":  # [RAI Table 3] 4-6: 30%, 7-9: 34%, >9: 36% (4-13 observed)
        r = rng.random()
        return rng.randint(4, 6) if r < 0.30 else rng.randint(7, 9) if r < 0.64 else rng.randint(10, 13)
    return rng.choices([4, 5, 6, 7, 8], [22, 31, 25, 11, 11])[0]  # [RAI Table 3 non-rural]


MEAN_GROUP = 7.0  # approx, for the unit mix below
PG = SHARE_IN_GROUPS / (MEAN_GROUP * (1 - SHARE_IN_GROUPS) + SHARE_IN_GROUPS)


def sample_person(kind_group):
    """kind_group: None (single), 'rural', 'urban'."""
    r = rng.random()
    if kind_group is None:
        t = "elderly" if r < P_ELDERLY / (1 - P_CHILD) else "adult"  # no unaccompanied children
    else:
        t = "child" if r < P_CHILD else "elderly" if r < P_CHILD + P_ELDERLY else "adult"
    v = min(1.8, max(0.6, rng.gauss(SPEED_MEAN, SPEED_SD)))
    if t == "elderly":
        v *= ELDERLY_FACTOR
    if t == "child":
        v *= CHILD_FACTOR
    if kind_group == "rural":
        v *= RURAL_GROUP_FACTOR
    return {"type": t, "v": v, "r": R_CHILD if t == "child" else R_ADULT}


def person_class(p, kind):
    if p["type"] == "child":
        return 2
    if p["type"] == "elderly":
        return 1
    return 0 if kind is None else (3 if kind == "rural" else 4)


def make_units(n):
    units, total = [], 0
    while total < n:
        if POP == "adults":
            p = {"type": "adult", "v": min(1.8, max(0.6, rng.gauss(SPEED_MEAN, SPEED_SD))), "r": R_ADULT}
            units.append({"kind": None, "members": [p]})
            total += 1
            continue
        if rng.random() < PG:
            kind = "rural" if rng.random() < P_RURAL_GROUP else "urban"
            k = min(group_size(kind), n - total) if n - total >= 2 else 1
            ms = [sample_person(kind) for _ in range(k)]
            if k > 1 and all(m["type"] != "adult" for m in ms):
                ms[0] = {"type": "adult", "v": ms[0]["v"] / (ELDERLY_FACTOR if ms[0]["type"] == "elderly" else CHILD_FACTOR), "r": R_ADULT}
            units.append({"kind": kind if k > 1 else None, "members": ms})
            total += k
        else:
            units.append({"kind": None, "members": [sample_person(None)]})
            total += 1
    for u in units:  # cohesion: whole group walks at its slowest member's speed [RAI: groups stay together]
        if len(u["members"]) > 1:
            vg = min(m["v"] for m in u["members"])
            for m in u["members"]:
                m["v"] = vg
    return units


# ------------------------------- geometry ---------------------------------------------
def box(x0, y0, x1, y1):
    return shapely.box(x0, y0, x1, y1)


STATIC = []  # (region, density) of static queuers
ZONES, LINES = {}, {}
HAS_SLOTS = BN in ("B5", "B6")
if BN == "B3":  # width cascade: 50 m route -> 10 m bridge -> 3 m alley [BOOK widths]; lengths [ASSUMED]
    L1, W1, LB, WB, LA, WA = 20.0, 50.0, 40.0, 10.0, 30.0, 3.0
    parts = [box(0, -W1 / 2, L1, W1 / 2), box(L1, -WB / 2, L1 + LB, WB / 2), box(L1 + LB, -WA / 2, L1 + LB + LA, WA / 2)]
    XE = L1 + LB + LA
    EXITS = [[(XE - 1, -WA / 2), (XE - 1, WA / 2), (XE, WA / 2), (XE, -WA / 2)]]
    START = (0.8, L1 - 0.8, -W1 / 2 + 0.8, W1 / 2 - 0.8)
    ZONES = {"feeder": (0, L1, -W1 / 2, W1 / 2), "bridge": (L1, L1 + LB, -WB / 2, WB / 2), "alley": (L1 + LB, XE, -WA / 2, WA / 2)}
    LINES = {"bridge_in": ("x", L1, WB), "alley_in": ("x", L1 + LB, WA)}
elif BN == "B4":  # Akhara thoroughfare: 50 m wide road [BOOK >50 m]; length, langar zone [ASSUMED]
    LEN, W = 120.0, 50.0
    parts = [box(0, -W / 2, LEN, W / 2)]
    EXITS = [[(LEN - 1, -W / 2), (LEN - 1, W / 2), (LEN, W / 2), (LEN, -W / 2)]]
    START = (0.8, 15.0, -W / 2 + 0.8, W / 2 - 0.8)
    ZONES = {"start": (0, 20, -W / 2, W / 2), "langar_reach": (55, 85, -W / 2, W / 2)}
    LINES = {"x40": ("x", 40, W), "x100": ("x", 100, W)}
    if LANGAR:
        STATIC.append(((60.0, 80.0, -W / 2 + 0.8, -W / 2 + 6.8), 3.0))  # langar queue 20x6 m at 3 p/m2 [ASSUMED]
else:  # B5/B6: shoreline front, barricade strip depth D in 2-10 m [BOOK]; frontage 60 m [ASSUMED]
    F, XS = 60.0, 57.0
    parts = [box(0, -F / 2, XS, F / 2), box(XS, -F / 2, XS + D, F / 2),
             box(XS - 6, F / 2, XS, F / 2 + 20), box(XS - 6, -F / 2 - 20, XS, -F / 2)]  # 6 m exit passages [ASSUMED]
    EXITS = [[(XS - 5, F / 2 + 19), (XS - 1, F / 2 + 19), (XS - 1, F / 2 + 20), (XS - 5, F / 2 + 20)],
             [(XS - 5, -F / 2 - 20), (XS - 1, -F / 2 - 20), (XS - 1, -F / 2 - 19), (XS - 5, -F / 2 - 19)]]
    START = (40.0, XS - 1.0, -F / 2 + 0.8, F / 2 - 0.8)
    ZONES = {"staging": (0, XS, -F / 2, F / 2), "strip": (XS, XS + D, -F / 2, F / 2)}
walkable = shapely.unary_union(parts)
assert walkable.is_valid and walkable.geom_type == "Polygon"

jps.set_warning_callback(lambda m: None)
jps.set_error_callback(print)
sim = jps.Simulation(model=jps.CollisionFreeSpeedModel(), geometry=walkable, dt=DT)
exit_stages = [sim.add_exit_stage(e) for e in EXITS]
exit_journeys = [sim.add_journey(jps.JourneyDescription([s])) for s in exit_stages]


def hex_sites(region, rho):
    s = math.sqrt(2 / (math.sqrt(3) * rho))
    x0, x1, y0, y1 = region
    pts, y, row = [], y0, 0
    while y <= y1:
        x = x0 + (0 if row % 2 == 0 else s / 2)
        while x <= x1:
            pts.append((x, y)); x += s
        y += s * math.sqrt(3) / 2; row += 1
    return np.array(pts), s


def place_units(units, sites, s):
    """Assign units to hex-lattice sites; groups take the nearest free sites (compact), compressed to
    the group spacing (RAI area per person) when the lattice is looser than that."""
    free = np.ones(len(sites), bool)
    out, out_pts = [], []
    for u in units:
        idx = np.flatnonzero(free)
        n = len(u["members"])
        if len(idx) < n:
            n = len(idx); u["members"] = u["members"][:n]
            if n == 0:
                break
        seed = int(nrng.choice(idx))
        if n == 1:
            ch = np.array([seed])
        else:
            d = np.hypot(sites[idx, 0] - sites[seed, 0], sites[idx, 1] - sites[seed, 1])
            ch = idx[np.argsort(d)[:n]]
        free[ch] = False
        pts = sites[ch].copy()
        if n > 1:
            dg = math.sqrt(AREA_PP[u["kind"]])
            c = pts.mean(0)
            cand = c + (pts - c) * min(1.0, dg / s)
            others = np.vstack(out_pts) if out_pts else np.empty((0, 2))
            if len(others):
                # clearance of compressed group against everyone already placed (and itself)
                dmin = np.min(np.hypot(cand[:, None, 0] - others[None, :, 0], cand[:, None, 1] - others[None, :, 1]))
            else:
                dmin = 9.9
            if dmin >= 0.6:
                pts = cand
        pts = pts + nrng.normal(0, 0.015, pts.shape)
        out.append(pts)
        out_pts.append(pts)
    return out


# ------------------------------- agents -------------------------------------------------
A = {}  # id -> dict
GROUPS = {}  # gid -> list of ids
failed_place = 0
gid_counter = 0

units = make_units(10 ** 6) if False else None
sites, s_lat = hex_sites(START, RHO0)
units = make_units(len(sites))
placed = place_units(units, sites, s_lat)

# static queuers (B4 langar)
static_ids = []
static_stage_ids = []
for region, rho in STATIC:
    ss, s2 = hex_sites(region, rho)
    su = make_units(len(ss))
    sp = place_units(su, ss, s2)
    for u, pts in zip(su, sp):
        for m, p in zip(u["members"], pts):
            st = sim.add_waypoint_stage((float(p[0]), float(p[1])), 0.4)
            jr = sim.add_journey(jps.JourneyDescription([st]))
            try:
                aid = sim.add_agent(jps.CollisionFreeSpeedModelAgentParameters(
                    journey_id=jr, stage_id=st, position=(float(p[0]), float(p[1])), desired_speed=1.0, radius=m["r"]))
            except RuntimeError:
                continue
            A[aid] = dict(cls=person_class(m, u["kind"]), state="static", gid=None, v=m["v"])
            static_ids.append(aid)

# slots / holding (B5, B6)
if HAS_SLOTS:
    SLOT_SP, COLS, AISLE, ROWG = 0.7, int((D - 0.6) / 0.7) + 1, 1.7, 3
    xs_ = [XS + D - 0.6 - SLOT_SP * k for k in range(COLS) if XS + D - 0.6 - SLOT_SP * k >= XS + 0.4]
    ys_, yy = [], -F / 2 + 0.6
    while yy + (ROWG - 1) * SLOT_SP <= F / 2 - 0.6:
        ys_ += [yy + k * SLOT_SP for k in range(ROWG)]
        yy += (ROWG - 1) * SLOT_SP + AISLE
    slot_xy = np.array([(x, y) for x in xs_ for y in ys_])
    NS = len(slot_xy)
    slot_stage = [sim.add_waypoint_stage((float(x), float(y)), 0.3) for x, y in slot_xy]
    slot_journey = [sim.add_journey(jps.JourneyDescription([st])) for st in slot_stage]
    free_slot = np.ones(NS, bool)
    hold_y = np.arange(-F / 2 + 4, F / 2 - 3, 4.0)
    HOLD_X = XS - 9.0
    hold_stage = [sim.add_waypoint_stage((HOLD_X, float(y)), 2.0) for y in hold_y]
    hold_journey = [sim.add_journey(jps.JourneyDescription([st])) for st in hold_stage]
    CAP_PER_MIN = NS / 300.0 * 60.0

    def pick_slot(ax, ay, among=None):
        idx = np.flatnonzero(free_slot) if among is None else among
        if len(idx) == 0:
            return None
        cost = (XS + D - slot_xy[idx, 0]) + 0.3 * np.abs(slot_xy[idx, 1] - ay)
        return int(idx[np.argmin(cost)])

    def dwell_for():
        if POLICY == "controlled":
            return 300.0  # police extraction at the 5-min average [HARIDWAR dip time; BOOK: police remove people from river]
        cv = 0.8 if POLICY == "free" else 1.5  # [ASSUMED] uncontrolled dips, lognormal with mean 300 s
        sg = math.sqrt(math.log(1 + cv * cv)); mu = math.log(300.0) - sg * sg / 2
        return float(min(2400.0, rng.lognormvariate(mu, sg)))
else:
    CAP_PER_MIN = None

units_runtime = []  # list of dicts: ids, centroid, state
walker_ids = []
for u, pts in zip(units, placed):
    ids = []
    gid = None
    if len(u["members"]) > 1:
        gid = gid_counter; gid_counter += 1
    for m, p in zip(u["members"], pts):
        if HAS_SLOTS:
            jid, sid = hold_journey[0], hold_stage[0]  # real target set below
        else:
            jid, sid = exit_journeys[0], exit_stages[0]
        try:
            aid = sim.add_agent(jps.CollisionFreeSpeedModelAgentParameters(
                journey_id=jid, stage_id=sid, position=(float(p[0]), float(p[1])),
                desired_speed=m["v"], radius=m["r"]))
        except RuntimeError:
            failed_place += 1
            if failed_place <= 3: print("   placement error:", sys.exc_info()[1], flush=True)
            continue
        A[aid] = dict(cls=person_class(m, u["kind"]), state="walk", gid=gid, v=m["v"], r=m["r"], t_exit=None,
                      slot=None, t_assign=None, t_bath=None, dwell=None, crossed=set(), x0=float(p[0]), t_ready=None)
        ids.append(aid); walker_ids.append(aid)
    if ids:
        units_runtime.append({"ids": ids, "gid": gid})
        if gid is not None:
            GROUPS[gid] = ids
N_WALK = len(walker_ids)
print(f"{NAME}: {N_WALK} walkers (+{len(static_ids)} static), failed placements {failed_place}, "
      f"groups {len(GROUPS)}, lattice {s_lat:.2f} m", flush=True)


def slot_assign_unit(u, pos):
    """Give a whole unit (group or single) free slots, compact around a seed slot; returns True if done."""
    ids = u["ids"]
    k = len(ids)
    if int(free_slot.sum()) < k:
        return False
    cx = float(np.mean([pos[i][0] for i in ids])); cy = float(np.mean([pos[i][1] for i in ids]))
    seed = pick_slot(cx, cy)
    fidx = np.flatnonzero(free_slot)
    d = np.hypot(slot_xy[fidx, 0] - slot_xy[seed, 0], slot_xy[fidx, 1] - slot_xy[seed, 1])
    chosen = fidx[np.argsort(d)[:k]]
    order = sorted(ids, key=lambda i: pos[i][1])
    chosen = sorted(chosen, key=lambda sidx: slot_xy[sidx][1])
    for i, sl in zip(order, chosen):
        free_slot[sl] = False
        a = A[i]; a["slot"] = int(sl); a["state"] = "toslot"; a["t_assign"] = None
        sim.switch_agent_journey(i, slot_journey[sl], slot_stage[sl])
    return True


def send_to_hold(u, pos):
    for i in u["ids"]:
        k = int(np.argmin(np.abs(hold_y - pos[i][1])))
        A[i]["state"] = "hold"
        sim.switch_agent_journey(i, hold_journey[k], hold_stage[k])


# ------------------------------- density grid -----------------------------------------------
CELL = 2.0
bx0, by0, bx1, by1 = walkable.bounds
XE_ = np.arange(math.floor(bx0), bx1 + CELL, CELL)
YE_ = np.arange(math.floor(by0), by1 + CELL, CELL)
cell_area = np.zeros((len(XE_) - 1, len(YE_) - 1))
for i in range(len(XE_) - 1):
    for j in range(len(YE_) - 1):
        cell_area[i, j] = walkable.intersection(box(XE_[i], YE_[j], XE_[i + 1], YE_[j + 1])).area
valid = cell_area >= 0.5 * CELL * CELL
peak_move = np.zeros_like(cell_area)
peak_static = np.zeros_like(cell_area)


def inbox(xy, b):
    return (xy[:, 0] >= b[0]) & (xy[:, 0] < b[1]) & (xy[:, 1] >= b[2]) & (xy[:, 1] < b[3])


zone_area = {k: walkable.intersection(box(b[0], b[2], b[1], b[3])).area for k, b in ZONES.items()}

# ------------------------------- initial slot assignment ------------------------------------
if HAS_SLOTS:
    pos0 = {aid: sim.agent(aid).position for aid in walker_ids}
    for u in sorted(units_runtime, key=lambda u: -np.mean([pos0[i][0] for i in u["ids"]])):
        if not slot_assign_unit(u, pos0):
            send_to_hold(u, pos0)
    for u in units_runtime:
        u["state"] = "assigned"

# ------------------------------- run -----------------------------------------------------------
keys = ["t", "n_walk", "n_hold", "n_bath", "n_exit", "dens_move_max", "dens_static_max", "slow_n", "cum_out", "dips_started"] + \
       [f"dens_{z}" for z in ZONES] + [f"cum_{l}" for l in LINES]
ts = {k: [] for k in keys}
fr_t, fr_n, fr_xy, fr_cls, fr_st = [], [], [], [], []
cross_t = {l: [] for l in LINES}
prev = {}
removed = 0
timeouts = 0
sample_k = 0
next_sample = 0.0
wall0 = time.time()
STATE_ID = {"walk": 0, "hold": 1, "toslot": 0, "bath": 2, "exit": 3, "static": 4}

while sim.elapsed_time() < MAX_TIME:
    sim.iterate()
    t = sim.elapsed_time()
    for aid in sim.removed_agents():
        a = A.get(aid)
        if a is not None and a["state"] != "static" and a["t_exit"] is None:
            a["t_exit"] = t; a["state"] = "done"; removed += 1
    if t < next_sample:
        continue
    next_sample += SAMPLE
    sample_k += 1
    ags = list(sim.agents())
    pos = {a.id: a.position for a in ags}

    if HAS_SLOTS:
        # arrivals / dwell / release
        for aid, p in pos.items():
            s = A.get(aid)
            if s is None:
                continue
            if s["state"] == "toslot":
                if s["t_assign"] is None:
                    s["t_assign"] = t
                sx, sy = slot_xy[s["slot"]]
                near = math.hypot(p[0] - sx, p[1] - sy) < 0.9
                if near or t - s["t_assign"] > 400.0:
                    s["state"] = "bath"; s["t_bath"] = t; s["dwell"] = dwell_for()
                    timeouts += (not near)
        # group-level release: a unit leaves once every member has finished its dip
        for u in units_runtime:
            ids = [i for i in u["ids"] if A[i]["state"] != "done"]
            if not ids or any(A[i]["state"] not in ("bath", "exit") for i in ids):
                continue
            bathing = [i for i in ids if A[i]["state"] == "bath"]
            if bathing and all(t - A[i]["t_bath"] >= A[i]["dwell"] for i in bathing):
                for i in bathing:
                    A[i]["state"] = "exit"; A[i]["t_ready"] = t
                    free_slot[A[i]["slot"]] = True
                    j = 0 if pos[i][1] >= 0 else 1
                    sim.switch_agent_journey(i, exit_journeys[j], exit_stages[j])
        # release holding units to free slots (closest to the strip first, FIFO by position)
        if free_slot.any():
            holders = [u for u in units_runtime if all(A[i]["state"] in ("hold",) for i in u["ids"] if i in pos and A[i]["state"] != "done")
                       and any(A[i]["state"] == "hold" for i in u["ids"])]
            holders.sort(key=lambda u: -np.mean([pos[i][0] for i in u["ids"] if i in pos]))
            for u in holders:
                u2 = {"ids": [i for i in u["ids"] if i in pos]}
                if not slot_assign_unit(u2, pos):
                    break

    # group cohesion: followers catch up, leader waits [RAI: cohesion maintained irrespective of size]
    for gid, ids in GROUPS.items():
        alive = [i for i in ids if i in pos and A[i]["state"] in ("walk", "toslot", "hold")]
        if len(alive) < 2:
            continue
        xs_m = [pos[i][0] for i in alive]
        lead = alive[int(np.argmax(xs_m))]; xmax = max(xs_m)
        vg = A[alive[0]]["v"]
        for i, x in zip(alive, xs_m):
            lag = xmax - x
            if i == lead:
                new = vg * (COH_SLOW if lag > 0 and max(xmax - xx for xx in xs_m) > COH_LAG else 1.0)
            else:
                new = vg * (COH_BOOST if lag > COH_LAG else 1.0)
            sim.agent(i).model.desired_speed = new

    # crossings
    for aid, p in pos.items():
        q = prev.get(aid)
        s = A.get(aid)
        if q is None or s is None or s["state"] == "static":
            continue
        for ln, (ax, c, w) in LINES.items():
            ii = 0 if ax == "x" else 1
            if ln not in s["crossed"] and q[ii] < c <= p[ii]:
                s["crossed"].add(ln); cross_t[ln].append(t)
    # speed estimate
    ids = list(pos.keys())
    xy = np.array([pos[i] for i in ids]).reshape(-1, 2)
    spd = np.array([math.hypot(pos[i][0] - prev[i][0], pos[i][1] - prev[i][1]) / SAMPLE if i in prev else 9.9 for i in ids])
    prev = pos
    stt = np.array([STATE_ID.get(A[i]["state"], 0) if i in A else 0 for i in ids], dtype=np.uint8)
    cls = np.array([A[i]["cls"] if i in A else 0 for i in ids], dtype=np.uint8)
    static_m = stt == 4
    bath_m = stt == 2
    stat_all = static_m | bath_m
    for arr_mask, tag in ((~stat_all, "m"), (stat_all, "s")):
        sub = xy[arr_mask]
        H = np.histogram2d(sub[:, 0], sub[:, 1], bins=[XE_, YE_])[0] if len(sub) else np.zeros_like(cell_area)
        dd = np.where(valid, H / np.maximum(cell_area, 1e-9), 0.0)
        if tag == "m":
            dm = dd; peak_move = np.maximum(peak_move, dd)
        else:
            ds = dd; peak_static = np.maximum(peak_static, dd)
    mv = ~stat_all
    ts["t"].append(t)
    ts["n_walk"].append(int(((stt == 0) & mv).sum())); ts["n_hold"].append(int((stt == 1).sum()))
    ts["n_bath"].append(int(bath_m.sum())); ts["n_exit"].append(int((stt == 3).sum()))
    ts["dens_move_max"].append(float(dm.max())); ts["dens_static_max"].append(float(ds.max()))
    ts["slow_n"].append(int(((spd < 0.25) & mv).sum()))
    ts["cum_out"].append(removed)
    ts["dips_started"].append(sum(1 for a in A.values() if a.get("t_bath") is not None) if HAS_SLOTS else 0)
    for z, b in ZONES.items():
        ts[f"dens_{z}"].append(float((inbox(xy, b) & mv).sum() / max(zone_area[z], 1e-9)) if len(xy) else 0.0)
    for ln in LINES:
        ts[f"cum_{ln}"].append(len(cross_t[ln]))
    if sample_k % FRAME_EVERY == 0:
        fr_t.append(t); fr_n.append(len(ids)); fr_xy.append(xy.astype(np.float32)); fr_cls.append(cls); fr_st.append(stt)
    if int(t) % 100 == 0 and abs(t - round(t)) < SAMPLE:
        print(f"  t={t:6.0f}s exited={removed}/{N_WALK} walk={ts['n_walk'][-1]} hold={ts['n_hold'][-1]} bath={ts['n_bath'][-1]} "
              f"movmax={dm.max():.2f} wall={time.time()-wall0:.0f}s", flush=True)
    if removed >= N_WALK - 0:
        break

# ------------------------------- metrics -------------------------------------------------------
T = {k: np.array(v, dtype=float) for k, v in ts.items()}
CLS_NAME = {0: "adult (single)", 1: "elderly", 2: "child (with group)", 3: "adult in rural group", 4: "adult in urban group"}
done = [i for i in walker_ids if A[i]["t_exit"] is not None]


def stats(x):
    x = np.asarray(x, float)
    return {} if len(x) == 0 else {"n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)),
                                   "p95": float(np.percentile(x, 95)), "max": float(x.max())}


tt_all = [A[i]["t_exit"] for i in done]
by_cls = {CLS_NAME[c]: stats([A[i]["t_exit"] for i in done if A[i]["cls"] == c]) for c in range(5)}
by_cls = {k: v for k, v in by_cls.items() if v}
comp = {CLS_NAME[c]: int(sum(1 for i in walker_ids if A[i]["cls"] == c)) for c in range(5)}
gsizes = [len(v) for v in GROUPS.values()]
dm_, ds_ = T["dens_move_max"], T["dens_static_max"]
M = {
    "name": NAME, "bottleneck": BN, "rho0": RHO0, "population": POP, "config": cfg,
    "walkers": N_WALK, "static_queuers": len(static_ids), "placement_failures": failed_place,
    "completed": f"{removed}/{N_WALK}", "simulated_time_s": float(sim.elapsed_time()), "wall_s": round(time.time() - wall0),
    "composition": comp, "n_groups": len(GROUPS), "group_sizes": {"mean": float(np.mean(gsizes)) if gsizes else 0, "max": max(gsizes) if gsizes else 0},
    "share_in_groups": float(sum(gsizes) / max(N_WALK, 1)),
    "travel_time_s": stats(tt_all), "travel_time_by_class_s": by_cls,
    "density": {"moving_peak_cell": float(dm_.max()), "moving_s_above_1.5": float((dm_ > 1.5).sum() * SAMPLE),
                "moving_s_above_2.0": float((dm_ > 2.0).sum() * SAMPLE), "moving_s_above_4.0": float((dm_ > 4.0).sum() * SAMPLE),
                "static_peak_cell": float(ds_.max()), "static_s_above_5": float((ds_ > 5).sum() * SAMPLE),
                "static_s_above_6": float((ds_ > 6).sum() * SAMPLE)},
    "queue": {"max_slow_agents": int(T["slow_n"].max()), "max_holding": int(T["n_hold"].max()),
              "time_of_max_holding_s": float(T["t"][int(np.argmax(T["n_hold"]))])},
}
M["zone_density_peak"] = {z: float(T[f"dens_{z}"].max()) for z in ZONES}
# line flows
win = 30.0
flows = {}
for ln, (ax, c, w) in LINES.items():
    tl = np.array(sorted(cross_t[ln]))
    if len(tl) > 5:
        e = np.arange(0, tl.max() + win, win)
        cnt = np.histogram(tl, bins=e)[0]
        f = cnt / win / w
        sus = f[f >= 0.8 * f.max()]
        flows[ln] = {"width_m": w, "n": int(len(tl)), "peak_30s_specific_flow": float(f.max()), "sustained_specific_flow": float(sus.mean()),
                     "first_s": float(tl.min()), "last_s": float(tl.max())}
M["flows_p_m_s"] = flows
if HAS_SLOTS:
    tb = [A[i]["t_bath"] for i in walker_ids if A[i]["t_bath"] is not None]
    wait_slot = [A[i]["t_bath"] - 0.0 for i in walker_ids if A[i]["t_bath"] is not None]
    dwell_all = [A[i]["dwell"] for i in walker_ids if A[i]["dwell"] is not None]
    q = np.where(T["n_hold"] > 20)[0]
    t_clear = float(T["t"][q[-1]]) if len(q) else 0.0
    mdl = (T["t"] >= 450) & (T["t"] <= max(t_clear, 460))
    dips = T["dips_started"]
    rate = float((dips[mdl][-1] - dips[mdl][0]) / (T["t"][mdl][-1] - T["t"][mdl][0]) * 60) if mdl.sum() > 10 else float("nan")
    M["ghat"] = {"slots": int(NS), "strip_depth_m": D, "columns": int(len(xs_)), "capacity_dips_per_min_at_300s": CAP_PER_MIN,
                 "sustained_dip_starts_per_min": rate, "queue_cleared_at_s": t_clear, "slot_timeouts": int(timeouts),
                 "time_to_start_dip_s": stats(wait_slot), "dwell_s": stats(dwell_all), "policy": POLICY if BN == "B6" else "n/a",
                 "peak_bathers": int(T["n_bath"].max()),
                 "time_to_start_dip_by_class_s": {CLS_NAME[c]: stats([A[i]["t_bath"] for i in walker_ids if A[i]["cls"] == c and A[i]["t_bath"] is not None])
                                                 for c in range(5) if any(A[i]["cls"] == c and A[i]["t_bath"] is not None for i in walker_ids)}}
(OUT / "metrics.json").write_text(json.dumps(M, indent=2))
np.savetxt(OUT / "timeseries.csv", np.column_stack([T[k] for k in keys]), delimiter=",", header=",".join(keys), comments="")
np.savez_compressed(OUT / "peakmaps.npz", XE=XE_, YE=YE_, valid=valid, move=peak_move, static=peak_static,
                    boundary=np.array(list(walkable.exterior.coords)))
np.savez_compressed(OUT / "frames.npz", t=np.array(fr_t), n=np.array(fr_n), xy=np.concatenate(fr_xy), cls=np.concatenate(fr_cls),
                    st=np.concatenate(fr_st), boundary=np.array(list(walkable.exterior.coords)))
np.savez_compressed(OUT / "agents.npz", cls=np.array([A[i]["cls"] for i in done]), t_exit=np.array([A[i]["t_exit"] for i in done]),
                    x0=np.array([A[i]["x0"] for i in done]),
                    t_bath=np.array([A[i]["t_bath"] if A[i]["t_bath"] is not None else np.nan for i in done]) if HAS_SLOTS else np.array([]),
                    dwell=np.array([A[i]["dwell"] if A[i]["dwell"] is not None else np.nan for i in done]) if HAS_SLOTS else np.array([]))
print(f"{NAME}: DONE {removed}/{N_WALK} in {sim.elapsed_time():.0f}s sim, {time.time()-wall0:.0f}s wall", flush=True)
