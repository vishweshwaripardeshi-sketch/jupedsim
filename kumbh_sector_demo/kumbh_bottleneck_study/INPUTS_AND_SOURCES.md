# Inputs for the Prayagraj bottleneck study: sources, and the basis for every assumption

Three kinds of entry:
- **PAPER**: taken from one of the supplied papers.
- **ASSUMED + support**: my choice, with published evidence that makes the value reasonable (see notes on how well I checked it).
- **ASSUMED, no source**: my judgment only. Treat these as the weakest inputs.

Widths come from Mehrotra & Vera (Prayagraj 2013). **All lengths are assumed**: the book has no scaled plan.

## A. Taken from the supplied papers
| Input | Value | Source |
|---|---|---|
| B3 widths: route / bridge / alley | 50 m / 10 m / 3 m | Mehrotra & Vera, infographic, PDF p.49 |
| B4 road width | 50 m (">50 m" processional route) | Mehrotra & Vera, p.49 |
| Barricade/sandbag strip depth range | 2-10 m | Mehrotra & Vera, p.42 |
| Dip duration (average) | 300 s (5 min) | Haridwar paper, section 3.4 |
| Police remove people from the river; immersion once a day | qualitative | Mehrotra & Vera, text on security |
| Adult mean walking speed | 1.3 m/s | Still PhD thesis, 3.1.3 |
| Body width / adult radius | 0.5 m / 0.25 m | Still 2019; Haridwar paper |
| Group sizes | rural: 30% size 4-6, 34% size 7-9, 36% size 10-13; urban: 4:22%, 5:31%, 6:25%, 7-8:22% | Rai, Verma & Chakroborty (Ujjain 2016), Table 3 |
| Space per person inside a group | 0.60 (rural), 0.57 (urban) m2 | Rai et al. Table 6 |
| Groups stay together (cohesion) | qualitative | Rai et al., sections 2.1, 4.4 |
| Children + elderly share | 21% combined | Haridwar paper text (citing Raheja 2015) |
| Reference flow | 1.82 p/(m s) | Still PhD thesis 3.1.6 (Green Guide 109 p/m/min) |
| Density limits | moving 1.5 / 2; standing 5 / 6; concern level 4 p/m2 | Haridwar paper (citing Oberhagemann 2012 and Still 2014); Still thesis |

## B. Assumed, with the basis for each
| Input | Value used | Basis for the assumption | Support / source (and how well I checked it) |
|---|---|---|---|
| Adult speed spread (SD) | 0.25 m/s | A typical spread of walking speed in a mixed crowd. No source for the SD itself | The mean is supported: Chattaraj, Seyfried & Chakroborty (2009) measured Indian free-flow speed 1.27 m/s (SE 0.03), German 1.24 m/s, [arXiv 0903.0149](https://arxiv.org/abs/0903.0149) (search summary, not read in full; Indian sample was male-only) |
| Elderly speed factor | x0.70 of adult | Elderly walk slower in published studies; 0.70 sits in the slower half of the reported range | Reported elderly/young ratios: ~0.91 (1.28 vs 1.4 m/s, corridor study, an arXiv paper whose exact ID I could not pin down from the snippet); ~0.82 (0.94 m/s Chinese elders vs 1.15 m/s French young adults, single-file, [arXiv 1912.07944](https://arxiv.org/abs/1912.07944)); ~0.67 (about 1.04 vs 1.55 m/s elderly/disabled vs young adults, midblock crossings, [TRID 1439021](https://trid.trb.org/View/1439021)); ~0.6 in irregular flows ("40% slower", citing Gorrini et al., via a search summary). **From search snippets only; not read in full.** None is from India or Kumbh |
| Child speed factor | x0.80 of adult | Judgment: children in groups walk slower than adults but not as slow as toddlers | Weak. One table gives 3-5 year-olds a mean of 0.49 (slow) to 0.98 m/s (fast), 7 subjects ([PMC9036623 table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC9036623/table/T1)), far below 0.8 x 1.3 for very young children. No data for older children |
| Child radius | 0.18 m | Scaled from the adult body width; children are smaller | No source |
| Rural groups slightly faster | x1.05 | Rai et al. say rural groups walk at a higher average speed (head loads) but give no number | Direction from Rai et al.; the 5% is arbitrary |
| Child / elderly split of the 21% | 8% / 13% | The Haridwar text gives only the combined 21% | The split came from a chart in that paper that I could not re-read; unverified |
| Share of people walking in groups | 60% | Rai et al. only sampled groups of 4+, so the share isn't in the paper; they cite up to 70% for sidewalks in a non-Indian study | Moussaid et al. 2010, as cited by Rai et al. (original not read). I picked 60% as a cautious value below that 70% |
| Share of rural groups | 69% | India's rural population share, used as a stand-in; Rai et al. say most Kumbh pilgrims come from a rural base | Census of India 2011 as cited in Rai et al. This is a proxy, not a measured share of Kumbh groups |
| Cohesion rule: lag limit 2 m; follower boost x1.25; leader slow-down x0.6 | as stated | The 2 m limit is just beyond the radius of a typical rural group footprint (2.8-7.2 m2, Rai et al. Table 4). Boost and slow-down factors are tuning values | Only the footprint is from Rai et al. The factors have no source |
| Groups dip together and leave together | rule | Extension of Rai et al.'s finding that groups keep together at all times | Not in any paper |
| Uncontrolled dip distribution | lognormal, mean 300 s, CV 0.8 and 1.5 | Mean from the Haridwar paper; lognormal because durations are positive and skewed to the long side | **No data on dip-time spread anywhere in the papers.** The CV values are arbitrary, so the size of the "free dips" penalty in B6 is not trustworthy |
| B3 lengths: feeder 20 m, bridge 40 m, alley 30 m | as stated | Feeder sized so the start crowd stays manageable (445 to 2,730 people); bridge and alley long enough to show a steady flow | No source: the book gives no lengths |
| B4 road length 120 m | 120 m | Long enough for the crowd to spread out | No source |
| Langar queue 20 x 6 m at 3 p/m2 | as stated | A dense queue below the 4 p/m2 concern level | No source for the size; the book only says langars feed >100,000 on peak days. The "no effect" result depends on this size |
| Strip depths tested | 2, 6, 10 m | 2 and 10 are the book's range; 6 is the midpoint | Range from Mehrotra & Vera p.42 |
| Shoreline slice | 60 m frontage, staging 57 m deep | A computable slice of the 3,700 m shoreline | No source |
| Exit passages | two, 6 m wide | Wide enough not to throttle leavers | No source |
| Bather spacing | 0.7 m (about 2 per m2) | 0.5 m body width plus margin; kept well below the 5/6 p/m2 standing limits; slightly tighter than the 0.75-0.77 m centre spacing implied by Rai et al.'s group space | Limits from the Haridwar paper; spacing itself no source |
| Aisles | 1.7 m after every 3 slot rows | Added after my first layout jammed (21% timeouts); wide enough for two people to pass | No source |
| Start densities | 0.5, 1.5, 3.0 p/m2 | Bracket the limits: below, at, and above the 1.5-2 p/m2 moving limit and the 4 p/m2 concern level | Limits from the Haridwar paper |
| Holding queue as 24 waypoint clusters; whole groups assigned slots together | modelling choices | Needed to stop deadlocks seen in early versions | No source |

## C. Things I did not use but that would improve this study
Kumbh-specific walking speeds by age (the Kumbh Mela Experiment GPS data behind Rai et al.), measured dip-time distributions at a ghat, a scaled sector plan, and observed flows at a bridge or ghat for validation.
