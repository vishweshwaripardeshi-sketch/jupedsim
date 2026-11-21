# Kumbh ghat crowd simulation (JuPedSim) - 5000 pilgrims, 3 gates -> 1 ghat

Layout is **schematic** (the papers give widths/times but no coordinates).
Inputs taken from the supplied papers vs. assumed are listed in
[INPUTS_AND_SOURCES.md](INPUTS_AND_SOURCES.md). Read that first.

## Scenario (`run_kumbh.py`)
5000 pilgrims enter over three 10 m pontoon bridges (width: Prayagraj 2013, Mehrotra & Vera),
queue in a holding area, take a 5-minute dip (Haridwar paper) in a 100 m bathing strip, and
leave along the shore. Walking speed 1.3 m/s (Still), body width 0.5 m, flat arrival profile.
JuPedSim 1.4.2, Collision-Free Speed Model.

## Results (`results/`, synthetic layout)
- `simulation.mp4`, `simulation.gif`, `layout.png`
- `density_timeseries.png`, `peak_density_map.png`, `travel_time.png`,
  `queue_formation.png`, `bottleneck.png`, `metrics.json`, `timeseries.csv`

| Metric | Value |
|---|---|
| Completed | 5000/5000 in 2583 s |
| Ghat capacity (assumed layout) / sustained throughput | 192 / 153 dips per min |
| Demand | 600 people/min |
| Largest holding queue | 3357 people at t=500 s, cleared by ~1911 s |
| Wait in holding before a slot | mean 656 s, p95 1373 s |
| Total entry-to-exit | mean 1200 s, p95 1840 s |
| Peak local density, moving/standing | 4.25 / 2.5 p/m2 (2 m cells) |
| Bridge flow | at most 0.45 p/(m s) = 25% of Green Guide 1.82; bridges are not the bottleneck |

## Limitations (important)
- The ghat is the bottleneck, but its capacity (192/min) follows directly from my assumed
  100 m frontage, 0.7 m slot spacing and aisle layout, so the queue size is mostly an
  assumption, not a finding.
- "Moving" density includes people waiting in the holding queue, so its time above
  2 p/m2 (~1900 s) overstates risk for a standing crowd; compare with the 5/6 p/m2 static limits.
- 96 of 5000 agents (1.9%) timed out reaching their slot and started their dip anyway.
- No stairs, groups, wet-surface effects or counter-flow on the bridges. 2D model.
- An earlier version with a shared arrival/exit strip jammed (21% timeouts); the strip now has
  a walkway and aisles. `legacy_assumed_inputs/` holds the first, assumption-only demo.

## Run
```
pip install -r requirements.txt
python run_kumbh.py 5000
python make_results.py 5000
```
