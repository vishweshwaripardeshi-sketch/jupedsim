#!/usr/bin/env python3
"""Run the full bottleneck study (18 runs), 3 at a time (RAM-limited)."""
import json
import pathlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

root = pathlib.Path(__file__).parent
py = str(root / ".venv" / "Scripts" / "python.exe")
runs = []
# B3 width cascade: 3 densities x {mixed Kumbh crowd, all-adult baseline}
for r in (0.5, 1.5, 3.0):
    for pop in ("mixed", "adults"):
        runs.append(dict(name=f"b3_r{r}_{pop}", bn="B3", rho0=r, pop=pop, max_time=2500))
# B4 Akhara thoroughfare with langar queue, 3 densities + no-queue baseline at the highest density
for r in (0.5, 1.5, 3.0):
    runs.append(dict(name=f"b4_r{r}_langar", bn="B4", rho0=r, pop="mixed", langar=True, max_time=1500))
runs.append(dict(name="b4_r3.0_nolangar", bn="B4", rho0=3.0, pop="mixed", langar=False, max_time=1500))
# B5 shoreline front: strip depth sweep (2, 6, 10 m) at 1.5 p/m2, density sweep at 6 m, adult baseline
for d in (2, 6, 10):
    runs.append(dict(name=f"b5_d{d}_r1.5", bn="B5", rho0=1.5, pop="mixed", strip_depth=d, policy="controlled", max_time=7000))
for r in (0.5, 3.0):
    runs.append(dict(name=f"b5_d6_r{r}", bn="B5", rho0=r, pop="mixed", strip_depth=6, policy="controlled", max_time=7000))
runs.append(dict(name="b5_d6_r1.5_adults", bn="B5", rho0=1.5, pop="adults", strip_depth=6, policy="controlled", max_time=7000))
# B6 river-exit control: police-controlled (= b5_d6_r1.5) vs uncontrolled dips
for pol in ("free", "free_long"):
    runs.append(dict(name=f"b6_{pol}", bn="B6", rho0=1.5, pop="mixed", strip_depth=6, policy=pol, max_time=7000))

only = sys.argv[1:]  # optional name filters
if only:
    runs = [r for r in runs if any(o in r["name"] for o in only)]
(root / "bn_runs").mkdir(exist_ok=True)


def go(cfg):
    out = root / "bn_runs" / cfg["name"]
    if (out / "metrics.json").exists():
        return cfg["name"], "skip (done)"
    log = open(root / "bn_runs" / f"{cfg['name']}.log", "w")
    rc = subprocess.run([py, str(root / "bn_sim.py"), json.dumps(cfg)], stdout=log, stderr=subprocess.STDOUT).returncode
    return cfg["name"], f"rc={rc}"


with ThreadPoolExecutor(3) as ex:
    for name, st in ex.map(go, runs):
        print(name, st, flush=True)
print("ALL DONE", flush=True)
