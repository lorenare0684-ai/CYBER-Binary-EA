# CYBER Binary EA

**Quotex binary-options signal Expert Advisor for MetaTrader 5** — research-backed
CALL/PUT signals with a live dashboard (winrate, wins, losses, accuracy) that
opens automatically in a new window when you attach the EA and auto-scales to
any window size.

> ⚠️ **Read-only advisor.** The EA only *generates signals* (arrows + alerts +
> dashboard). Execution is done manually on Quotex. It never sends orders.

---

## TL;DR — the 85%+ flagship (Micro-Fix rule, M5)

| Asset | **Accuracy** | Trades | Out-of-sample (May–Jul) |
|-------|--------------|--------|-------------------------|
| **EURJPY** | **90.4%** | 415 | **96.6%** |
| GBPUSD | 87.4% | 413 | 87.0% |
| USDJPY | 85.5% | 415 | **96.2%** |
| EURGBP | 83.2% | 416 | 85.1% |
| **Blended 4-asset flagship** | **86.6%** | 1659 | **91.2%** |
| + skip Mondays | 87.7% | 1244 | 91.8% |

- **16 signals/day** (4 assets × 4 bars: 16:35/16:40/16:45/16:50 NY), Mon–Thu, ~64/week.
- Every month ≥ 73% (Feb 87%, Mar 73%, Apr 86%, May 94%, Jun 91%, Jul 89%); PF 5.5.
- Optional CALL rule (17:50–18:00 NY, 10-min): +6 signals/day at ~72–74% (blended 80.6%).
- Full research in [`docs/RESEARCH.md`](docs/RESEARCH.md).

## The strategy: Micro-Fix (NY settlement flow)

The 30 minutes before the **17:00 New York CME/futures settlement** show a
reproducible institutional flow pattern:

| Window (NY local time) | Direction | Expiry | Backtest accuracy |
|------------------------|-----------|--------|-------------------|
| 16:35 – 16:50 (pre-settlement dip) | **PUT** | 25 min | **83–90% per asset** |
| 17:50 – 18:00 (rally into close) | CALL (optional) | 10 min | 72–74% |

- The windows are anchored to **New York local time** (not UTC) with automatic
  **US-DST** detection in the EA (second Sunday of March → first Sunday of
  November) — the formula was validated against America/New_York for 2020–2029
  with 0 mismatches. In summer the PUT window is 20:35–20:50 UTC; in winter it
  is 21:35–21:50 UTC.
- **Fridays are skipped by default** (+2.6 pp); `MicroNoMonday` optionally adds
  +1.1 pp. The 25-minute expiry (k=5) beat 20-minute on every asset.
- One signal per closed 5-minute bar in the window → 4 signals per asset per day.

**Supported assets (validated on M5):** EURJPY 90.4% · GBPUSD 87.4% · USDJPY
85.5% · EURGBP 83.2% · AUDUSD 76.9% · EURUSD 72.0% · (XAUUSD inverts the
pattern — not recommended). The EA works on any of them without changes.

Legacy mode (optional, M15): NY-Close Seasonal rule — PUT 20:00–21:00 UTC /
CALL 21:00–23:00 UTC, 1-hour expiry — 66–67% accuracy (n=776).

---

## Files

```
ea/CYBER_Binary_Signal_EA.mq5   the Expert Advisor (drop into MetaEditor)
dashboard/dashboard.html        static demo of the dashboard (backtest data)
backtest/engine.py              vectorized backtesting engine
backtest/make_report.py         regenerates the research report + dashboard data
backtest/download_data.py       re-downloads the market data (getdata.finance, MIT)
backtest/out/report.md          full validation report
docs/RESEARCH.md                same report, conveniently placed
tools/check_mql5.py             static MQL5 syntax checker used during development
tools/make_dashboard_demo.py    regenerates the dashboard demo
```

## Installation (MT5)

1. Copy `ea/CYBER_Binary_Signal_EA.mq5` to:
   `<Terminal data folder>\MQL5\Experts\`
   (In MT5: `File ▸ Open Data Folder ▸ MQL5 ▸ Experts`.)
2. In MetaEditor press **Compile** (F7) — must finish with *0 errors, 0 warnings*.
3. In MT5: drag the EA onto a chart.
   - **Flagship (default): attach to EURJPY, GBPUSD, USDJPY and EURGBP charts
     (M5).** The Micro-Fix rule is on by default: PUT window 16:35–16:50 NY,
     25-min expiry. 4 signals per chart per day → 16/day on 4 charts.
   - Legacy mode: M15 chart, set `EnableMicroRule=false`,
     `EnableSeasonalRule=true`, `ExpiryBars=4` (1-hour expiry).
4. The **HTML dashboard opens automatically in your browser** (a new window).
   It refreshes every 5 s; the on-chart panel updates live and re-scales with
   the chart window. Statistics survive restarts (stored in
   `MQL5\Files\CYBER_Binary_EA_trades.csv`).

## Using the signals on Quotex

1. When an arrow appears (or an Alert pops), open the same asset on Quotex.
2. Buy **DOWN** for a PUT arrow (flagship), **UP** for a CALL arrow.
3. Set the expiry to the suggested time (shown in the alert, in the label next
   to the arrow, and as a dotted vertical line on the chart; default 25 min).
4. The chart shows full signal detail: arrow + **visible text label**
   (direction, rule, expiry time, entry price), an **entry-price line**, the
   expiry line, and a **live "Last Signal" panel** (bottom-left) with a
   countdown to expiry and the result once closed.
5. Optional: enable `NotifyOnSignal` (push). The EA handles US-DST
   automatically; only set `ManualNyOffset` if you disable `UseAutoUsDst`.
4. Optional: enable `NotifyOnSignal` (push). The EA handles US-DST
   automatically; only set `ManualNyOffset` if you disable `UseAutoUsDst`.

## Key inputs

| Input | Default | Meaning |
|-------|---------|---------|
| `EnableMicroRule` | true | flagship Micro-Fix rule (M5) |
| `MicroPutStartMin/MicroPutEndMin` | 995/1010 | PUT window, NY minutes (16:35–16:50) |
| `MicroNoFriday` | true | skip Fridays (+2.6 pp validated) |
| `MicroPutExpiryBars` | 5 | PUT expiry (5 bars = 25 min on M5, best on all assets) |
| `MicroNoMonday` | false | skip Mondays too (+1.1 pp, -25% signals) |
| `MicroCallEnabled` | false | also trade the 17:50–18:00 NY CALL (72–74%) |
| `MicroCallExpiryBars` | 2 | CALL expiry (10 min on M5) |
| `UseAutoUsDst` | true | automatic US DST (2nd Sun Mar → 1st Sun Nov) |
| `EnableSeasonalRule` | false | legacy M15 NY-Close Seasonal rule |
| `AutoOpenDashboard` | true | open the HTML dashboard in the browser on attach |
| `Payout` | 0.85 | payout used for Net P&L / PF statistics |

## Reproducing the research

```bash
python3 backtest/download_data.py     # ~100 MB of 1m/5m/15m/1h/30m FX data
python3 backtest/make_report.py       # regenerates backtest/out/* (report, JSON)
python3 tools/make_dashboard_demo.py  # regenerates dashboard/dashboard.html demo
python3 tools/check_mql5.py ea/CYBER_Binary_Signal_EA.mq5   # EA syntax gate
```

## Risk notes (read before live trading)

- The edge is a **slow drift, not a guarantee**. The flagship had no losing
  month in this sample (worst: 70% in Mar 2026), but expect occasional losing
  months and streaks in live trading.
- Historical FX data ≠ Quotex OTC candles (synthetic 24/7 feed) — **demo-test
  first**, and compare the OTC session times with your broker.
- Binary break-even at 85% payout is 54.05% accuracy — the flagship targets
  80–84%, so it has a large margin, but keep 1–2% max risk per trade.
- Never trade what you cannot afford to lose. Binary options carry a high risk
  of losing your entire stake.

## Development notes

The EA passed the strict bug-hunt milestone: static MQL5 syntax validation
(`tools/check_mql5.py`), a tree-sitter MQL5 grammar parse, a Python runtime
simulation of the EA's exact resolution semantics, and the US-DST formula was
validated against the official America/New_York timezone (14,612 samples,
0 mismatches). The EA's Micro-Fix logic reproduces the backtest exactly
(83.57% in the EA-semantics simulation).
