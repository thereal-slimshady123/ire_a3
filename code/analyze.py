"""Part 2 analysis: operating points, trade-off figures, LaTeX tables, merged CSV.

Operating points are chosen on the tuning half of the queries (the fastest
setting that reaches the target recall there). The numbers printed and plotted
are then measured on the reporting half.
"""
import csv
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from common import FIGURES_DIR, RAW_DIR, RESULTS_DIR  # noqa: E402

TABLES_DIR = RESULTS_DIR / "tables"
DATASETS = ["sift", "glove"]
DATASET_LABEL = {"sift": "SIFT-1M (L2)", "glove": "GloVe-100 (normalised)"}
INDEXES = ["hnsw", "ivfflat", "ivfpq"]
LABEL = {"hnsw": "HNSW", "ivfflat": "IVF-Flat", "ivfpq": "IVF-PQ", "exact": "Exact"}
NUMERIC = {"recall", "qps", "seconds_total", "build_seconds", "index_bytes",
           "bytes_per_vector", "n_vectors", "value", "threads", "queries", "seconds"}


def read_raw(name):
    path = RAW_DIR / f"{name}.csv"
    if not path.exists():
        return []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for key in NUMERIC & r.keys():
            if r[key] not in ("", None):
                r[key] = float(r[key])
    return rows


def merge_results():
    """One row per benchmark run, with the experiment it came from."""
    rows = []
    for path in sorted(RAW_DIR.glob("*.csv")):
        for r in read_raw(path.stem):
            r = dict(experiment=path.stem, **r)
            rows.append(r)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    out = RESULTS_DIR / "results.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, restval="")
        writer.writeheader()
        writer.writerows(rows)
    return out


def operating_point(rows, dataset, kind, target):
    """Fastest tuning-half setting with recall >= target; its reporting-half numbers."""
    tune = {(r["build"], r["value"]): r for r in rows
            if r["dataset"] == dataset and r["index"] == kind and r["split"] == "tune"}
    report = {(r["build"], r["value"]): r for r in rows
              if r["dataset"] == dataset and r["index"] == kind and r["split"] == "report"}
    eligible = [key for key, r in tune.items() if r["recall"] >= target]
    if not eligible:
        return None
    best = max(eligible, key=lambda key: tune[key]["qps"])
    chosen = report[best]
    return dict(build=best[0], value=best[1], recall=chosen["recall"], qps=chosen["qps"],
                build_seconds=chosen["build_seconds"], index_bytes=chosen["index_bytes"],
                bytes_per_vector=chosen["bytes_per_vector"], param=chosen["param"])


def pareto(points):
    """Points not beaten on both recall and speed by another point."""
    frontier = []
    for recall, qps in sorted(points, key=lambda p: (-p[0], -p[1])):
        if not frontier or qps > frontier[-1][1]:
            frontier.append((recall, qps))
    return sorted(frontier)


def exact_row(part1, dataset):
    for r in part1:
        if r["dataset"] == dataset and r["mode"] == "single query, 1 thread":
            return r
    return None


def figure(rows, part1, dataset):
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    markers = {"hnsw": "o", "ivfflat": "s", "ivfpq": "^"}
    for kind in INDEXES:
        points = [(r["qps"], r["recall"]) for r in rows
                  if r["dataset"] == dataset and r["index"] == kind and r["split"] == "report"]
        if not points:
            continue
        front = pareto([(rec, q) for q, rec in points])
        ax.plot([q for _, q in front], [rec for rec, _ in front], marker=markers[kind],
                label=LABEL[kind])
    ex = exact_row(part1, dataset)
    if ex:
        ax.scatter([ex["qps"]], [1.0], marker="*", s=160, color="black", label="Exact (1 thread)",
                   zorder=5)
    ax.set_xscale("log")
    ax.set_xlabel("queries per second (one query at a time, one thread, log scale)")
    ax.set_ylabel("recall@10")
    ax.set_title(DATASET_LABEL[dataset])
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"recall_vs_qps_{dataset}.png", dpi=160)
    plt.close(fig)


def tex_escape(s):
    return str(s).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def write_tables(rows, part1):
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    speed_lines = [
        r"\begin{tabular}{llrr}",
        r"\toprule",
        r"Dataset & Index & QPS @ recall 0.90 & QPS @ recall 0.95 \\",
        r"\midrule",
    ]
    cost_lines = [
        r"\begin{tabular}{llllrrr}",
        r"\toprule",
        r"Dataset & Index & Build setting & Param & Build (s) & Index (MiB) & Bytes/vector \\",
        r"\midrule",
    ]
    for dataset in DATASETS:
        ex = exact_row(part1, dataset)
        if ex:
            speed_lines.append(
                f"{DATASET_LABEL[dataset]} & Exact & \\multicolumn{{2}}{{r}}{{{ex['qps']:.1f} (no recall loss)}} \\\\")
        for kind in INDEXES:
            p90 = operating_point(rows, dataset, kind, 0.90)
            p95 = operating_point(rows, dataset, kind, 0.95)
            c90 = f"{p90['qps']:.1f}" if p90 else "not reached"
            c95 = f"{p95['qps']:.1f}" if p95 else "not reached"
            speed_lines.append(f"{DATASET_LABEL[dataset]} & {LABEL[kind]} & {c90} & {c95} \\\\")
            if p95:
                cost_lines.append(
                    f"{DATASET_LABEL[dataset]} & {LABEL[kind]} & {tex_escape(p95['build'])} & "
                    f"{p95['param']}={int(p95['value'])} & {p95['build_seconds']:.1f} & "
                    f"{p95['index_bytes'] / 2**20:.1f} & {p95['bytes_per_vector']:.1f} \\\\")
            else:
                cost_lines.append(
                    f"{DATASET_LABEL[dataset]} & {LABEL[kind]} & -- & -- & -- & -- & -- \\\\")
    speed_lines += [r"\bottomrule", r"\end{tabular}"]
    cost_lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES_DIR / "qps_at_recall.tex").write_text("\n".join(speed_lines) + "\n")
    (TABLES_DIR / "cost_at_095.tex").write_text("\n".join(cost_lines) + "\n")


def main():
    rows = read_raw("part2_ann")
    part1 = read_raw("part1_exact")
    for dataset in DATASETS:
        if any(r["dataset"] == dataset for r in rows):
            figure(rows, part1, dataset)
    write_tables(rows, part1)
    out = merge_results()
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
