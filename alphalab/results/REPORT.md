# AlphaLab-lite results

Generated 2026-09-30 19:13 UTC. Horizon 8 bars (M15). Total formulas tried across all symbols: 19,973.

## XAUUSD
bars 236,127 | search 2016-09-05..2023-09-01 | holdout 2023-09-01..2026-09-01 | median round-trip cost 2.8 bp = 0.09 ATR-units of the 8-bar move
Random-entry baseline on holdout (same costs, 5 seeds): annualised Sharpe -4.39 +- 0.44. Anything near this number is cost drag, not signal.
PBO (probability of backtest overfitting, CSCV over top 13 trials, weekly): **0.10**  (0.5 = pure luck, <0.2 is what you want)

| rank | formula | search IC/half-yr | holdout IC/half-yr | holdout trades | holdout Sharpe (ann.) | deflated SR p | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `rsi2` | +0.029 (min -0.006) | -0.006 (min -0.025) | 7493 | -3.02 | 0.000 | fails holdout |
| 2 | `mul(rstd16(hour_cos),rsi2)` | +0.031 (min +0.001) | -0.007 (min -0.036) | 5712 | -2.87 | 0.000 | fails holdout |
| 3 | `runlen` | +0.024 (min -0.001) | -0.005 (min -0.019) | 6026 | -3.31 | 0.000 | fails holdout |
| 4 | `ret_2` | +0.024 (min -0.004) | -0.005 (min -0.019) | 5897 | -3.16 | 0.000 | fails holdout |
| 5 | `body` | +0.021 (min +0.004) | -0.007 (min -0.022) | 6163 | -3.95 | 0.000 | fails holdout |
| 6 | `ret_1` | +0.021 (min +0.004) | -0.006 (min -0.021) | 6155 | -3.97 | 0.000 | fails holdout |
| 7 | `ret_4` | +0.025 (min -0.023) | -0.006 (min -0.018) | 5542 | -4.42 | 0.000 | fails holdout |
| 8 | `barpos` | +0.018 (min +0.005) | -0.010 (min -0.020) | 7603 | -5.79 | 0.000 | fails holdout |
| 9 | `tanh(ret_4)` | +0.025 (min -0.023) | -0.006 (min -0.018) | 6513 | -3.98 | 0.000 | fails holdout |
| 10 | `rmean4(ret_1)` | +0.025 (min -0.024) | -0.005 (min -0.018) | 5309 | -3.78 | 0.000 | fails holdout |
| 11 | `rmean4(barpos)` | +0.017 (min -0.013) | -0.008 (min -0.016) | 6480 | -4.30 | 0.000 | fails holdout |
| 12 | `rsi14` | +0.022 (min -0.023) | -0.005 (min -0.030) | 4879 | -2.98 | 0.000 | fails holdout |
| 13 | `z_20` | +0.020 (min -0.037) | +0.001 (min -0.014) | 5660 | -3.24 | 0.000 | fails holdout |

## BTCUSD
bars 341,340 | search 2017-01-03..2023-10-29 | holdout 2023-10-29..2026-09-30 | median round-trip cost 6.0 bp = 0.06 ATR-units of the 8-bar move
Random-entry baseline on holdout (same costs, 5 seeds): annualised Sharpe -6.70 +- 0.65. Anything near this number is cost drag, not signal.
PBO (probability of backtest overfitting, CSCV over top 9 trials, weekly): **0.07**  (0.5 = pure luck, <0.2 is what you want)

| rank | formula | search IC/half-yr | holdout IC/half-yr | holdout trades | holdout Sharpe (ann.) | deflated SR p | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `add(barpos,z_20)` | +0.079 (min +0.036) | -0.037 (min -0.052) | 9221 | -5.78 | 0.000 | fails holdout |
| 2 | `z_20` | +0.075 (min +0.036) | -0.037 (min -0.055) | 8404 | -5.63 | 0.000 | fails holdout |
| 3 | `rsi14` | +0.071 (min +0.020) | -0.038 (min -0.051) | 7098 | -4.43 | 0.000 | fails holdout |
| 4 | `don_20` | +0.067 (min +0.039) | -0.037 (min -0.061) | 9290 | -6.00 | 0.000 | fails holdout |
| 5 | `sub(rsi2,z_20)` | +0.068 (min +0.039) | +0.035 (min +0.012) | 7936 | -5.90 | 0.000 | fails holdout |
| 6 | `rsi2` | +0.067 (min +0.006) | -0.027 (min -0.049) | 10949 | -7.41 | 0.000 | fails holdout |
| 7 | `don_50` | +0.063 (min +0.021) | -0.035 (min -0.062) | 8052 | -3.98 | 0.000 | fails holdout |
| 8 | `z_50` | +0.064 (min +0.021) | -0.036 (min -0.055) | 6803 | -4.42 | 0.000 | fails holdout |
| 9 | `ret_8` | +0.064 (min +0.015) | -0.027 (min -0.042) | 7541 | -5.10 | 0.000 | fails holdout |

## EURUSD
bars 230,185 | search 2012-11-16..2019-05-27 | holdout 2019-05-27..2022-03-04 | median round-trip cost 1.1 bp = 0.07 ATR-units of the 8-bar move
Random-entry baseline on holdout (same costs, 5 seeds): annualised Sharpe -5.66 +- 0.85. Anything near this number is cost drag, not signal.
PBO (probability of backtest overfitting, CSCV over top 9 trials, weekly): **0.00**  (0.5 = pure luck, <0.2 is what you want)

| rank | formula | search IC/half-yr | holdout IC/half-yr | holdout trades | holdout Sharpe (ann.) | deflated SR p | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `z_20` | +0.048 (min -0.002) | -0.025 (min -0.047) | 5607 | -6.26 | 0.000 | fails holdout |
| 2 | `rsi2` | +0.042 (min -0.002) | -0.027 (min -0.047) | 7374 | -7.20 | 0.000 | fails holdout |
| 3 | `neg(z_20)` | +0.048 (min -0.002) | +0.025 (min -0.023) | 5607 | -3.57 | 0.000 | fails holdout |
| 4 | `ret_8` | +0.043 (min -0.011) | -0.018 (min -0.045) | 4981 | -5.73 | 0.000 | fails holdout |
| 5 | `ret_4` | +0.039 (min -0.006) | -0.019 (min -0.041) | 5419 | -6.63 | 0.000 | fails holdout |
| 6 | `rank200(rsi2)` | +0.039 (min -0.003) | -0.028 (min -0.061) | 7208 | -7.04 | 0.000 | fails holdout |
| 7 | `rsi14` | +0.044 (min +0.000) | -0.025 (min -0.053) | 4797 | -5.83 | 0.000 | fails holdout |
| 8 | `don_20` | +0.042 (min -0.007) | -0.025 (min -0.046) | 6320 | -5.64 | 0.000 | fails holdout |
| 9 | `dmi` | +0.040 (min +0.014) | -0.017 (min -0.049) | 4389 | -4.80 | 0.000 | fails holdout |

## GBPUSD
bars 230,185 | search 2012-11-19..2019-05-27 | holdout 2019-05-27..2022-03-04 | median round-trip cost 1.3 bp = 0.07 ATR-units of the 8-bar move
Random-entry baseline on holdout (same costs, 5 seeds): annualised Sharpe -4.65 +- 0.43. Anything near this number is cost drag, not signal.
PBO (probability of backtest overfitting, CSCV over top 14 trials, weekly): **0.31**  (0.5 = pure luck, <0.2 is what you want)

| rank | formula | search IC/half-yr | holdout IC/half-yr | holdout trades | holdout Sharpe (ann.) | deflated SR p | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `div(rsi14,asia)` | +0.082 (min -0.010) | -0.063 (min -0.121) | 0 | 0.00 | 0.437 | fails holdout |
| 2 | `div(don_50,asia)` | +0.075 (min +0.013) | -0.032 (min -0.099) | 0 | 0.00 | 0.437 | fails holdout |
| 3 | `div(div(rsi14,asia),asia)` | +0.082 (min -0.010) | -0.063 (min -0.121) | 0 | 0.00 | 0.437 | fails holdout |
| 4 | `div(z_20,asia)` | +0.079 (min -0.008) | -0.070 (min -0.119) | 0 | 0.00 | 0.437 | fails holdout |
| 5 | `sub(sub(mul(vr16,div(vr16,asia)),z_20),don_50)` | +0.086 (min -0.003) | +0.069 (min +0.014) | 0 | 0.00 | 0.437 | fails holdout |
| 6 | `sub(lag1(ema_slope),sub(mul(vr16,div(vr16,asia)),z_20))` | +0.088 (min +0.014) | -0.070 (min -0.120) | 0 | 0.00 | 0.437 | fails holdout |
| 7 | `sub(barpos,sub(mul(vr16,div(vr16,asia)),z_20))` | +0.084 (min +0.005) | -0.072 (min -0.132) | 0 | 0.00 | 0.437 | fails holdout |
| 8 | `sub(sub(mul(vr16,div(vr16,asia)),barpos),z_20)` | +0.084 (min +0.005) | +0.072 (min +0.025) | 0 | 0.00 | 0.437 | fails holdout |
| 9 | `sub(barpos,sub(mul(vr16,div(vr16,asia)),ret_8))` | +0.078 (min +0.012) | -0.067 (min -0.122) | 0 | 0.00 | 0.437 | fails holdout |
| 10 | `sub(ret_1,sub(mul(vr16,div(vr16,asia)),z_20))` | +0.082 (min +0.006) | -0.069 (min -0.128) | 0 | 0.00 | 0.437 | fails holdout |
| 11 | `sub(mul(vr16,div(vr16,asia)),z_20)` | +0.081 (min -0.006) | +0.070 (min +0.024) | 0 | 0.00 | 0.437 | fails holdout |
| 12 | `sub(div(asia,asia),z_20)` | +0.079 (min -0.008) | +0.070 (min +0.025) | 0 | 0.00 | 0.437 | fails holdout |
| 13 | `sub(sub(sub(mul(vr16,div(vr16,asia)),z_20),rsi2),barpos)` | +0.083 (min +0.009) | +0.073 (min +0.028) | 0 | 0.00 | 0.437 | fails holdout |
| 14 | `sub(div(vr16,asia),z_20)` | +0.074 (min -0.026) | +0.061 (min +0.005) | 0 | 0.00 | 0.437 | fails holdout |
| 15 | `sub(asia,sub(mul(vr16,div(vr16,asia)),z_20))` | +0.081 (min -0.006) | -0.070 (min -0.128) | 0 | 0.00 | 0.437 | fails holdout |

## USDJPY
bars 230,185 | search 2012-11-19..2019-05-27 | holdout 2019-05-27..2022-03-04 | median round-trip cost 1.1 bp = 0.06 ATR-units of the 8-bar move
Random-entry baseline on holdout (same costs, 5 seeds): annualised Sharpe -5.99 +- 0.44. Anything near this number is cost drag, not signal.
PBO (probability of backtest overfitting, CSCV over top 9 trials, weekly): **0.21**  (0.5 = pure luck, <0.2 is what you want)

| rank | formula | search IC/half-yr | holdout IC/half-yr | holdout trades | holdout Sharpe (ann.) | deflated SR p | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `rsi2` | +0.028 (min +0.013) | -0.029 (min -0.048) | 7346 | -6.58 | 0.000 | fails holdout |
| 2 | `ret_4` | +0.027 (min +0.008) | -0.026 (min -0.063) | 5394 | -5.13 | 0.000 | fails holdout |
| 3 | `ret_8` | +0.031 (min -0.006) | -0.023 (min -0.067) | 4914 | -4.43 | 0.000 | fails holdout |
| 4 | `ret_2` | +0.024 (min +0.009) | -0.023 (min -0.046) | 5755 | -5.70 | 0.000 | fails holdout |
| 5 | `add(ret_4,neg(-0.49))` | +0.027 (min +0.008) | -0.026 (min -0.063) | 5394 | -5.13 | 0.000 | fails holdout |
| 6 | `rank200(ret_2)` | +0.024 (min +0.008) | -0.022 (min -0.042) | 7084 | -5.61 | 0.000 | fails holdout |
| 7 | `barpos` | +0.020 (min +0.003) | -0.020 (min -0.037) | 7442 | -6.19 | 0.000 | fails holdout |
| 8 | `ret_1` | +0.020 (min +0.007) | -0.019 (min -0.030) | 6020 | -5.44 | 0.000 | fails holdout |
| 9 | `max(body,z_20)` | +0.030 (min -0.025) | -0.028 (min -0.078) | 5973 | -4.51 | 0.000 | fails holdout |

## LightGBM walk-forward (all features, monthly retrain, out-of-sample only)

| symbol | OOS rank IC | IC by year | directional acc | trades @z>1 | Sharpe @z>1 | Sharpe @z>1.5 | Sharpe @z>2 | Sharpe @z>2.5 (trades) | top features |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD | +0.0208 | 2017:-0.013 2018:+0.029 2019:+0.010 2020:+0.042 2021:+0.011 2022:+0.035 2023:-0.008 2024:+0.018 2025:+0.032 2026:+0.018 | 51.0% | 14134 | -3.85 | -2.53 | -1.50 | -1.09 (1891) | vr16, ret_480, dom, atr_pct, hour_cos |
| BTCUSD | +0.0468 | 2018:+0.068 2019:+0.091 2020:+0.077 2021:+0.049 2022:+0.037 2023:+0.041 2024:+0.024 2025:+0.011 2026:+0.019 | 51.9% | 20713 | -2.16 | -1.06 | -0.76 | -0.21 (3084) | vr16, atr_pct, ret_480, dom, atr_rank |
| EURUSD | +0.0280 | 2013:+0.092 2014:+0.051 2015:+0.008 2016:+0.035 2017:+0.034 2018:+0.018 2019:+0.044 2020:+0.025 2021:+0.006 2022:-0.000 | 51.1% | 13590 | -2.13 | -1.20 | -0.73 | -0.56 (1926) | vr16, ret_480, dom, atr_pct, hour_cos |
| GBPUSD | +0.0259 | 2013:+0.070 2014:+0.022 2015:+0.055 2016:+0.022 2017:+0.026 2018:+0.025 2019:+0.017 2020:+0.023 2021:+0.013 2022:-0.004 | 50.9% | 12491 | -2.02 | -1.60 | -0.93 | -0.10 (1930) | vr16, ret_480, atr_pct, dom, hour_cos |
| USDJPY | +0.0299 | 2013:+0.090 2014:+0.041 2015:+0.009 2016:+0.012 2017:+0.019 2018:+0.017 2019:+0.061 2020:+0.023 2021:+0.023 2022:+0.110 | 51.0% | 14096 | -2.21 | -1.45 | -0.87 | -0.85 (1746) | vr16, ret_480, atr_pct, dom, atr_rank |

- **No alpha survived the holdout + deflated-Sharpe test. No prop-firm simulation run. This is the honest result.**

Total runtime 11 min.