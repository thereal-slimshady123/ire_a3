"""Part 4: a failure mode on data we generate ourselves.

Property varied: the dimension d of i.i.d. uniform vectors in [0, 1]^d.
Everything else is held fixed: N, number of queries, generator seed, index
build settings and the search-time grids. Hypotheses are in hypothesis.md.

Dimension settings: 16, 64, 256, plus 128 as the control.
"""
import argparse
import sys

import faiss
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from bench_ann import K, make_index, set_search, time_single_queries  # noqa: E402
from common import FIGURES_DIR, RESULTS_DIR, exact_sqdists, index_bytes, replace_rows, threads  # noqa: E402
from metrics import median_time, recall_at_k  # noqa: E402

N = 200_000
N_QUERIES = 1000
DIMS = [16, 64, 128, 256]
CONTROL_DIM = 128
SEED = 20261020
BUILD = {"hnsw": dict(M=16), "ivfflat": dict(nlist=1024), "ivfpq": dict(nlist=1024, m=16)}
SEARCH = {"hnsw": ("efSearch", [16, 32, 64, 128, 256]),
          "ivfflat": ("nprobe", [1, 4, 16, 64]),
          "ivfpq": ("nprobe", [1, 4, 16, 64])}
LABEL = {"hnsw": "HNSW (M=16)", "ivfflat": "IVF-Flat (nlist=1024)", "ivfpq": "IVF-PQ (nlist=1024, m=16)"}
TABLES_DIR = RESULTS_DIR / "tables"


def generate(dim, n=N, n_queries=N_QUERIES):
    """Uniform [0, 1]^dim vectors. A separate seeded stream is used for the queries."""
    base = np.random.default_rng([SEED, dim]).random((n, dim), dtype=np.float32)
    queries = np.random.default_rng([SEED + 1, dim]).random((n_queries, dim), dtype=np.float32)
    return base, queries


def relative_contrast(base, queries, chunk=50):
    """Median over queries of mean distance to all points / distance to the nearest point."""
    values = []
    base64 = base.astype(np.float64)
    base_sq = (base64 ** 2).sum(1)
    for start in range(0, len(queries), chunk):
        q = queries[start:start + chunk].astype(np.float64)
        d2 = (q ** 2).sum(1)[:, None] + base_sq[None, :] - 2.0 * q @ base64.T
        dist = np.sqrt(np.maximum(d2, 0.0))
        values.append(dist.mean(axis=1) / dist.min(axis=1))
    return float(np.median(np.concatenate(values)))


def run(n=N, n_queries=N_QUERIES, dims=DIMS):
    rows = []
    for dim in dims:
        base, queries = generate(dim, n, n_queries)
        gt_index = faiss.IndexFlatL2(dim)
        gt_index.add(base)
        gt_d, _ = gt_index.search(queries, K)
        kth = gt_d[:, K - 1]
        rc = relative_contrast(base, queries)
        print(f"[dim={dim}] relative contrast (median) = {rc:.4f}", flush=True)
        for kind in ("hnsw", "ivfflat", "ivfpq"):
            index, quantizer = make_index(kind, dim, BUILD[kind])
            if kind != "hnsw":
                index.train(base)
            index.add(base)
            size = index_bytes(index)
            param, values = SEARCH[kind]
            for value in values:
                set_search(index, kind, value)
                _, ids = index.search(queries, K)
                d = exact_sqdists(base, queries, ids)
                recall = recall_at_k(ids, d, kth, K)
                with threads(1):
                    seconds = median_time(lambda: time_single_queries(index, queries), 3)
                rows.append(dict(
                    property="dimension", setting=dim, control=int(dim == CONTROL_DIM),
                    index=kind, build=";".join(f"{k}={v}" for k, v in BUILD[kind].items()),
                    param=param, value=value, n_vectors=n, n_queries=n_queries,
                    recall=recall, qps=n_queries / seconds, relative_contrast=rc,
                    index_bytes=size, bytes_per_vector=size / n,
                ))
                print(f"[dim={dim}] {kind} {param}={value} recall={recall:.4f} "
                      f"qps={n_queries / seconds:.0f}", flush=True)
    replace_rows(rows, "part4_dimension", key_fields=("property", "setting", "index"))
    return rows


def fixed_budget(rows, index, param_value):
    out = {}
    for r in rows:
        if r["index"] == index and r["value"] == param_value:
            out[r["setting"]] = (r["recall"], r["qps"], r["relative_contrast"])
    return out


def figure_and_table(rows):
    dims = sorted({r["setting"] for r in rows})
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
    for ax, kind in zip(axes, ("hnsw", "ivfflat", "ivfpq")):
        for dim in dims:
            pts = sorted([(r["qps"], r["recall"]) for r in rows
                          if r["index"] == kind and r["setting"] == dim])
            style = "--" if dim == CONTROL_DIM else "-"
            ax.plot([p[0] for p in pts], [p[1] for p in pts], style, marker="o",
                    label=f"d={dim}" + (" (control)" if dim == CONTROL_DIM else ""))
        ax.set_xscale("log")
        ax.set_title(LABEL[kind])
        ax.set_xlabel("queries per second (log scale)")
        ax.grid(True, which="both", alpha=0.3)
    axes[0].set_ylabel("recall@10")
    axes[-1].legend(loc="lower left")
    fig.suptitle(f"Uniform random vectors, N={N:,}: recall versus speed as dimension grows")
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "part4_dimension.png", dpi=160)
    plt.close(fig)

    budgets = {"hnsw": 64, "ivfflat": 16, "ivfpq": 16}
    lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"$d$ & Relative contrast & HNSW recall (efSearch=64) & IVF-Flat recall (nprobe=16) & "
        r"IVF-PQ recall (nprobe=16) & Exact NN distance / mean \\",
        r"\midrule",
    ]
    rc_by_dim = {r["setting"]: r["relative_contrast"] for r in rows}
    per_index = {kind: fixed_budget(rows, kind, budgets[kind]) for kind in budgets}
    for dim in dims:
        recalls = [per_index[k][dim][0] for k in ("hnsw", "ivfflat", "ivfpq")]
        label = f"{dim} (control)" if dim == CONTROL_DIM else f"{dim}"
        lines.append(f"{label} & {rc_by_dim[dim]:.3f} & {recalls[0]:.3f} & {recalls[1]:.3f} & "
                     f"{recalls[2]:.3f} & {1 / rc_by_dim[dim]:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "part4.tex").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=N)
    parser.add_argument("--n-queries", type=int, default=N_QUERIES)
    args = parser.parse_args()
    rows = run(args.n, args.n_queries)
    figure_and_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
