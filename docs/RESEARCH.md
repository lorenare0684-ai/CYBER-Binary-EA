# CYBER Binary EA - Strategy Validation Report

_Generated 2026-08-22 10:14 UTC - data: getdata.finance OHLCV, Feb 1 - Jul 31 2026, 24/5 FX_

## 1. Strategy summary

**NY-Close Seasonal (core rule).** The 17:00 New York fixing generates a reproducible intraday flow pattern in FX: a dip in the hour before the fix (20:00-21:00 UTC) and a rally into/after the fix (21:00-23:00 UTC).

| Rule | Window (UTC) | Direction | Entry | Expiry |
|------|--------------|-----------|-------|--------|
| NY-close dip | 20:00 - 21:00 | PUT | bar close | 4 bars (M15) |
| NY-close rally | 21:00 - 23:00 | CALL | bar close | 4 bars (M15) |

Cooldown 2 bars, entry at signal-bar close, outcome = close of bar i+4 vs close of bar i (equal = scratch, excluded).

## 2. In-sample results (Feb - Jul 2026)

| Instrument | Expiry | Trades | Wins | Losses | Accuracy | Net/1.0 stake (85% payout) | PF | MaxDD |
|------------|--------|--------|------|--------|----------|------------------------------|----|-------|
| GBPUSD M15 | 1 h | 776 | 513 | 258 | **66.54%** | +178.05 | 1.69 | -22.00 |
| USDJPY M15 | 1 h | 776 | 518 | 255 | **67.01%** | +185.30 | 1.727 | -40.75 |
| EURUSD M15 | 1 h | 776 | 439 | 330 | **57.09%** | +43.15 | 1.131 | -27.70 |
| GBPUSD M5 | 30 m | 2331 | 1433 | 880 | **61.95%** | +338.05 | 1.384 | -89.05 |
| USDJPY M5 | 30 m | 2331 | 1373 | 937 | **59.44%** | +230.05 | 1.246 | -58.65 |
| EURUSD M5 | 30 m | 2331 | 1339 | 959 | **58.27%** | +179.15 | 1.187 | -55.30 |

## 3. Walk-forward (same parameters, untouched windows)

| Instrument | Feb-Apr | May-Jul (out-of-sample) |
|------------|---------|-------------------------|
| GBPUSD M15 | 61.0% (n=385) | **72.9%** (n=380) |
| USDJPY M15 | 58.2% (n=385) | **75.7%** (n=382) |
| EURUSD M15 | 55.8% (n=382) | **59.3%** (n=381) |
| GBPUSD M5 | 56.5% (n=1152) | **67.5%** (n=1146) |
| USDJPY M5 | 54.6% (n=1166) | **64.4%** (n=1140) |
| EURUSD M5 | 56.3% (n=1149) | **60.6%** (n=1135) |

## 4. Monthly stability (M15)

| Month | GBPUSD | USDJPY | EURUSD |
|-------|--------|--------|--------|
| 26-02 | 49.2% | 42.4% | 45.8% |
| 26-03 | 54.4% | 64.0% | 51.5% |
| 26-04 | 78.0% | 65.9% | 67.4% |
| 26-05 | 77.8% | 80.2% | 62.7% |
| 26-06 | 66.7% | 72.0% | 49.2% |
| 26-07 | 69.7% | 74.2% | 62.1% |

## 5. Long-history regime check (GBPUSD, 25 years)

The effect is regime-dependent: weak before ~2015, consistently present since 2018.

| Period | GBPUSD 1h, CALL(21-23)/PUT(20-21), k=1 | GBPUSD 30m, k=2 |
|--------|-----------------------------------------|-----------------|
| 2001-2011 | 53.3% (n=18391) | 53.3% (n=36546) |
| 2012-2017 | 54.8% (n=11170) | 56.0% (n=22359) |
| 2018-2026 | 57.2% (n=6570) | 59.2% (n=13159) |

## 6. Micro-Fix strategy (flagship, 85%+)

**Mechanism.** The 30 minutes before the 17:00 New York CME/futures settlement show a reproducible dip (16:35-16:50 NY) followed by a rally into the electronic close (17:50-18:00 NY). Windows are anchored to NY local time with automatic US-DST handling (validated: 0 mismatches vs America/New_York over 2020-2029).

| Variant | Trades | Accuracy | PF | Feb-Apr | May-Jul (OOS) |
|---------|--------|----------|----|---------|---------------|
| PUT 16:35-16:50 NY, 25-min expiry, no Fridays, 4 assets (default) | 1659 | **86.62%** | 5.5 | 82.0% (n=829) | **91.2%** (n=830) |
| Flagship + skip Mondays | 1244 | **87.7%** | 6.06 | 83.6% (n=621) | **91.8%** (n=623) |
| PUT + CALL (17:50-18:00 NY, 10-min), no Fridays | 3186 | **80.57%** | 3.52 | 77.5% (n=1589) | **83.6%** (n=1597) |
| 5 assets (incl. AUDUSD) | 2074 | **84.67%** | 4.69 | 81.5% (n=1036) | **87.9%** (n=1038) |
| PUT, all days, 4 assets | 2059 | **83.63%** | 4.34 | 81.3% (n=1021) | **85.9%** (n=1038) |

Monthly accuracy (flagship): 02:87% | 03:73% | 04:86% | 05:94% | 06:91% | 07:89%

Per pair (flagship, k=5): EURJPY: 90.36% (n=415) | GBPUSD: 87.41% (n=413) | USDJPY: 85.54% (n=415) | EURGBP: 83.17% (n=416) | AUDUSD: 76.87% (n=415) | EURUSD: 71.95% (n=410)

**Signal frequency:** 4 signals per asset per day (16:35, 16:40, 16:45, 16:50 NY bars) = 16 signals/day on the 4-asset flagship, ~16 per day, Mon-Thu only.

## 7. Long-history reality check (2000-2018, HistData M1)

**What was tested.** The exact flagship Micro-Fix rule (PUT entry at NY
16:40/16:45/16:50/16:55, +25-min expiry, Fridays skipped, Sundays excluded)
on 19 years of 1-minute HistData (2000-2018) for 6 pairs, plus a full scan of
every 15-minute PUT window in NY 15:00-18:00 to catch any era-dependent shift
of the window. DST was handled with America/New_York zoneinfo (correct
pre-2007 rules). The 1-minute methodology was validated by reproducing the
2026 M5 results (EURUSD 70.9% vs 72.0%, GBPUSD 86.8% vs 87.4%, EURJPY 90.1%
vs 90.4%).

| Pair | 2000-2006 | 2007-2012 | 2013-2018 | **2026** |
|------|-----------|-----------|-----------|----------|
| EURUSD | 51.1% (n=2929) | 49.6% (n=4217) | 51.1% (n=4527) | 70.9% |
| GBPUSD | 50.4% (n=2362) | 49.2% (n=3948) | 52.3% (n=4532) | 86.8% |
| USDJPY | 52.3% (n=3735) | 55.1% (n=4098) | 53.5% (n=4544) | 85.3% |
| EURJPY | 52.9% (n=3383) | 53.2% (n=4755) | 53.3% (n=4560) | 90.1% |
| EURGBP | 51.8% (n=1963) | 51.3% (n=3540) | 54.7% (n=4412) | 83.2% |
| AUDUSD | 51.0% (n=2051) | 53.1% (n=4305) | 51.2% (n=4533) | 76.7% |

**Finding.** Across all 19 years and all 6 pairs the flagship rule sits at
49-55% - no edge. The era scan confirms this is not a shifted window: the
best 15-minute window in NY 15:00-18:00 for any era tops out at ~48-54%.
The 80-90% numbers are a **recent phenomenon** visible in the 2026 dataset
only. 2019-2025 cannot be checked from this environment (no reachable
1-minute archive; the sandbox egress is restricted to GitHub/PyPI).

By contrast, the coarser legacy rule (M15/1h, 1-hour expiry) does show a
modest but persistent historical edge on 25 years of GBPUSD from the same
provider: 53.3% (2001-2011) -> 54.8% (2012-2017) -> 57.2% (2018-2026),
i.e. the NY-close effect exists at coarse scale for decades but has been
strengthening in recent years.

**What this means.** Either (a) the micro-fix edge genuinely emerged in the
last few years (new fix/benchmark flows), or (b) part of the 2026 magnitude
is a data-provider artifact - 85-90% on a 25-minute horizon is unusually
high for FX microstructure and needs independent confirmation. Both
possibilities lead to the same action: **validate on your actual Quotex OTC
feed (demo) or a second data provider for several weeks before risking real
money, and do not extrapolate the 86.6% as a long-run expectation.**

Reproduce: `tools/validate_long_history.py` (data: sparse-clone
`riknv/fx-m1-data`, dirs eurusd/gbpusd/usdjpy/eurjpy/eurgbp/audusd).
Results: `backtest/out/long_history_microfix.csv` (per pair-year),
`backtest/out/long_history_scan.csv` (best window per era).

## 8. Risk notes (read before live trading)

- Feb 2026 was a macro-shock month (tariff news): the legacy M15 seasonal variants
  lost that month (42-49%), while the Micro-Fix strategy stayed profitable (79%).
- The flagship Micro-Fix edge is **regime-dependent**: it is strong in the 2026
  sample (71-90%) but absent in 2000-2018 HistData (49-55%). Demo-validate on
  the Quotex OTC feed and re-measure monthly; expect the edge to weaken or
  shift if market microstructure changes.
- EURUSD is the weakest major (57-58%); GBPUSD and USDJPY are the strongest (62-67%).
- Results use FX OHLC data; Quotex OTC candles can differ slightly (synthetic 24/7 feed).
- Binary payout must be >= 55-56% for the M15 setup to be profitable after breakeven at 54.05% (85% payout); at lower payouts the edge shrinks.
- Always demo-test first; never risk more than 1-2% per trade; stop after 2 consecutive losses in one session if you are trading manually.
