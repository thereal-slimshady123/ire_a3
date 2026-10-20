"""Shared helpers: result files, FAISS thread control, ground truth cache."""
import csv
from contextlib import contextmanager

import faiss
import numpy as np

from data import DATA_DIR, ROOT

RESULTS_DIR = ROOT / "results"
RAW_DIR = RESULTS_DIR / "raw"
FIGURES_DIR = RESULTS_DIR / "figures"
TUNE_QUERIES = 5000


@contextmanager
def threads(n):
    old = faiss.omp_get_max_threads()
    faiss.omp_set_num_threads(n)
    try:
        yield
    finally:
        faiss.omp_set_num_threads(old)


def write_rows(rows, name):
    """Write one experiment's rows to results/raw/<name>.csv."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.csv"
    if not rows:
        return path
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def replace_rows(rows, name, key_fields=("dataset", "index")):
    """Swap the rows for these keys into results/raw/<name>.csv, keeping the rest.

    Lets one dataset or index be re-run without discarding the others.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.csv"
    new = [{k: str(v) for k, v in r.items()} for r in rows]
    new_keys = {tuple(r[k] for k in key_fields) for r in new}
    old = []
    if path.exists():
        with open(path, newline="") as f:
            old = [r for r in csv.DictReader(f)
                   if tuple(r[k] for k in key_fields) not in new_keys]
    merged = old + new
    if not merged:
        return path
    fieldnames = []
    for r in merged:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(merged)
    return path


def exact_ground_truth(train, queries, k=10):
    """Exact k-NN with FAISS. Returns squared distances and ids, both (Q, k)."""
    index = faiss.IndexFlatL2(train.shape[1])
    index.add(train)
    d, i = index.search(queries, k)
    return d, i


def index_bytes(index):
    return int(faiss.serialize_index(index).nbytes)


def cache_path(name):
    return DATA_DIR / f"{name}.npz"


def load_or_compute_truth(name, train, queries, k=10):
    """Exact neighbours cached under data/ so later experiments reuse them."""
    path = cache_path(f"truth_{name}_{train.shape[0]}")
    if path.exists():
        z = np.load(path)
        return z["d"], z["i"]
    d, i = exact_ground_truth(train, queries, k)
    np.savez(path, d=d, i=i)
    return d, i
