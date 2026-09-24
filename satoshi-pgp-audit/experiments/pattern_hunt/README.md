# Pattern hunt: does the key -> pubkey -> hash160 map leak anything?

Three escalating tests on keys in the puzzle-#71 range [2^70, 2^71), plus a GPU package
for a 100-billion-key run on a local NVIDIA card.

| script | keys | runtime here (4 cores) | result |
|---|---|---|---|
| bigtest.py  | 1 M consecutive + 20 k random | 7 min | null; planted 1% leak caught at 20.4 sigma |
| bigtest2.py | 10 M (multiprocessing) + 30 k random | ~1 h | null; planted 0.5% leak caught at 12.9 sigma |
| bigtest3.py | 1 B streaming (coincurve, 100k chains x 10k) | 93 min | null; see bigtest3_1B_results.txt |
| gpu100b/    | 100 B (CUDA, cupy) | ~1-1.5 h on an RTX 3090 | run on your own machine |

Test families in bigtest3: bit balance, all 70 key bits x 160 address bits, address bit-pair
dependence, RANDU-style 2D/3D lattices, byte/16-bit histograms, runs, neighbour Hamming distance,
hex-digit x key-bit chi-square, gradient-boosted classifiers (which half / quarter / low bit /
middle bit), planted-leak and true-random controls.

Detection floor (5 sigma) scales as 5/sqrt(N): 10 M -> 0.158 %, 1 B -> 0.0158 %, 100 B -> 0.0016 %.
Run with `uv run bigtest3.py` (uv resolves numpy/scipy/scikit-learn/coincurve from the script header).
Set OMP_NUM_THREADS=1 or workers will fight over BLAS threads (3x slower).
