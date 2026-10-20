import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metrics import recall_at_k  # noqa: E402


def test_perfect_result_scores_one():
    ids = np.arange(10)[None, :]
    d = np.arange(10, dtype=np.float32)[None, :]
    assert recall_at_k(ids, d, np.array([9.0]), k=10) == 1.0


def test_half_correct_scores_half():
    ids = np.arange(10)[None, :]
    d = np.array([[1, 2, 3, 4, 5, 100, 101, 102, 103, 104]], dtype=np.float32)
    assert recall_at_k(ids, d, np.array([5.0]), k=10) == 0.5


def test_ties_at_kth_distance_are_not_errors():
    # The true 10th neighbour is at distance 4; the index returned a different
    # point at the same distance, so the result must still score 1.0.
    ids = np.arange(10)[None, :]
    d = np.full((1, 10), 4.0, dtype=np.float32)
    assert recall_at_k(ids, d, np.array([4.0]), k=10) == 1.0


def test_tie_tolerance_absorbs_float32_rounding():
    ids = np.arange(10)[None, :]
    d = np.full((1, 10), 1e6 * (1 + 3e-6), dtype=np.float32)
    assert recall_at_k(ids, d, np.array([1e6]), k=10) == 1.0


def test_missing_results_are_not_hits():
    ids = np.array([[0, 1, 2, 3, 4, 5, 6, 7, -1, -1]])
    d = np.zeros((1, 10), dtype=np.float32)
    assert recall_at_k(ids, d, np.array([0.0]), k=10) == 0.8


def test_duplicate_ids_are_counted_once():
    ids = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
    d = np.zeros((1, 10), dtype=np.float32)
    assert recall_at_k(ids, d, np.array([0.0]), k=10) == 0.1


def test_mean_over_queries():
    ids = np.vstack([np.arange(10), np.arange(10) + 100])
    d = np.vstack([np.zeros(10), np.full(10, 50.0)]).astype(np.float32)
    assert recall_at_k(ids, d, np.array([0.0, 0.0]), k=10) == 0.5


def test_only_first_k_results_are_scored():
    ids = np.arange(20)[None, :]
    d = np.concatenate([np.zeros(10), np.full(10, 99.0)])[None, :].astype(np.float32)
    assert recall_at_k(ids, d, np.array([0.0]), k=10) == 1.0
