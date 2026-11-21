#!/usr/bin/env python3
"""
SYNTHETIC demo: one Kumbh-style sector, simulated with JuPedSim.

!! Every number below marked ASSUMPTION is a placeholder, NOT measured data.
!! Replace them with real values (see the ASSUMPTIONS block) before drawing
!! any conclusion about a real sector.

Workflow:
  1. Geometry   - approach road -> ghat plaza -> pontoon bridge -> exit
  2. Stages     - waypoints and exit
  3. Journey    - approach -> plaza -> bridge -> exit
  4. Demand     - agents released over time (inflow profile)
  5. Simulate   - Collision-Free Speed Model
  6. Measure    - density in plaza, flow over the bridge, travel time
  7. Plot       - density-over-time + final snapshot
"""
import pathlib
import random

import jupedsim as jps
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shapely
from matplotlib.patches import Polygon as MplPolygon

# ----------------------------------------------------------------------------
# ASSUMPTIONS (all synthetic) -------------------------------------------------
# ----------------------------------------------------------------------------
SEED = 42
DT = 0.05  # s, time step
SIM_TIME = 900.0  # s simulated (15 min)

APPROACH_W = 12.0  # m, approach road width            ASSUMPTION
APPROACH_L = 50.0  # m                                  ASSUMPTION
PLAZA_W, PLAZA_L = 40.0, 30.0  # m, ghat holding plaza  ASSUMPTION
BRIDGE_W = 6.0  # m, pontoon bridge width (the bottleneck) ASSUMPTION
BRIDGE_L = 40.0  # m                                    ASSUMPTION

import sys
INFLOW_PER_MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 120  # persons/min  ASSUMPTION (CLI override)
INFLOW_DURATION = 480.0  # s of continuous inflow         ASSUMPTION
SPEED_MEAN, SPEED_SD = 1.1, 0.25  # m/s free speed       ASSUMPTION (slow: luggage/elderly)
RADIUS_MEAN, RADIUS_SD = 0.22, 0.03  # m body radius      ASSUMPTION
DWELL_TIME = 0.0  # s waiting at ghat (0 = skip; see note in README)

# ----------------------------------------------------------------------------
# 1. GEOMETRY -----------------------------------------------------------------
# Layout (x to the right), one simple polygon (JuPedSim regions have no holes):
#   approach road -> plaza (wider) -> bridge (narrow) -> exit
# ----------------------------------------------------------------------------
x0 = 0.0
x1 = x0 + APPROACH_L  # end of approach / start of plaza
x2 = x1 + PLAZA_L  # end of plaza / start of bridge
x3 = x2 + BRIDGE_L  # end of bridge (exit)
ya = APPROACH_W / 2
yp = PLAZA_W / 2
yb = BRIDGE_W / 2

boundary = [
    (x0, -ya), (x1, -ya), (x1, -yp), (x2, -yp), (x2, -yb), (x3, -yb),
    (x3, yb), (x2, yb), (x2, yp), (x1, yp), (x1, ya), (x0, ya),
]
walkable = shapely.Polygon(boundary)
assert walkable.is_valid, "geometry polygon is invalid"

# ----------------------------------------------------------------------------
# 2-3. SURFACE, STAGES, JOURNEY ----------------------------------------------
# ----------------------------------------------------------------------------
jps.set_warning_callback(print)
jps.set_error_callback(print)

out_dir = pathlib.Path(__file__).parent / f"out_{INFLOW_PER_MIN}pmin"
out_dir.mkdir(exist_ok=True)

sim = jps.Simulation(
    model=jps.CollisionFreeSpeedModel(),
    geometry=walkable,
    dt=DT,
    trajectory_writer=jps.SqliteTrajectoryWriter(
        output_file=out_dir / "sector.sqlite"
    ),
)

# One exit stage at the end of the bridge. No intermediate waypoints: the
# routing engine already steers agents through the bridge, and waypoints inside
# a crowded plaza make agents pile up around them (deadlock, found the hard way).
exit_stage = sim.add_exit_stage(
    [(x3 - 1, -yb), (x3 - 1, yb), (x3, yb), (x3, -yb)]
)
journey = jps.JourneyDescription([exit_stage])
journey_id = sim.add_journey(journey)

# ----------------------------------------------------------------------------
# 4. DEMAND: release agents at the entrance over time -------------------------
# ----------------------------------------------------------------------------
rng = random.Random(SEED)
release_interval = 60.0 / INFLOW_PER_MIN  # s between agents
spawn_zone = shapely.box(x0 + 0.5, -ya + 0.5, x0 + 4.0, ya - 0.5)
entry_time: dict[int, float] = {}
next_release = 0.0
spawn_fail = 0


def try_spawn():
    """Spawn one agent at a free spot in the entry zone."""
    global spawn_fail
    for _ in range(30):
        x = rng.uniform(0.5, 4.0)
        y = rng.uniform(-ya + 0.5, ya - 0.5)
        # skip if too close to an existing agent
        if any(True for _ in sim.agents_in_range((x, y), 0.6)):
            continue
        v0 = max(0.4, rng.gauss(SPEED_MEAN, SPEED_SD))
        r = min(0.35, max(0.15, rng.gauss(RADIUS_MEAN, RADIUS_SD)))
        aid = sim.add_agent(
            jps.CollisionFreeSpeedModelAgentParameters(
                journey_id=journey_id,
                stage_id=exit_stage,
                position=(x, y),
                desired_speed=v0,
                radius=r,
            )
        )
        entry_time[aid] = sim.elapsed_time()
        return True
    spawn_fail += 1  # entrance saturated: queue spills back outside sector
    return False


# ----------------------------------------------------------------------------
# 5-6. SIMULATE + MEASURE ------------------------------------------------------
# ----------------------------------------------------------------------------
plaza_poly = shapely.box(x1, -yp, x2, yp)
plaza_area = plaza_poly.area
bridge_zone = shapely.box(x2, -yb, x3, yb)
bridge_area = bridge_zone.area

times, plaza_density, bridge_density, in_sector = [], [], [], []
travel_times: list[float] = []
exited_times: list[float] = []

steps = int(SIM_TIME / DT)
sample_every = int(5.0 / DT)  # sample every 5 s
for step in range(steps):
    t = sim.elapsed_time()
    while next_release <= t < INFLOW_DURATION:
        try_spawn()
        next_release += release_interval

    sim.iterate()

    for aid in sim.removed_agents():
        if aid in entry_time:
            travel_times.append(sim.elapsed_time() - entry_time[aid])
            exited_times.append(sim.elapsed_time())

    if step % sample_every == 0:
        ags = list(sim.agents())
        n_plaza = sum(
            1 for a in ags if plaza_poly.contains(shapely.Point(a.position))
        )
        n_bridge = sum(
            1 for a in ags if bridge_zone.contains(shapely.Point(a.position))
        )
        times.append(sim.elapsed_time())
        plaza_density.append(n_plaza / plaza_area)
        bridge_density.append(n_bridge / bridge_area)
        in_sector.append(len(ags))

    if t > INFLOW_DURATION and sim.agent_count() == 0:
        break


# ----------------------------------------------------------------------------
# REPORT ----------------------------------------------------------------------
# ----------------------------------------------------------------------------
print("\n=== RESULTS (SYNTHETIC INPUTS - NOT REAL DATA) ===")
print(f"Agents released        : {len(entry_time)} (entrance-saturated skips: {spawn_fail})")
print(f"Agents exited          : {len(travel_times)}")
if travel_times:
    print(
        f"Travel time (s)        : mean {np.mean(travel_times):.0f}, "
        f"p95 {np.percentile(travel_times, 95):.0f}, max {np.max(travel_times):.0f}"
    )
print(f"Peak plaza density     : {max(plaza_density):.2f} p/m2")
print(f"Peak bridge density    : {max(bridge_density):.2f} p/m2")
if len(exited_times) > 10:
    span = exited_times[-1] - exited_times[0]
    flow = (len(exited_times) - 1) / span / BRIDGE_W
    print(f"Bridge specific flow   : {flow:.2f} p/(m*s)  (typical capacity ~1.2-1.9)")
print(f"Outputs in             : {out_dir}")

# ----------------------------------------------------------------------------
# 7. PLOTS --------------------------------------------------------------------
# ----------------------------------------------------------------------------
fig, ax = plt.subplots(2, 1, figsize=(10, 9))

ax[0].plot(times, plaza_density, label="plaza")
ax[0].plot(times, bridge_density, label="bridge")
ax[0].axhline(4, color="orange", ls="--", lw=1, label="4 p/m2 warning")
ax[0].axhline(6, color="red", ls="--", lw=1, label="6 p/m2 critical")
ax[0].set_xlabel("time [s]")
ax[0].set_ylabel("density [p/m2]")
ax[0].set_title("Density over time (synthetic inputs)")
ax[0].legend()

ax[1].add_patch(
    MplPolygon(boundary, closed=True, fc="#eeeeee", ec="k")
)
snap = list(sim.agents())
if snap:
    ax[1].scatter(
        [a.position[0] for a in snap], [a.position[1] for a in snap], s=6
    )
ax[1].set_xlim(x0 - 2, x3 + 2)
ax[1].set_ylim(-yp - 2, yp + 2)
ax[1].set_aspect("equal")
ax[1].set_title("Geometry (end-of-run agents shown, if any remain)")

plt.tight_layout()
fig.savefig(out_dir / "summary.png", dpi=130)
print("Saved", out_dir / "summary.png")
