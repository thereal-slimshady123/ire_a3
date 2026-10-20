"""Part 2: sweep build and search settings for HNSW, IVF-Flat and IVF-PQ.

Each row is one (index, build setting, search setting, query split). Recall is
computed with batch search; speed is measured one query at a time on one thread.
Both query halves are measured so that operating points can be chosen on the
tuning half and reported on the reporting half.
"""
import argparse
import sys
import time

import faiss

from common import index_bytes, load_or_compute_truth, replace_rows, threads
from data import load
from metrics import median_time, recall_at_k

K = 10
HNSW_M = [8, 16, 32]
HNSW_EF_CONSTRUCTION = 200
HNSW_EF_SEARCH = [16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512]
IVF_NLIST = [1024, 4096]
IVF_NPROBE = [1, 2, 4, 8, 16, 32, 64, 128, 256]
PQ_M = {"sift": [16, 32], "glove": [10, 20]}
PQ_NBITS = 8


def make_index(kind, dim, build):
    """Return (index, quantizer). The quantizer must stay referenced."""
    if kind == "hnsw":
        index = faiss.IndexHNSWFlat(dim, build["M"])
        index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
        return index, None
    quantizer = faiss.IndexFlatL2(dim)
    if kind == "ivfflat":
        return faiss.IndexIVFFlat(quantizer, dim, build["nlist"]), quantizer
    if kind == "ivfpq":
        return faiss.IndexIVFPQ(quantizer, dim, build["nlist"], build["m"], PQ_NBITS), quantizer
    raise ValueError(kind)


def time_single_queries(index, queries):
    """One search call per query, as a serving system would issue them."""
    for q in queries:
        index.search(q[None, :], K)


def set_search(index, kind, value):
    if kind == "hnsw":
        index.hnsw.efSearch = value
    else:
        index.nprobe = value


def build_configs(kind, dataset):
    if kind == "hnsw":
        return [dict(M=m) for m in HNSW_M]
    if kind == "ivfflat":
        return [dict(nlist=n) for n in IVF_NLIST]
    return [dict(nlist=n, m=m) for n in IVF_NLIST for m in PQ_M[dataset]]


def search_params(kind):
    return ("efSearch", HNSW_EF_SEARCH) if kind == "hnsw" else ("nprobe", IVF_NPROBE)


def build_label(build):
    return ";".join(f"{k}={v}" for k, v in build.items())


def sweep(dataset, kind, data, truth_d, builds=None):
    train = data["train"]
    queries = data["queries"]
    splits = {"tune": queries[data["tune"]], "report": queries[data["report"]]}
    kth = {"tune": truth_d[data["tune"]][:, K - 1], "report": truth_d[data["report"]][:, K - 1]}
    param_name, values = search_params(kind)
    rows = []
    for build in builds or build_configs(kind, dataset):
        t0 = time.perf_counter()
        index, quantizer = make_index(kind, train.shape[1], build)
        if kind != "hnsw":
            index.train(train)
        index.add(train)
        build_s = time.perf_counter() - t0
        size = index_bytes(index)
        print(f"[{dataset}] {kind} {build_label(build)} built in {build_s:.1f}s, "
              f"{size / 2**20:.1f} MiB", flush=True)
        for value in values:
            set_search(index, kind, value)
            for split, q in splits.items():
                dists, ids = index.search(q, K)
                recall = recall_at_k(ids, dists, kth[split], K)
                with threads(1):
                    seconds = median_time(lambda: time_single_queries(index, q), 3)
                qps = len(q) / seconds
                rows.append(dict(
                    dataset=dataset, index=kind, build=build_label(build),
                    param=param_name, value=value, split=split,
                    n_vectors=len(train), recall=recall, qps=qps,
                    seconds_total=seconds, build_seconds=build_s,
                    index_bytes=size, bytes_per_vector=size / len(train),
                ))
            r = rows[-1]
            print(f"[{dataset}] {kind} {build_label(build)} {param_name}={value} "
                  f"recall(report)={r['recall']:.4f} qps={r['qps']:.0f}", flush=True)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["sift", "glove"])
    parser.add_argument("--indexes", nargs="+", default=["hnsw", "ivfflat", "ivfpq"])
    parser.add_argument("--n-train", type=int, default=None,
                        help="use only the first N indexed vectors (quick mode)")
    parser.add_argument("--name", default="part2_ann")
    args = parser.parse_args()

    for dataset in args.datasets:
        data = load(dataset, n_train=args.n_train)
        truth_d, _ = load_or_compute_truth(dataset, data["train"], data["queries"])
        for kind in args.indexes:
            rows = sweep(dataset, kind, data, truth_d)
            replace_rows(rows, args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
