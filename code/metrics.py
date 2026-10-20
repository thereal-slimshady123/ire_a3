"""Recall@k with tie handling, and median timing."""
import time

import numpy as np


def recall_at_k(found_ids, found_sqdists, true_kth_sqdist, k=10, rel_tol=1e-5):
    """Mean recall@k over queries.

    A returned id counts as a hit when its squared distance is no larger than
    the squared distance of the true k-th neighbour. Points tied with the k-th
    neighbour are therefore hits, and the score does not depend on which of
    several equidistant points an index happened to return.

    found_ids:       (Q, >=k) ids returned by the index, -1 marks a missing result
    found_sqdists:   (Q, >=k) squared distances of found_ids
    true_kth_sqdist: (Q,) squared distance of the exact k-th neighbour
    rel_tol:         relative slack for float32 rounding in distance computation
    """
    found_ids = np.asarray(found_ids)[:, :k]
    found_sqdists = np.asarray(found_sqdists)[:, :k]
    threshold = np.asarray(true_kth_sqdist, dtype=np.float64)[:, None] * (1 + rel_tol)
    hit_mask = (found_ids >= 0) & (found_sqdists <= threshold)
    per_query = [len(set(ids[ok].tolist())) / k for ids, ok in zip(found_ids, hit_mask)]
    return float(np.mean(per_query))


def median_time(fn, repeats=3):
    """Median wall-clock seconds of calling fn() `repeats` times."""
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return float(np.median(times))
