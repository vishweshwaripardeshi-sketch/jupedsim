# Prayagraj bottleneck simulations: results

Four of the six bottlenecks taken from Mehrotra & Vera's book (3 width cascade, 4 Akhara thoroughfare,
5 Sangam shoreline front, 6 river-exit control) were simulated with JuPedSim 1.4.2 (Collision-Free Speed Model)
for a mixed Kumbh crowd at three start densities. **Read the caveats before quoting any number.** The widths come from
the book, but every length, the crowd mix shares and the behaviour rules are assumptions
(see [INPUTS_AND_SOURCES.md](INPUTS_AND_SOURCES.md)). This is a model of how these shapes behave, not a forecast for Prayagraj.

## What was simulated
- **Crowd:** singles, rural and urban groups (sizes 4-13 and space per person from Rai et al., Ujjain 2016), elderly,
  children (only inside groups). In the 3.0 p/m2 B3 run, for example, about 63% of the 2,730 people walked in 229 groups of mean size 7.5.
  Groups walk at their slowest member's speed and keep together ([00_crowd_composition.png](charts/00_crowd_composition.png)).
- **Densities:** the crowd starts packed at 0.5, 1.5 or 3.0 people/m2 (limits from your papers: 1.5-2 moving, 4 Green Guide, 5-6 standing).
- **18 runs:** B3 and B4 at 3 densities, B3 also with an all-adult baseline, B4 with a no-queue baseline; B5 with strip depths 2/6/10 m
  and densities 0.5/1.5/3.0 at 6 m, plus an all-adult baseline; B6 with three dip policies. Every run uses one random seed.
- **Outputs:** [charts/](charts/) (PNG), [videos/](videos/) (12 MP4), [data/summary.csv](data/summary.csv), per-run metrics and time series.

## B3: width cascade (50 m route -> 10 m bridge -> 3 m alley)
- **The 3 m alley is the limit.** Its sustained flow was 0.68-0.71 p/(m s) (about 2.1 people/s) at every density, so clearing time just
  scales with crowd size: 99% had left after 309 s (463 people), 730 s (1,344) and 1,409 s (2,730) for the mixed crowd.
  The 10 m bridge and 50 m route are not limiting. ([B3_1](charts/B3_1_flow_vs_density.png), [B3_3](charts/B3_3_clearing_and_travel_time.png))
- **The queue builds inside the bridge, not the feeder.** Peak bridge density reached 3.2 p/m2 at the highest start density; moving-crowd density
  stayed above 2 p/m2 for 1,357 s. The alley itself stayed near 1.1-1.2 p/m2. ([B3_2](charts/B3_2_density_over_time.png), [B3_4](charts/B3_4_peak_density_maps.png))
- **Mixed crowd vs all adults:** the mixed crowd took 8-14% longer on average (191 vs 168 s, 409 vs 374 s, 745 vs 689 s). The cause in the model is group
  cohesion (slowest-member speed). Elderly and children were *not* slower on average than adults (e.g. 743 vs 747 s at 3.0 p/m2): when a queue sets the pace, individual
  walking speed hardly matters.
- **Against the reference:** 0.7 p/(m s) is about 39% of the Green Guide's 1.82. The model's narrow-channel capacity is probably lower than real pilgrim flow, so absolute
  clearing times are likely overestimated; I did not calibrate this.

## B4: Akhara thoroughfare (50 m wide, langar queue on one edge)
- **A 20 x 6 m langar queue made no measurable difference** on a 50 m road: at 3.0 p/m2 mean travel time was 263 s with and without it (95th percentile 395 vs 394 s).
  The delay comes from the packed starting crowd, not from the queue: mean 145 / 197 / 263 s at 0.5 / 1.5 / 3.0 p/m2. ([B4_2](charts/B4_2_throughput_density_time.png))
- Peak walker density was 2.3 / 3.5 / 3.75 p/m2 at the three densities, mostly at the start. ([B4_1](charts/B4_1_peak_density_maps.png))
- This only holds for the queue size I assumed; the book gives no queue dimensions. It says nothing about narrower thoroughfares, whose widths the book does not give.
- By type, travel times differed little (adults 260 s, elderly 267 s, children 252 s, rural groups 261 s, urban groups 278 s at 3.0 p/m2). ([B4_3](charts/B4_3_travel_time_by_type.png))

## B5: Sangam shoreline front (60 m frontage slice, 5-minute dip)
- **Strip depth is the dominant lever.** At 1.5 p/m2 the mean wait before a pilgrim could dip was 2,209 s (37 min) for a 2 m strip, 524 s (8.7 min) for 6 m
  and 287 s (4.8 min) for 10 m; 95th percentiles 4,369 / 1,128 / 721 s. The 2 m strip took 4,539 s to clear its queue, the 6 m strip 1,061 s, the 10 m strip 652 s.
  ([B5_1](charts/B5_1_strip_depth_sweep.png))
- **Density sweep at 6 m:** mean wait 57 s / 524 s / 1,263 s at 0.5 / 1.5 / 3.0 p/m2; queue cleared at 305 / 1,061 / 2,647 s. ([B5_2](charts/B5_2_density_sweep.png))
- **Throughput:** measured dip starts per minute were 17.4 (capacity 22.8) for the 2 m strip and 56.9 (capacity 91.2) at 6 m, i.e. 62-76% of the slot capacity;
  55.3/min at 3.0 p/m2. For the 10 m strip and the 0.5 p/m2 run the queue cleared too early to measure a steady rate, so none is reported.
- **Standing densities stayed well under the limits:** bathers peaked at 2.0-2.5 p/m2 (the slot layout sets this), never near 5-6. The waiting crowd peaked at 4.5 p/m2 at 3.0 p/m2 start,
  above the Green Guide's 4 but under 5 ([B5_3](charts/B5_3_peak_density_static.png)). The "moving above 2 p/m2" figures in the summary table include that standing queue.
- **Groups cost time:** the all-adult crowd waited 437 s on average against 524 s for the mixed crowd (+20%), because groups need several free slots together and leave together.
- Urban-group members waited longer than other types (685 s vs ~500 s at 6 m). I did not investigate this; it may be sampling noise (one seed) or an artefact of group slot allocation.

## B6: river-exit control (dip policy at a 6 m strip, 1.5 p/m2)
| Policy | Mean wait before dip | 95th pct | Throughput | Queue cleared | Mean total time |
|---|---|---|---|---|---|
| Controlled: everyone out at 5 min | 524 s | 1,128 s | 56.9 /min | 1,061 s | 1,005 s |
| Free dips (mean 5 min, CV 0.8) | 670 s | 1,570 s | 40.8 /min | 1,550 s | 1,356 s |
| Free, long tail (mean 5 min, CV 1.5) | 709 s | 1,854 s | 31.5 /min | 1,812 s | 1,521 s |

With the same average dip time, letting dips vary cut throughput by 28% and 45% and raised the mean wait by 28% and 35%. The spread of dip times matters, not just the average, partly because a group
only leaves when its slowest member is done. ([B6_1](charts/B6_1_river_exit_policies.png)) The uncontrolled distributions are my assumption. The model does not simulate the
"once a day" immersion rule or the police extraction itself, only their effect as a fixed 5-minute dip.

## Caveats
1. **Geometry:** widths are from the book; all lengths, the 60 m frontage and the exit passages are assumed. The book's maps have no scale bar.
2. **Crowd model:** group sizes and spacing are from one study (Rai et al., rural/urban groups of 4+ in Ujjain). Share of people in groups (60%), elderly/child speed factors, rural speed bonus,
   the child/elderly split, and the cohesion rule are assumptions.
3. **One random seed per run, no replicates.** Differences under about 10% (such as most differences between pilgrim types) should not be read as real.
4. **Packed-start experiments:** everyone starts at t = 0. In B5/B6 this makes the dips run in synchronised waves (the steps in the queue curves), and the waiting crowd forms 24 clusters at waypoints
   rather than a continuous queue. A staggered arrival process would look different.
5. **Capacity vs reference:** the model's narrow-channel flow (0.7 p/(m s)) is well below the Green Guide's 1.82. Absolute times are uncalibrated; comparisons between scenarios are more trustworthy than the numbers themselves.
6. **Artefacts:** 2-4 agents per B3 run (0.15%) got stuck in the corner pockets where the bridge steps down to the alley and are excluded from means; 0-64 agents (up to 4.5%; none in the 2 m strip run) in B5/B6 started their dip
   after a 400 s timeout without reaching their slot.
7. **Not modelled:** stairs, wet surfaces, counter-flow on bridges, panic, the police themselves, the 7 km perimeter walk-in (bottleneck 1), the pontoon bridges' full length (2) and the three bottlenecks' interaction.
8. **No validation:** nothing was compared with observed Kumbh flows or densities.

## Files
- [charts/](charts/): 00 composition; B3_1-4; B4_1-3; B5_1-3; B6_1; 99 summary table
- [videos/](videos/): b3 (3 densities), b4 (3), b5 (strip depths 2/6/10 and 3.0 p/m2), b6 (free, free_long); colour = pilgrim type, black ring = bathing, grey = static queuers.
  The "controlled" B6 case is `b5_d6_r1.5.mp4`.
- [data/](data/): summary.csv, per-run metrics JSON and time series
- [code/](code/): bn_sim.py (model), run_all.py (the 18 runs), bn_report.py, bn_video.py
