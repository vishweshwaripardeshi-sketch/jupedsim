# Inputs for the Prayagraj bottleneck study, and where each came from

Geometry widths come from Mehrotra & Vera (Prayagraj 2013). **All lengths are assumed**: the book has no scaled plan.

| Input | Value | Source |
|---|---|---|
| B3 widths: route / bridge / alley | 50 m / 10 m / 3 m | Mehrotra & Vera, infographic PDF p.49 |
| B3 lengths: feeder / bridge / alley | 20 / 40 / 30 m | ASSUMED |
| B4 road width | 50 m (">50 m" processional route) | Mehrotra & Vera p.49 |
| B4 road length, langar queue (20 x 6 m, 3 p/m2) | 120 m; 20 x 6 m | ASSUMED (book only says langars feed >100,000 on peak days) |
| B5/B6 barricade strip depth | 2, 6, 10 m | Mehrotra & Vera p.42 (2-10 m); the three values are my picks within it |
| B5/B6 frontage / staging / exits | 60 m / 57 m deep / two 6 m passages | ASSUMED (shoreline is 3,700 m in the book; a 60 m slice is simulated) |
| Dip duration | 300 s (B5, B6 "controlled") | Haridwar paper (5 min average); police extraction: Mehrotra & Vera |
| Uncontrolled dips (B6) | lognormal, mean 300 s, CV 0.8 and 1.5 | ASSUMED |
| Bather spacing / aisles | 0.7 m (~2 p/m2), 1.7 m aisle per 3 rows | ASSUMED |
| Walking speed (adult) | mean 1.3 m/s | Still PhD thesis 3.1.3; SD 0.25 ASSUMED |
| Elderly / child speed factors | x0.70 / x0.80 | ASSUMED |
| Child / elderly share | 8% / 13% (21% combined) | Haridwar paper text for the 21%; the split is ASSUMED and unverified |
| Body radius | adult 0.25 m, child 0.18 m | 0.5 m body width: Still 2019, Haridwar paper; child ASSUMED |
| Group sizes | rural: 30% size 4-6, 34% 7-9, 36% 10-13; urban: 4:22%, 5:31%, 6:25%, 7-8:22% | Rai, Verma & Chakroborty (Ujjain 2016), Table 3 |
| Space per person in a group | 0.60 (rural), 0.57 (urban) m2 | Rai et al. Table 6 |
| Share of rural groups | 69% | Rai et al. (India 69% rural; census, as cited there) |
| Share of people walking in groups | 60% | ASSUMED (Rai et al. only sampled groups of 4+; cites 70% for non-Indian data) |
| Rural groups slightly faster | x1.05 | ASSUMED (Rai et al. say faster, give no number) |
| Group rule | whole group walks at its slowest member's speed; leader waits if followers lag > 2 m; groups dip together and leave together | Rai et al. (cohesion kept at all times); thresholds ASSUMED |
| Reference flow | 1.82 p/(m s) | Still PhD thesis 3.1.6 (Green Guide, 109 p/m/min) |
| Density limits | moving 1.5 / 2; standing 5 / 6; Green Guide 4 p/m2 | Haridwar paper (citing Oberhagemann 2012, Still 2014); Still thesis |
| Start densities | 0.5, 1.5, 3.0 p/m2 | my choice, bracketing the limits above |
