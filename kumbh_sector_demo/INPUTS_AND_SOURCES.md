# Inputs and where each came from (run_kumbh.py)

The layout is **schematic**: the papers give widths, lengths and times but no
coordinates or drawings, so the sector shape is stylised. Numbers marked
ASSUMED are my choices, not from any paper.

## Taken from the supplied papers
| Input | Value | Source |
|---|---|---|
| Pontoon bridge width (used for all 3 gates) | 10 m | Mehrotra & Vera, *Kumbh Mela: Mapping the Ephemeral Megacity* (Prayagraj 2013), infographic, PDF p.49 (OCR) |
| Bathing strip depth | 10 m (upper bound of 2-10 m) | same, PDF p.42: shore strip where barricades/sandbags are placed, 2-10 m wide |
| Duration of one dip | 5 min (300 s) | Haridwar paper (Spatial Strategies for Crowd Management), section 3.4 |
| Free walking speed (mean) | 1.3 m/s | Still PhD thesis, 3.1.3 (fast steady walk, Hillsborough gate C) |
| Body width -> agent radius | 0.5 m -> 0.25 m | Still 2019 (50 x 30 cm ellipse); Haridwar paper (0.5 m) |
| Moving-crowd density limits | 1.5 acceptable, 2.0 critical p/m2 | Haridwar paper citing Oberhagemann 2012 |
| Static-crowd density limits | 5 max, 6 high risk p/m2 | Haridwar paper citing Still 2014 |
| Green Guide concern level | 4 p/m2 | Still PhD thesis (Green Guide discussion) |
| Reference gate flow | 109 p/m/min = 1.82 p/(m s) | Still PhD thesis, 3.1.6 (Green Guide) |
| Flat (transport-limited) arrival profile | constant release rate | Still 2019, Fig. 2 (RAMP: arrival profiles) |
| Holding queue before the ghat, flow throttled | design choice backed by | Gayathri et al., *Crowd Dynamics in Processions* (Shahi Snan 2016, Nashik): crowd stopped ~100 m before the ghat, inflow kept <= outflow |

## Assumed (not in any supplied paper)
Walking-speed SD 0.25 m/s; radius SD 0.02 m; bridge length 40 m; plaza 90 x 100 m;
shore frontage 100 m (a slice of the 3,700 m Sangam shoreline); bather spacing
0.7 m (~2 per m2); gate split 40/30/30; total release 600 persons/min; exit
passages 10 x 20 m; 24 holding points; bathers leave along the shore.
**5000 pilgrims and three gates came from your request.**

## In the papers but not used
- Mauni Amavasya 2013: 30.5 million attendance; 8 million on the opening day (Prayagraj PDF p.42, p.275). Official headcount is disputed (40-60 million vs 120 million, footnote 3). Too large to scale to one sector without sector-level counts.
- 14 bathing hours/day (5 am-7 pm); 3 m tent-block alleys; >50 m processional routes; 156 km of temporary roads.
- Stairs: Still's thesis gives 40 p/min (stairs) vs 60 p/min (level) per unit width; JuPedSim 1.4.2 is 2D, so ghat steps are not modelled.
- Prayagraj bridge count conflicts inside the same PDF: text says 17, infographic says 18.

## Still missing
Coordinates of a real sector, measured inflow over time, measured walking speeds
at Prayagraj, gate-wise shares, and any validation data (video/counts).
