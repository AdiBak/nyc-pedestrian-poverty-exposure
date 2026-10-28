"""Draw the robustness figure from robustness.csv.

Run from the paper folder:  python make_figures.py
The values in robustness.csv are copied from docs/CHECKS_LOG.md and docs/research_log.md.
Before submission, replace the csv with output written by the package so every number traces to code.
"""
import csv
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = pathlib.Path(__file__).parent
rows = list(csv.DictReader(open(here / "robustness.csv")))

fig, ax = plt.subplots(figsize=(6.4, 5.6))
y = len(rows)
ticks, labels = [], []
last = None
for r in rows:
    y -= 1
    if r["group"] != last and last is not None:
        y -= 0.6
    last = r["group"]
    rr = float(r["rr"])
    if r["lo"]:
        ax.plot([float(r["lo"]), float(r["hi"])], [y, y], color="0.25", lw=1.6)
        ax.plot(rr, y, "o", color="0.1", ms=5)
    else:
        ax.plot(rr, y, "o", mfc="white", mec="0.1", ms=5)
    ticks.append(y)
    labels.append(r["label"])
ax.axvline(1.16, color="0.6", ls=":", lw=1)
ax.axvline(1.0, color="0.3", lw=0.8)
ax.set_yticks(ticks)
ax.set_yticklabels(labels, fontsize=8)
ax.set_xlim(0.98, 1.30)
ax.set_xlabel("Rate ratio per 10 point increase in tract poverty rate", fontsize=9)
ax.tick_params(axis="x", labelsize=8)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(here / "figures" / "robustness.pdf")
print("wrote figures/robustness.pdf")
