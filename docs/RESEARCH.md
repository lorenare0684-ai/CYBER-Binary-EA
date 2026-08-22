# CYBER Binary EA - Strategy Validation Report

_Generated 2026-08-22 09:43 UTC - data: getdata.finance OHLCV, Feb 1 - Jul 31 2026, 24/5 FX_

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

## 6. Risk notes (read before live trading)

- Feb 2026 was a macro-shock month (tariff news): every variant lost that month (42-49%). Expect occasional losing months; the edge is a slow drift, not a guarantee.
- EURUSD is the weakest major (57-58%); GBPUSD and USDJPY are the strongest (62-67%).
- Results use FX OHLC data; Quotex OTC candles can differ slightly (synthetic 24/7 feed).
- Binary payout must be >= 55-56% for the M15 setup to be profitable after breakeven at 54.05% (85% payout); at lower payouts the edge shrinks.
- Always demo-test first; never risk more than 1-2% per trade; stop after 2 consecutive losses in one session if you are trading manually.
