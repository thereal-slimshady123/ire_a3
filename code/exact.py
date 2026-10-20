"""Part 1: exact baseline.

Checks FAISS exact search against the neighbours stored in the data file, and
times exact search one query at a time versus in one batch.
"""
import argparse
import sys

import faiss
import numpy as np

from common import load_or_compute_truth, replace_rows, threads
from data import load
from metrics import median_time, recall_at_k

K = 10
SINGLE_QUERY_SAMPLE = 500


def stored_neighbour_check(data, d_exact, train):
    """Recall of the file's neighbours, scored with our exact k-th distance."""
    queries = data["queries"]
    file_ids = data["neighbours"][:, :K].astype(np.int64)
    # Squared distances of the stored neighbours, computed in float64.
    diff = train[file_ids].astype(np.float64) - queries[:, None, :].astype(np.float64)
    file_sqd = (diff ** 2).sum(axis=2)
    return recall_at_k(file_ids, file_sqd, d_exact[:, K - 1], k=K)


def timing_rows(index, queries, dataset):
    rows = []
    n = len(queries)
    # One query at a time over all 1M+ vectors takes tens of minutes for the
    # full half, so the single-query rate is measured on a fixed prefix of it.
    sample = queries[:SINGLE_QUERY_SAMPLE]

    def single_query_loop():
        for q in sample:
            index.search(q[None, :], K)

    with threads(1):
        t = median_time(single_query_loop, repeats=3)
    rows.append(dict(dataset=dataset, index="exact", mode="single query, 1 thread",
                     threads=1, queries=len(sample), seconds=t, qps=len(sample) / t))

    with threads(1):
        t = median_time(lambda: index.search(queries, K), repeats=3)
    rows.append(dict(dataset=dataset, index="exact", mode="batch of all queries, 1 thread",
                     threads=1, queries=n, seconds=t, qps=n / t))

    with threads(faiss.omp_get_max_threads()):
        t = median_time(lambda: index.search(queries, K), repeats=3)
    rows.append(dict(dataset=dataset, index="exact", mode="batch of all queries, all threads",
                     threads=faiss.omp_get_max_threads(), queries=n, seconds=t, qps=n / t))
    return rows


def run(dataset, n_train=None):
    data = load(dataset, n_train=n_train)
    train = data["train"]
    report = data["queries"][data["report"]]
    d_truth, _ = load_or_compute_truth(dataset, train, data["queries"])

    print(f"[{dataset}] vectors={train.shape} queries(report)={report.shape}")
    # The stored neighbours refer to the full dataset, so the check needs all of it.
    stored = None
    if n_train is None:
        stored = stored_neighbour_check(
            {"queries": data["queries"], "neighbours": data["neighbours"]}, d_truth, train)
        print(f"[{dataset}] recall@10 of stored neighbours vs exact: {stored:.6f}")

    index = faiss.IndexFlatL2(train.shape[1])
    index.add(train)
    rows = timing_rows(index, report, dataset)
    for r in rows:
        r["recall_stored_check"] = "" if stored is None else stored
        print(f"[{dataset}] {r['mode']}: {r['qps']:.1f} qps")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["sift", "glove"])
    parser.add_argument("--n-train", type=int, default=None,
                        help="use only the first N indexed vectors (quick mode)")
    args = parser.parse_args()
    all_rows = []
    for name in args.datasets:
        all_rows += run(name, args.n_train)
    replace_rows(all_rows, "part1_exact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
