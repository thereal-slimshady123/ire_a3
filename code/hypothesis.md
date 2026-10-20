# Hypotheses

Written and committed before the experiments were run.

## Part 3: Scaling on SIFT (100K, 300K, 1M vectors)

Question: how does the cost (queries per second) of reaching recall@10 = 0.95 change with the number of indexed vectors N, for exact search, HNSW and IVF-Flat?

Settings: HNSW with M = 16, efConstruction = 200; IVF-Flat with nlist = round(4 * sqrt(N)), so nlist grows with N; nprobe swept. Ground truth is recomputed for each N, since the stored neighbours refer to the full 1M set.

H1 (exact). Each query reads all N vectors, so QPS is proportional to 1/N. The log-log slope of QPS against N should be close to -1.

H2 (HNSW). Greedy graph search visits a number of nodes that grows roughly with log N at fixed recall, so QPS should fall far more slowly than 1/N. Expected log-log slope between -0.1 and -0.4.

H3 (IVF-Flat). With nlist proportional to sqrt(N), each list holds about sqrt(N)/4 vectors. If the nprobe needed for recall 0.95 stays roughly constant, the vectors scanned per query grow as nprobe * N / nlist, which is proportional to sqrt(N). Expected log-log slope near -0.5. A slope near -1 would mean the required nprobe grows with N as well.

What would refute the mechanism: an HNSW slope near -1, or an IVF-Flat slope far from -0.5 while the nprobe chosen on the tuning half stays constant.

## Part 4: Dimension of uniform random vectors (own data)

Property varied: the dimension d of i.i.d. uniform vectors in [0, 1]^d. Settings: d = 16, 64, 256. Control: d = 128, run through the identical pipeline. Held fixed: N = 200,000 indexed vectors, 1,000 queries, the generator seed, HNSW with M = 16 and efConstruction = 200, IVF with nlist = 1024, PQ with m = 16 sub-quantizers at 8 bits, and the search grids efSearch in {16, 32, 64, 128, 256} and nprobe in {1, 4, 16, 64}.

Mechanism. As d grows, squared distances between random points concentrate around their mean. The nearest neighbour then becomes only slightly closer than a typical point. The relative contrast (mean distance divided by nearest-neighbour distance) falls toward 1, so small errors in the index's search path are more likely to return a point that is not among the true top 10.

H1. The relative contrast decreases monotonically with d over 16, 64, 128, 256.

H2. At a fixed search budget, recall@10 falls as d increases for all three indexes. The control (d = 128) lies between its neighbours and shows no special behaviour.

H3. At a fixed budget, IVF-Flat and IVF-PQ lose more recall than HNSW. Reason: k-means cells in high dimension are less compact relative to the nearest-neighbour distance, so a true neighbour is more often outside the nprobe cells that were searched. HNSW instead widens its search with efSearch as it goes, so it can keep finding neighbours when the budget is fixed.

What would refute this: recall that does not fall with d, or HNSW falling faster than the IVF indexes at the same budget.

Not tested: the choice of N, non-uniform distributions, clustered or near-duplicate data, and other build settings.
