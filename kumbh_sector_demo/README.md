# Kumbh-style ghat crowd simulation (JuPedSim) - synthetic demo

**All geometry and parameters are assumed placeholders, not real Prayagraj data.**
The purpose is to show the simulation workflow; results should not be read as
predictions for a real sector.

## Scenario (`run_ghat.py`)
5000 pilgrims enter through three 8 m gates (west 2000, north 1500, south 1500;
600 people/min total for ~8 min), cross an 80x50 m plaza, pass a 5 m wide, 20 m
long neck (the bottleneck) and reach a ghat basin. Model: Collision-Free Speed
Model, dt = 0.05 s.

## Results (`results/`)
- `simulation.mp4`, `simulation.gif` - animation (colour = speed)
- `density_timeseries.png`, `peak_density_map.png` - density
- `travel_time.png` - travel time by gate
- `queue_formation.png` - queue growth and snapshot at maximum queue
- `bottleneck.png` - cumulative curves, flow across the neck, neck speed/density
- `metrics.json`, `timeseries.csv` - numbers

Headline (synthetic inputs): the neck passes ~222 people/min against ~600/min
demand, so a queue of up to ~2750 people builds in front of it and takes ~15 min
to clear after the last entry. Peak local density 6.0 p/m2 (2 m cells); mean
travel time ~600 s.

## Known limitations
- "Queue length" metric is unreliable (reported 59 m, snapshot shows ~23 m); use the snapshot.
- Neck flow (0.74 p/(m*s)) is below published values (~1.2-1.9) and is uncalibrated.
- No dwell time at the water, no groups, no exit flow, no obstacles.
- Waypoints inside a crowded plaza caused a deadlock in an early version, so agents are routed straight to the exit.

## Run
```
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python run_ghat.py 5.0      # neck width in m
python make_video.py        # needs out_ghat_neck5m/frames.npz from the run
```
`run_sector.py` is the earlier, simpler single-sector demo (`python run_sector.py 400`).
Written for the PyPI `jupedsim` 1.4.2 API (differs from the repo's current master API).
