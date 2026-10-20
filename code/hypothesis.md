# Hypotheses

Written and committed before the experiments were run.

## Part 3: Scaling on SIFT (100K, 300K, 1M vectors)

Question: how does the cost (queries per second) of reaching recall@10 = 0.95 change with the number of indexed vectors N, for exact search, HNSW and IVF-Flat?

Settings: HNSW with M = 16, efConstruction = 200; IVF-Flat with nlist = round(4 * sqrt(N)), so nlist grows with N; nprobe swept. Ground truth is recomputed for each N, since the stored neighbours refer to the full 1M set.

H1 (exact). Each query reads all N vectors, so QPS is proportional to 1/N. The log-log slope of QPS against N should be close to -1.

H2 (HNSW). Greedy graph search visits a number of nodes that grows roughly with log N at fixed recall, so QPS should fall far more slowly than 1/N. Expected log-log slope between -0.1 and -0.4.

H3 (IVF-Flat). With nlist proportional to sqrt(N), each list holds about sqrt(N)/4 vectors. If the nprobe needed for recall 0.95 stays roughly constant, the vectors scanned per query grow as nprobe * N / nlist, which is proportional to sqrt(N). Expected log-log slope near -0.5. A slope near -1 would mean the required nprobe grows with N as well.

What would refute the mechanism: an HNSW slope near -1, or an IVF-Flat slope far from -0.5 while the nprobe chosen on the tuning half stays constant.
