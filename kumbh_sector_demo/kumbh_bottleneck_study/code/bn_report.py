#!/usr/bin/env python3
"""Charts + summary table for the Prayagraj bottleneck study. Reads bn_runs/*, writes
kumbh_bottleneck_study/charts/*.png and data/summary.csv. All inputs are synthetic/assumed
where tagged in bn_sim.py; see INPUTS_AND_SOURCES.md."""
import csv
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon as MplPolygon

root = pathlib.Path(__file__).parent
RUNS = root / "bn_runs"
OUT = root / "kumbh_bottleneck_study"
CH, DATA = OUT / "charts", OUT / "data"
CH.mkdir(parents=True, exist_ok=True); DATA.mkdir(parents=True, exist_ok=True)
GG = 109 / 60.0  # Green Guide 1.82 p/(m s) [Still thesis 3.1.6]
NOTE = "Synthetic geometry (book widths, assumed lengths); Kumbh crowd mix from Rai et al. + assumptions - see INPUTS_AND_SOURCES.md"
CC = ["#1f77b4", "#ff7f0e", "#d62728", "#2ca02c", "#17becf"]
CLS = ["adult (single)", "elderly", "child (with group)", "adult in rural group", "adult in urban group"]


def load(name):
    d = RUNS / name
    if not (d / "metrics.json").exists():
        return None
    r = {"m": json.loads((d / "metrics.json").read_text()), "d": d}
    r["ts"] = np.genfromtxt(d / "timeseries.csv", delimiter=",", names=True)
    return r


def ghat_rate(ts):
    """Dip starts per minute while the queue is saturating the ghat; (nan, t_clear) if the queue cleared too early."""
    h = ts["n_hold"]; q = np.where(h > 20)[0]
    if not len(q):
        return float("nan"), None
    tc = float(ts["t"][q[-1]])
    for ta in (450.0,):
        if tc - ta >= 400:
            m = (ts["t"] >= ta) & (ts["t"] <= tc)
            d, t = ts["dips_started"][m], ts["t"][m]
            return float((d[-1] - d[0]) / (t[-1] - t[0]) * 60), tc
    return float("nan"), tc


def t99(r):
    co = r["ts"]["cum_out"]; return float(r["ts"]["t"][np.argmax(co >= 0.99 * r["m"]["walkers"])])


def foot(fig):
    fig.text(0.5, 0.003, NOTE, ha="center", fontsize=7, color="gray")


def save(fig, name):
    foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(CH / name, dpi=130); plt.close(fig); print("wrote", name)


def maps(runs, labels, fname, key="move", vmax=4, title=""):
    runs = [(r, l) for r, l in zip(runs, labels) if r]
    if not runs:
        return
    fig, axs = plt.subplots(1, len(runs), figsize=(5.2 * len(runs), 4.6), squeeze=False)
    for ax, (r, l) in zip(axs[0], runs):
        pk = np.load(r["d"] / "peakmaps.npz")
        pm = np.ma.masked_where(~pk["valid"], pk[key]).T
        im = ax.pcolormesh(pk["XE"], pk["YE"], pm, cmap="inferno", vmin=0, vmax=vmax)
        ax.add_patch(MplPolygon(pk["boundary"], closed=True, fill=False, ec="w", lw=0.6))
        ax.set(aspect="equal", title=l, xlabel="x [m]")
        fig.colorbar(im, ax=ax, shrink=0.7, label="peak p/m²")
    fig.suptitle(title, fontsize=11)
    save(fig, fname)


summary = []
allr = {}
for p in sorted(RUNS.glob("*/metrics.json")):
    allr[p.parent.name] = load(p.parent.name)

# ---------------- composition ----------------
r0 = allr.get("b3_r1.5_mixed")
if r0:
    m = r0["m"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    comp = m["composition"]
    ax[0].bar([k.replace(" ", "\n") for k in comp], list(comp.values()), color=CC)
    ax[0].set(ylabel="people", title=f"Crowd composition (n={m['walkers']})")
    ax[1].axis("off")
    ax[1].text(0, 0.95, f"Groups: {m['n_groups']}  (mean size {m['group_sizes']['mean']:.1f}, max {m['group_sizes']['max']})\n"
                        f"People walking in groups: {100*m['share_in_groups']:.0f}%  (ASSUMED 60%)\n\n"
                        "From Rai et al. (Ujjain 2016):\n  group sizes 4-13 (rural: 30% 4-6, 34% 7-9, 36% >9)\n"
                        "  space per person in group 0.60 (rural) / 0.57 (urban) m²\n"
                        "From Haridwar paper: 21% children+elderly\n"
                        "Assumed: elderly x0.70 and children x0.80 speed,\n  rural groups x1.05, children only inside groups",
               va="top", fontsize=9, family="monospace")
    save(fig, "00_crowd_composition.png")

# ---------------- B3 ----------------
B3NOTE = 'Bridge-entrance flow includes the initial filling of the 40 m bridge; the 3 m alley is the steady limit.'
dens = (0.5, 1.5, 3.0)
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
for k, (ln, w) in enumerate((("bridge_in", 10), ("alley_in", 3))):
    xs = np.arange(len(dens)); wd = 0.38
    for j, pop in enumerate(("mixed", "adults")):
        v = []
        for r in dens:
            rr = allr.get(f"b3_r{r}_{pop}")
            v.append(rr["m"]["flows_p_m_s"].get(ln, {}).get("sustained_specific_flow", np.nan) if rr else np.nan)
        ax[k].bar(xs + (j - 0.5) * wd, v, wd, label=f"{pop} crowd", color=["#4c78a8", "#aaaaaa"][j])
    ax[k].axhline(GG, color="r", ls="--", label=f"Green Guide {GG:.2f}")
    ax[k].set(xticks=xs, xticklabels=[f"{r} p/m²" for r in dens], ylabel="sustained specific flow p/(m·s)",
              title=f"Flow into the {w} m {'bridge' if w == 10 else 'alley'}")
    ax[k].legend(fontsize=8)
fig.text(0.5, 0.045, B3NOTE, ha="center", fontsize=7.5, color="#555"); save(fig, "B3_1_flow_vs_density.png")

fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), sharey=True)
for a, r in zip(ax, dens):
    rr = allr.get(f"b3_r{r}_mixed")
    if not rr:
        continue
    ts = rr["ts"]
    for z, c in zip(("feeder", "bridge", "alley"), ("#1f77b4", "#2ca02c", "#d62728")):
        a.plot(ts["t"], ts[f"dens_{z}"], c=c, label=f"{z} average")
    a.plot(ts["t"], ts["dens_move_max"], "k", lw=0.8, label="peak 2 m cell")
    a.axhline(2, color="gold", ls="--", lw=1); a.axhline(4, color="red", ls="--", lw=1)
    a.set(title=f"start density {r} p/m²", xlabel="time [s]")
ax[0].set_ylabel("p/m²"); ax[0].legend(fontsize=7)
save(fig, "B3_2_density_over_time.png")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
for r, c in zip(dens, ("#4c78a8", "#f58518", "#e45756")):
    for pop, ls in (("mixed", "-"), ("adults", ":")):
        rr = allr.get(f"b3_r{r}_{pop}")
        if rr:
            ts = rr["ts"]; ax[0].plot(ts["t"], ts["cum_out"] / rr["m"]["walkers"], c=c, ls=ls, label=f"{r} p/m² {pop}")
ax[0].set(xlabel="time [s]", ylabel="fraction that has left", title="Clearing the feeder through the 10 m -> 3 m cascade")
ax[0].legend(fontsize=7)
w = 0.12
for j, r in enumerate(dens):
    rr = allr.get(f"b3_r{r}_mixed")
    if not rr:
        continue
    bc = rr["m"]["travel_time_by_class_s"]
    ax[1].bar(np.arange(len(bc)) + (j - 1) * 0.27, [v["mean"] for v in bc.values()], 0.27, label=f"{r} p/m²")
    ax[1].set_xticks(np.arange(len(bc))); ax[1].set_xticklabels([k.replace(" ", "\n") for k in bc], fontsize=7)
ax[1].set(ylabel="mean travel time [s]", title="Travel time by pilgrim type (mixed crowd)"); ax[1].legend(fontsize=8)
save(fig, "B3_3_clearing_and_travel_time.png")
maps([allr.get(f"b3_r{r}_mixed") for r in dens], [f"{r} p/m² start" for r in dens], "B3_4_peak_density_maps.png", title="B3 width cascade - peak density (mixed crowd)")

# ---------------- B4 ----------------
b4 = [allr.get(f"b4_r{r}_langar") for r in dens] + [allr.get("b4_r3.0_nolangar")]
b4l = [f"{r} p/m² + langar queue" for r in dens] + ["3.0 p/m², no queue"]
maps(b4, b4l, "B4_1_peak_density_maps.png", title="B4 Akhara thoroughfare (50 m wide) - peak density of walkers")
fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))
for rr, l, c in zip(b4, b4l, ("#4c78a8", "#f58518", "#e45756", "#555555")):
    if rr:
        ts = rr["ts"]; ax[0].plot(ts["t"], ts["dens_move_max"], c=c, label=l)
        ax[1].plot(ts["t"], ts["cum_out"] / rr["m"]["walkers"], c=c, label=l)
ax[0].axhline(2, color="gold", ls="--"); ax[0].axhline(4, color="red", ls="--")
ax[0].set(xlabel="time [s]", ylabel="p/m²", title="Peak local density (2 m cells)"); ax[0].legend(fontsize=7)
ax[1].set(xlabel="time [s]", ylabel="fraction exited", title="Passing the langar zone to the far end")
names, means, p95 = [], [], []
for rr, l in zip(b4, b4l):
    if rr:
        names.append(l.replace(" + ", "\n+ ").replace(", ", ",\n")); means.append(rr["m"]["travel_time_s"]["mean"]); p95.append(rr["m"]["travel_time_s"]["p95"])
ax[2].bar(np.arange(len(names)) - 0.2, means, 0.4, label="mean"); ax[2].bar(np.arange(len(names)) + 0.2, p95, 0.4, label="95th pct")
ax[2].set_xticks(np.arange(len(names))); ax[2].set_xticklabels(names, fontsize=7); ax[2].set(ylabel="seconds", title="Travel time over 120 m"); ax[2].legend()
save(fig, "B4_2_throughput_density_time.png")
rr = allr.get("b4_r3.0_langar")
if rr:
    bc = rr["m"]["travel_time_by_class_s"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar([k.replace(" ", "\n") for k in bc], [v["mean"] for v in bc.values()], yerr=[v["p95"] - v["mean"] for v in bc.values()], color=CC, capsize=3)
    ax.set(ylabel="travel time [s] (bar = mean, whisker = 95th pct)", title="B4 at 3.0 p/m² with langar queue: who is slowest")
    save(fig, "B4_3_travel_time_by_type.png")

# ---------------- B5 ----------------
depths = (2, 6, 10)
d5 = [allr.get(f"b5_d{d}_r1.5") for d in depths]
fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
cap = [r["m"]["ghat"]["capacity_dips_per_min_at_300s"] if r else np.nan for r in d5]
mea = [ghat_rate(r["ts"])[0] if r else np.nan for r in d5]
xs = np.arange(3)
ax[0].bar(xs - 0.2, cap, 0.4, label="capacity (slots / 5 min)", color="#999999"); ax[0].bar(xs + 0.2, mea, 0.4, label="measured dip starts/min", color="#1d4ed8")
ax[0].set(xticks=xs, xticklabels=[f"{d} m strip" for d in depths], ylabel="people / min", title="Shoreline throughput vs strip depth (60 m frontage)"); ax[0].legend(fontsize=8)
for r, d, c in zip(d5, depths, ("#d62728", "#2ca02c", "#1f77b4")):
    if r:
        ax[1].plot(r["ts"]["t"], r["ts"]["n_hold"], c=c, label=f"{d} m strip")
ax[1].set(xlabel="time [s]", ylabel="people waiting for a slot", title="Queue formation at 1.5 p/m² start"); ax[1].legend()
for r, d, c in zip(d5, depths, ("#d62728", "#2ca02c", "#1f77b4")):
    if r:
        ax[2].plot(r["ts"]["t"], r["ts"]["dens_static_max"], c=c, label=f"{d} m strip")
ax[2].axhline(5, color="gold", ls="--", label="5 p/m² static max"); ax[2].axhline(6, color="red", ls="--", label="6 p/m² high risk")
ax[2].set(xlabel="time [s]", ylabel="p/m²", title="Peak density of bathers"); ax[2].legend(fontsize=7)
save(fig, "B5_1_strip_depth_sweep.png")

fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
d5r = {r: allr.get(f"b5_d6_r{r}") for r in dens}
for r, c in zip(dens, ("#4c78a8", "#f58518", "#e45756")):
    rr = d5r[r]
    if rr:
        ax[0].plot(rr["ts"]["t"], rr["ts"]["n_hold"], c=c, label=f"{r} p/m²")
        ax[1].plot(rr["ts"]["t"], rr["ts"]["n_bath"], c=c, label=f"{r} p/m²")
ax[0].set(xlabel="time [s]", ylabel="waiting", title="Queue (6 m strip)"); ax[0].legend()
ax[1].set(xlabel="time [s]", ylabel="bathing", title="People in the water strip")
lab, vals = [], []
for r in dens:
    rr = d5r[r]
    if rr:
        for c, v in rr["m"]["ghat"]["time_to_start_dip_by_class_s"].items():
            pass
cls_names = CLS
w = 0.27
for j, r in enumerate(dens):
    rr = d5r[r]
    if not rr:
        continue
    bc = rr["m"]["ghat"]["time_to_start_dip_by_class_s"]
    ax[2].bar(np.arange(len(bc)) + (j - 1) * w, [v["mean"] / 60 for v in bc.values()], w, label=f"{r} p/m²")
    ax[2].set_xticks(np.arange(len(bc))); ax[2].set_xticklabels([k.replace(" ", "\n") for k in bc], fontsize=7)
ax[2].set(ylabel="mean wait before dip [min]", title="Wait before the dip, by pilgrim type"); ax[2].legend(fontsize=8)
save(fig, "B5_2_density_sweep.png")
maps([allr.get(f"b5_d{d}_r1.5") for d in depths], [f"{d} m strip" for d in depths], "B5_3_peak_density_static.png", key="static", vmax=6,
     title="B5 shoreline - peak density of people standing in the water strip")

# ---------------- B6 ----------------
pol = [("controlled\n(police at 5 min)", allr.get("b5_d6_r1.5"), "b5_d6_r1.5"), ("free dips\n(CV 0.8)", allr.get("b6_free"), "b6_free"),
       ("free, long tail\n(CV 1.5)", allr.get("b6_free_long"), "b6_free_long")]
fig, ax = plt.subplots(2, 2, figsize=(13, 8.4))
for (l, rr, nm), c in zip(pol, ("#2ca02c", "#ff7f0e", "#d62728")):
    if not rr:
        continue
    a = np.load(rr["d"] / "agents.npz")
    dw = a["dwell"][~np.isnan(a["dwell"])]
    ax[0, 0].hist(dw / 60, bins=40, alpha=0.5, color=c, label=l.replace("\n", " "))
    ax[0, 1].plot(rr["ts"]["t"], rr["ts"]["n_hold"], c=c, label=l.replace("\n", " "))
ax[0, 0].set(xlabel="dip duration [min]", ylabel="people", title="Dip duration under each policy"); ax[0, 0].legend(fontsize=8)
ax[0, 1].set(xlabel="time [s]", ylabel="waiting for a slot", title="Queue"); ax[0, 1].legend(fontsize=8)
labs = [l for l, rr, _ in pol if rr]
ax[1, 0].bar(np.arange(len(labs)) - 0.2, [rr["m"]["ghat"]["time_to_start_dip_s"]["mean"] / 60 for _, rr, _ in pol if rr], 0.4, label="mean")
ax[1, 0].bar(np.arange(len(labs)) + 0.2, [rr["m"]["ghat"]["time_to_start_dip_s"]["p95"] / 60 for _, rr, _ in pol if rr], 0.4, label="95th pct")
ax[1, 0].set(xticks=np.arange(len(labs)), xticklabels=labs, ylabel="min", title="Time until a pilgrim gets to dip"); ax[1, 0].legend()
ax[1, 1].bar(np.arange(len(labs)), [ghat_rate(rr["ts"])[0] for _, rr, _ in pol if rr], color=["#2ca02c", "#ff7f0e", "#d62728"][:len(labs)])
ax[1, 1].axhline(pol[0][1]["m"]["ghat"]["capacity_dips_per_min_at_300s"] if pol[0][1] else 0, color="k", ls="--", label="capacity at 5 min dips")
ax[1, 1].set(xticks=np.arange(len(labs)), xticklabels=labs, ylabel="dip starts / min", title="Throughput"); ax[1, 1].legend()
save(fig, "B6_1_river_exit_policies.png")

# ---------------- summary ----------------
rows = []
for nm, r in sorted(allr.items()):
    if not r:
        continue
    m = r["m"]; g = m.get("ghat", {})
    rows.append(dict(run=nm, bottleneck=m["bottleneck"], start_density=m["rho0"], population=m["population"], walkers=m["walkers"],
                     completed=m["completed"], sim_s=round(m["simulated_time_s"]), mean_travel_s=round(m["travel_time_s"].get("mean", 0)),
                     p95_travel_s=round(m["travel_time_s"].get("p95", 0)), peak_moving_cell=m["density"]["moving_peak_cell"],
                     s_moving_above_2=m["density"]["moving_s_above_2.0"], peak_static_cell=m["density"]["static_peak_cell"],
                     max_queue=max(m["queue"]["max_holding"], m["queue"]["max_slow_agents"]),
                     t99_s=round(t99(r)), dips_per_min=("n/a" if np.isnan(ghat_rate(r["ts"])[0]) else round(ghat_rate(r["ts"])[0], 1)) if g else "", capacity=g.get("capacity_dips_per_min_at_300s", "") if g else "",
                     timeouts=g.get("slot_timeouts", "") if g else ""))
with open(DATA / "summary.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for nm, r in allr.items():
    if r:
        (DATA / f"{nm}_metrics.json").write_text(json.dumps(r["m"], indent=1))
fig, ax = plt.subplots(figsize=(17, 0.38 * len(rows) + 1.6)); ax.axis("off")
cols = ["run", "walkers", "completed", "t99_s", "mean_travel_s", "p95_travel_s", "peak_moving_cell", "s_moving_above_2", "peak_static_cell", "max_queue", "dips_per_min", "capacity", "timeouts"]
tb = ax.table(cellText=[[str(r[c]) if not isinstance(r[c], float) else f"{r[c]:.2f}" for c in cols] for r in rows], colLabels=cols, loc="center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(7.5); tb.scale(1, 1.25)
ax.set_title("All runs - key metrics (synthetic geometry; see report for caveats)", fontsize=11)
save(fig, "99_summary_table.png")
print("runs summarised:", len(rows))
