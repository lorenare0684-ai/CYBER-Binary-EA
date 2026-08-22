# CYBER Binary EA

**Quotex binary-options signal Expert Advisor for MetaTrader 5** — research-backed
CALL/PUT signals with a live dashboard (winrate, wins, losses, accuracy) that
opens automatically in a new window when you attach the EA and auto-scales to
any window size.

> ⚠️ **Read-only advisor.** The EA only *generates signals* (arrows + alerts +
> dashboard). Execution is done manually on Quotex. It never sends orders.

---

## TL;DR — the 90%+ flagship (Micro-Fix precision mode, M5)

| Setup | **Accuracy** | Trades | Out-of-sample (May–Jul) |
|-------|--------------|--------|-------------------------|
| **EURJPY** (16:40–16:45 NY, 20-min) | **93.3%** | 208 | **97.1%** |
| **EURJPY + USDJPY** (90%+ default) | **92.6%** | 312 | **96.2%** |
| GBPUSD (16:40–16:45 NY, 25-min) | 88.8% | 206 | 87.4% |
| All 4 assets (precision) | 87.6% | 934 | 89.3% |
| Wide mode: 16:35–16:50, 4 assets | 86.6% | 1659 | 91.2% |

- **Precision mode is the new default** (`MicroPrecisionMode=true`): EURJPY
  2 signals/day at 93.3%; add USDJPY for 3/day at 92.6% blended. Every month
  ≥ 85% (Feb 90%, Mar 85%, Apr 93%, May 98%, Jun 96%, Jul 94%); PF 10.7.
- Wide mode (`MicroPrecisionMode=false`): 16 signals/day at 86.6% blended.
- Optional CALL rule (17:50–18:00 NY, 10-min): +6 signals/day at ~72–74%.
- Full research in [`docs/RESEARCH.md`](docs/RESEARCH.md).

### ⚠️ What 20+ years of data shows (read this)

The flagship was re-validated on **19 years of 1-minute HistData (2000–2018,
all 6 pairs)** with the exact same rule and correct historical DST: accuracy
is **49–55% — the edge did not exist then**. The 71–90% numbers are a recent
(2026) phenomenon; 2019–2025 is unverifiable from this environment. The
coarser legacy rule (M15/1h) does show a modest edge over 25 years (53% →
55% → 57% by era, same provider). **Treat the 80%+ as regime-specific, not a
20-year expectation** — demo-validate on your Quotex OTC feed for several
weeks before risking real money, and re-measure monthly.

## The strategy: Micro-Fix (NY settlement flow)

The 30 minutes before the **17:00 New York CME/futures settlement** show a
reproducible institutional flow pattern:

| Window (NY local time) | Direction | Expiry | Backtest accuracy |
|------------------------|-----------|--------|-------------------|
| 16:40 – 16:45 (dip core) EURJPY | **PUT** | 20 min | **93.3%** |
| 16:45 (dip core) USDJPY | **PUT** | 30 min | **91.4%** |
| 16:40 – 16:45 (dip core) GBPUSD | **PUT** | 25 min | 88.8% |
| 16:35 – 16:50 (wide) | **PUT** | 25 min | 83–90% per asset |
| 17:50 – 18:00 (rally into close) | CALL (optional) | 10 min | 72–74% |

- The windows are anchored to **New York local time** (not UTC) with automatic
  **US-DST** detection in the EA (second Sunday of March → first Sunday of
  November) — the formula was validated against America/New_York for 2020–2029
  with 0 mismatches. In summer the PUT window is 20:35–20:50 UTC; in winter it
  is 21:35–21:50 UTC.
- **Fridays are skipped by default** (+2.6 pp); `MicroNoMonday` optionally adds
  +1.1 pp. The 25-minute expiry (k=5) beat 20-minute on every asset.
- One signal per closed 5-minute bar in the window → 4 signals per asset per day.

**Supported assets (validated on M5):** EURJPY 93.3% (precision) · USDJPY
91.4% (precision) · GBPUSD 88.8% (precision) · EURGBP 83.2% · AUDUSD 76.9% ·
EURUSD 72.0% · (XAUUSD inverts the pattern — not recommended). The EA works
on any of them without changes.

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
   - **90%+ default: attach to EURJPY and USDJPY charts (M5).** Precision
     mode is on by default: EURJPY 16:40–16:45 NY 20-min expiry (2 signals/
     day), USDJPY 16:45 NY 30-min (1 signal/day) → 3/day at 92.6% blended.
     Add GBPUSD (16:40–16:45, 25-min) for 2 more/day at 88.8%.
   - Legacy mode: M15 chart, set `EnableMicroRule=false`,
     `EnableSeasonalRule=true`, `ExpiryBars=4` (1-hour expiry).
4. The **HTML dashboard opens automatically in your browser** (a new window).
   It refreshes every 5 s; the on-chart panel updates live and re-scales with
   the chart window. Statistics survive restarts (stored in
   `MQL5\Files\CYBER_Binary_EA_trades.csv`).

   **On-chart signals (non-repainting):** arrows are drawn once at the fixed
   time/price of the closed signal bar and never move. PUT arrows sit above
   the bar, CALL arrows below it (never hidden by candles), each with a
   visible label (direction, rule, expiry, entry), an entry-price line and an
   expiry line. On attach, the EA also **redraws up to 250 past signals from
   its statistics file** as fixed arrows, so you see the history immediately.
   The two panels (stats + last-signal with countdown) are stacked at the same
   corner so they never overlap, and the font auto-shrinks so every line
   always fits the window.

   **Historical painting (`PaintHistorySignals=true`, default):** the EA
   scans the chart's own closed bars (last `HistorySignalBars` = 10,000 by
   default, ~35 days on M5) and paints an arrow at every historical price
   where the micro-fix rule would have fired — even on a brand-new chart with
   no saved statistics. It uses the same shared window logic as live signals
   (per-bar US-DST so winter/summer bars are placed correctly, Friday/Monday
   filters, precision/wide mode) and skips bars that already carry a live
   arrow. Expect ~56 arrows on EURJPY/GBPUSD, ~28 on USDJPY over 10,000 M5
   bars; raise `HistorySignalBars` to paint deeper history.

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
| `MicroPrecisionMode` | true | per-asset optimized windows (90%+); false = wide 16:35–16:50 |
| `MicroPutStartMin/MicroPutEndMin` | 995/1010 | PUT window, NY minutes (used in wide mode) |
| `MicroNoFriday` | true | skip Fridays (+2.6 pp validated) |
| `MicroPutExpiryBars` | 5 | PUT expiry in wide mode (5 bars = 25 min on M5) |
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

- The edge is a **slow drift, not a guarantee** — and it is **regime-dependent**:
  the flagship numbers come from the 2026 sample; the same rule on 2000–2018
  HistData (19 years, 6 pairs) shows 49–55% (no edge). Expect occasional
  losing months and streaks in live trading, and re-measure monthly.
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
0 mismatches). The EA's Micro-Fix logic reproduces the backtest exactly.

**v1.30 compile fixes (MetaEditor-clean):** the file previously used
`LOG_VERSION` and `SW_SHOWNORMAL` without defining them and called
`ShellExecuteW` without importing it from shell32.dll — MetaEditor reported
16 errors (undeclared identifiers + cascade "reference cannot used" /
"implicit conversion" noise). Fixed:
- `#define LOG_VERSION 3` (statistics file format version)
- `#define SW_SHOWNORMAL 1` + `#import "shell32.dll"` block with the full
  6-parameter `ShellExecuteW(long hwnd, ...)` signature (hwnd=0 in the call)
- `NULL` string args replaced with `""` (MQL5 has no NULL for strings)
- `tools/check_mql5.py` now also **resolves identifiers**: every identifier
  used in the code must be declared (#define, #import, input, variable,
  parameter, struct) or be a known MQL5 builtin — the check that would have
  caught these bugs. Verified: removing `LOG_VERSION` fails the gate.

**v1.31 compile fixes (round 2):** MetaEditor reported `reference cannot used`
(×4) and `implicit conversion from 'int' to 'string'` (×1). Fixed:
- All 4 local `TradeRec &t = g_trades[i];` reference declarations replaced
  with by-value copies (`TradeRec t = ...`) — MQL5 only allows references as
  function parameters, so local references to array elements fail to compile.
  All 4 sites only read the struct, so copies are semantically identical.
- `LOG_VERSION` is now a string literal (`"3"`): it is compared against a
  `FileReadString()` result (`verNum != LOG_VERSION`), and MQL5 rejects the
  implicit int→string conversion in that comparison.
- `tools/check_mql5.py` gained two more rules that catch both classes:
  non-parameter `Type &name = ...` declarations, and string-variable vs
  numeric-#define comparisons. Both sanity-tested (each fails the gate).
