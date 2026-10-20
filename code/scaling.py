"""Part 3 (Scaling): cost of reaching recall@10 = 0.95 as N grows, on SIFT.

Settings are fixed in hypothesis.md: HNSW with M = 16, IVF-Flat with
nlist = round(4 * sqrt(N)). The operating point is chosen on the tuning half and
reported on the reporting half. Ground truth is recomputed for each N.
"""
import argparse
import math
import sys

import faiss
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from bench_ann import K, sweep  # noqa: E402
from common import FIGURES_DIR, RESULTS_DIR, load_or_compute_truth, threads, replace_rows  # noqa: E402
from data import load  # noqa: E402
from metrics import median_time  # noqa: E402

SIZES = [100_000, 300_000, 1_000_000]
TARGET = 0.95
SINGLE_QUERY_SAMPLE = 500
TABLES_DIR = RESULTS_DIR / "tables"


def exact_qps(train, queries):
    index = faiss.IndexFlatL2(train.shape[1])
    index.add(train)
    sample = queries[:SINGLE_QUERY_SAMPLE]
    with threads(1):
        seconds = median_time(lambda: [index.search(q[None, :], K) for q in sample], 3)
    return len(sample) / seconds, seconds


def best_point(rows, n, index):
    tune = {(r["build"], r["value"]): r for r in rows
            if r["n_vectors"] == n and r["index"] == index and r["split"] == "tune"}
    report = {(r["build"], r["value"]): r for r in rows
              if r["n_vectors"] == n and r["index"] == index and r["split"] == "report"}
    eligible = [k for k, r in tune.items() if r["recall"] >= TARGET]
    if not eligible:
        return None
    best = max(eligible, key=lambda k: tune[k]["qps"])
    return report[best]


def run(sizes):
    rows = []
    for n in sizes:
        data = load("sift", n_train=n)
        truth_d, _ = load_or_compute_truth("sift", data["train"], data["queries"])
        qps, seconds = exact_qps(data["train"], data["queries"][data["report"]])
        rows.append(dict(dataset="sift", index="exact", build="none", param="", value=0,
                         split="report", n_vectors=n, recall=1.0, qps=qps,
                         seconds_total=seconds, build_seconds=0.0, index_bytes=0,
                         bytes_per_vector=0.0))
        print(f"[scaling N={n}] exact: {qps:.1f} qps", flush=True)
        nlist = round(4 * math.sqrt(n))
        for kind, builds in (("hnsw", [dict(M=16)]), ("ivfflat", [dict(nlist=nlist)])):
            new = sweep("sift", kind, data, truth_d, builds=builds)
            for r in new:
                r["n_vectors"] = n
            rows += new
        replace_rows(rows, "part3_scaling", key_fields=("n_vectors", "index"))
    return rows


def slope(xs, ys):
    return float(np.polyfit(np.log(xs), np.log(ys), 1)[0])


def figure_and_table(rows):
    sizes = sorted({int(r["n_vectors"]) for r in rows})
    series = {"Exact": "exact", "HNSW (M=16)": "hnsw", "IVF-Flat": "ivfflat"}
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    lines = [
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Index & $N$ & QPS @ recall 0.95 & Slope vs $N$ \\",
        r"\midrule",
    ]
    for label, kind in series.items():
        xs, ys = [], []
        for n in sizes:
            if kind == "exact":
                e = [r for r in rows if r["index"] == "exact" and int(r["n_vectors"]) == n]
                qps = e[0]["qps"] if e else None
            else:
                p = best_point(rows, n, kind)
                qps = p["qps"] if p else None
            if qps is not None:
                xs.append(n)
                ys.append(qps)
        if len(xs) >= 2:
            s = slope(xs, ys)
            ax.plot(xs, ys, marker="o", label=f"{label} (slope {s:.2f})")
            for n, y in zip(xs, ys):
                lines.append(f"{label} & {n:,} & {y:.1f} & {s:.2f} \\\\")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("N (SIFT vectors indexed, log scale)")
    ax.set_ylabel("queries per second at recall@10 = 0.95 (log scale)")
    ax.set_title("SIFT: cost of 0.95 recall versus dataset size")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "scaling_sift.png", dpi=160)
    plt.close(fig)
    lines += [r"\bottomrule", r"\end{tabular}"]
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "scaling.tex").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=SIZES)
    args = parser.parse_args()
    rows = run(args.sizes)
    figure_and_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
