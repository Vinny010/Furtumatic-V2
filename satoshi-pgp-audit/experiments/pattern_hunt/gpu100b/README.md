# 100-billion-key pattern test — for YOUR machine (GPU)

This runs on your Windows PC with an NVIDIA card. It is the same test family as
`bigtest3.py` (the 1-billion CPU run) but generates keys → pubkeys → hash160 on the
GPU and only ships compact statistics back to Python.

## What it measures (all streaming, nothing stored)
1. Address bit balance (160 counters)
2. Key-bit × address-bit dependence, all 70 key bits × 160 address bits (11,200 z-scores)
3. Address bit-pair dependence (12,720 pairs)
4. RANDU-style lattice: 2D and 3D histograms of consecutive address bytes
5. Byte / 16-bit-pair histograms, runs-per-address, neighbour Hamming distance k vs k+1
6. Hex-digit × key-bit chi-square (which half / quarter / eighth of the range)
7. Planted-leak control (must fire) and true-random control (must not fire)

## Detection floor
| keys   | 5-sigma floor on any bias |
|--------|---------------------------|
| 10 M   | 0.158 %                   |
| 1 B    | 0.0158 %                  |
| 100 B  | 0.0016 %                  |

A bias smaller than a few percent cannot be turned into a search speed-up anyway
(you still have to test ~all the keys), so 100B only tightens the "nothing there" bound.

## Setup (Windows, PowerShell)
```
winget install Python.Python.3.11
pip install numpy scipy scikit-learn cupy-cuda12x
```
(CUDA 12 driver needed: any recent NVIDIA driver has it. RTX 3090 / 5070 Ti both fine.)

## Run
```
python gpu_pattern_test.py --keys 100e9 --range 71
```
Expected speed: ~20–40 M keys/s on a 3090 (kernel is a plain double-and-add + SHA-256 + RIPEMD-160,
not BitCrack-optimised). 100B ≈ 1–1.5 hours. Use `--keys 1e9` first to check everything runs (~1 min).

Output is a text report identical in layout to `bigtest3.log`. Send it back to me (any session) and I
will read it against the controls. Anything above 5 sigma that is NOT in the planted-leak line is a finding.
