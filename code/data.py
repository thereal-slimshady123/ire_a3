"""Loading of the SIFT and GloVe-100 files from ann-benchmarks."""
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FILES = {
    "sift": "sift-128-euclidean.hdf5",
    "glove": "glove-100-angular.hdf5",
}
TUNE = slice(0, 5000)
REPORT = slice(5000, 10000)


def normalise(x):
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def load(name, n_train=None):
    """Return the indexed vectors and both query halves.

    GloVe vectors are normalised so that Euclidean distance ranks them the
    same way as angular distance. The stored neighbours are kept as given.
    """
    with h5py.File(DATA_DIR / FILES[name], "r") as f:
        train_ds = f["train"]
        n = train_ds.shape[0] if n_train is None else n_train
        train = np.asarray(train_ds[:n], dtype=np.float32)
        test = np.asarray(f["test"], dtype=np.float32)
        neighbours = np.asarray(f["neighbors"])
    if name == "glove":
        train = normalise(train)
        test = normalise(test)
    return {
        "train": train,
        "queries": test,
        "neighbours": neighbours,
        "tune": TUNE,
        "report": REPORT,
    }
