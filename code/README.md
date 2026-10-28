# Benchmarking ANN search: HNSW, IVF-Flat, IVF-PQ

Code for CS4.406 Assignment 3. The report is `../report.pdf`; all numbers, figures and tables it uses are in `../results/`.

## Layout

| File | Part | Purpose |
|---|---|---|
| `data.py` | all | Loads SIFT and GloVe-100 (HDF5), normalises GloVe, defines the tuning/reporting query split |
| `metrics.py` | 1, 2 | Tie-aware recall@10 and median timing |
| `tests/test_metrics.py` | 1 | Unit tests for recall@10 |
| `common.py` | all | Result CSVs, FAISS thread control, exact ground truth (cached in `../data/`) |
| `exact.py` | 1 | Exact baseline, check against stored neighbours, single-query vs batch timing |
| `bench_ann.py` | 2 | Sweeps build and search settings for the three indexes |
| `analyze.py` | 2 | Operating points, trade-off figures, LaTeX tables, merged `results/results.csv` |
| `scaling.py` | 3 | Scaling experiment on SIFT at 100K, 300K and 1M vectors |
| `part4.py` | 4 | Generator and experiment: uniform random vectors, varying dimension |
| `hypothesis.md` | 3, 4 | Hypotheses, committed before the experiments ran |
| `run_all.sh` | all | Regenerates everything |

## Requirements

Python 3.10 or later. Install with `python -m pip install -r requirements.txt`.
A LaTeX installation with `pdflatex` is needed only to build `../report.pdf`.

## Data

Download from ann-benchmarks into `../data/` (the folder is git-ignored):

- `sift-128-euclidean.hdf5` (https://ann-benchmarks.com/sift-128-euclidean.hdf5)
- `glove-100-angular.hdf5` (https://ann-benchmarks.com/glove-100-angular.hdf5)

```
curl -L -o ../data/sift-128-euclidean.hdf5 https://ann-benchmarks.com/sift-128-euclidean.hdf5
curl -L -o ../data/glove-100-angular.hdf5 https://ann-benchmarks.com/glove-100-angular.hdf5
```

## Running

Full reproduction (all data; the sweeps take several hours on a 16-thread laptop):

```
cd code
bash run_all.sh
```

Quick reproduction (first 100,000 indexed vectors, Part 4 with 50,000 vectors, results written to `../results_quick/`, no report build):

```
cd code
bash run_all.sh --quick
```

> **Windows note.** `run_all.sh` uses bash syntax (`set -euo pipefail`, `$(...)`) and requires a POSIX shell. On Windows, run it inside **Git Bash** (ships with Git for Windows) or **WSL**. In Git Bash: open the Git Bash terminal, `cd` to the `code/` directory, and run `bash run_all.sh`.

Individual steps can be run on their own, for example `python bench_ann.py --datasets glove --indexes hnsw`. Each script replaces only the rows it produced, so partial reruns do not discard other results.

## Method notes

- **Recall.** A returned id is a hit if its exact squared distance is no larger than the exact squared distance of the true 10th neighbour (relative tolerance 1e-5). Distances are recomputed from the raw vectors, because IVF-PQ returns approximate distances.
- **Timing.** Speed is queries per second, one query per call, one FAISS thread, median of three repeats. Python call overhead is included and is the same for every index. Exact single-query search is timed on the first 500 queries of the reporting half, because the full half takes too long; the rate is per query, so the comparison holds.
- **Query split.** Operating points are chosen on the first 5,000 queries (the fastest setting with tuning recall at or above the target). Reported recall and speed are measured on the last 5,000.
- **Ground truth.** Computed with FAISS `IndexFlatL2` and checked against the neighbours stored in the files (recall 1.0 for both). Recomputed for subsets, since the stored neighbours refer to the full dataset.
- **GloVe.** Vectors are normalised to unit length, and Euclidean distance is used throughout.
- **Hardware and versions.** Recorded in the report.
