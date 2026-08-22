# CYBER Binary EA

**Quotex binary-options signal Expert Advisor for MetaTrader 5** — research-backed
CALL/PUT signals with a live dashboard (winrate, wins, losses, accuracy) that
opens automatically in a new window when you attach the EA and auto-scales to
any window size.

> ⚠️ **Read-only advisor.** The EA only *generates signals* (arrows + alerts +
> dashboard). Execution is done manually on Quotex. It never sends orders.

---

## TL;DR — results (backtest, Feb–Jul 2026, real FX 1-minute data)

| Instrument | Timeframe | Expiry | Trades | Accuracy | Profit factor |
|------------|-----------|--------|--------|----------|---------------|
| **USDJPY** | M15 | 1 h | 776 | **67.0%** | 1.73 |
| **GBPUSD** | M15 | 1 h | 776 | **66.5%** | 1.69 |
| GBPUSD | M5 | 30 m | 2331 | 62.0% | 1.38 |
| USDJPY | M5 | 30 m | 2331 | 59.4% | 1.25 |
| EURUSD | M15 | 1 h | 776 | 57.1% | 1.13 |

Out-of-sample walk-forward (May–Jul, parameters untouched): GBPUSD **72.9%**,
USDJPY **75.7%**. Full research in [`docs/RESEARCH.md`](docs/RESEARCH.md).

## The strategy: NY-Close Seasonal

FX has a reproducible intraday flow pattern around the **17:00 New York fixing**:

| Window (UTC) | Direction | Backtest accuracy (M15/1h) |
|--------------|-----------|------------------------------|
| 20:00 – 21:00 (pre-fix dip) | **PUT** | **75%** (GBPUSD, n=258) |
| 21:00 – 22:00 (fix rally) | **CALL** | 65% (GBPUSD, n=260) |
| 22:00 – 23:00 (rally tail) | **CALL** | 58% (GBPUSD, n=258) |

Signal = one arrow per bar at the bar close during these windows, expiry
`ExpiryBars` bars later (default 4 bars = 1 h on M15). A cooldown of 2 bars
keeps trades spaced. An optional second rule (burst-reversal: a large bearish
candle below the slow EMA tends to bounce, 54–57% on M5) is available but
disabled by default.

---

## Files

```
ea/CYBER_Binary_Signal_EA.mq5   the Expert Advisor (drop into MetaEditor)
dashboard/dashboard.html        static demo of the dashboard (backtest data)
backtest/engine.py              vectorized backtesting engine (indicators, grid, walk-forward)
backtest/make_report.py         regenerates the research report + dashboard data
backtest/download_data.py       re-downloads the market data (getdata.finance, MIT)
backtest/out/report.md          full validation report
docs/RESEARCH.md                same report, conveniently placed
tools/check_mql5.py             static MQL5 syntax checker used during development
```

## Installation (MT5)

1. Copy `ea/CYBER_Binary_Signal_EA.mq5` to:
   `<Terminal data folder>\MQL5\Experts\`
   (In MT5: `File ▸ Open Data Folder ▸ MQL5 ▸ Experts`.)
2. In MetaEditor press **Compile** (F7) — must finish with *0 errors, 0 warnings*.
3. In MT5: drag the EA onto a chart.
   - Recommended: **GBPUSD or USDJPY, M15**, `ExpiryBars = 4` (1-hour expiry).
   - M5 users: `ExpiryBars = 6` (30-minute expiry).
4. The **HTML dashboard opens automatically in your browser** (a new window).
   It refreshes every 5 s; the on-chart panel updates live and re-scales with
   the chart window. Statistics survive restarts (stored in
   `MQL5\Files\CYBER_Binary_EA_trades.csv`).

## Using the signals on Quotex

1. When an arrow appears (or an Alert pops), open the same asset on Quotex.
2. Buy **UP** for a CALL arrow, **DOWN** for a PUT arrow.
3. Set the expiry to the suggested time (shown in the alert and as a dotted
   line on the chart).
4. Optional: enable `NotifyOnSignal` (push) and set `UtcOffsetHours` if your
   broker's GMT differs.

## Key inputs

| Input | Default | Meaning |
|-------|---------|---------|
| `EnableSeasonalRule` | true | core NY-close rule |
| `EnableBurstRule` | false | optional M5 burst-reversal rule |
| `ExpiryBars` | 4 | expiry in bars (M15 → 1 h; M5 → 30 m with 6) |
| `CooldownBars` | 2 | min bars between signals |
| `MinConditions` | 0 | 0 = window only (best); 1–5 = add confluence filters |
| `PutStartHour/PutEndHour` | 20/21 | PUT window, UTC |
| `CallStartHour/CallEndHour` | 21/23 | CALL window, UTC |
| `AutoOpenDashboard` | true | open the HTML dashboard in the browser on attach |
| `Payout` | 0.85 | payout used for Net P&L / PF statistics |

## Reproducing the research

```bash
python3 backtest/download_data.py     # ~100 MB of 1m/5m/15m/1h/30m FX data
python3 backtest/make_report.py       # regenerates backtest/out/* (report, JSON, trades CSV)
python3 tools/make_dashboard_demo.py  # regenerates dashboard/dashboard.html demo
python3 tools/check_mql5.py ea/CYBER_Binary_Signal_EA.mq5   # EA syntax gate
```

## Risk notes (read before live trading)

- The edge is a **slow drift, not a guarantee**. Feb 2026 (a tariff-shock month)
  lost in every variant; expect occasional losing months.
- Historical FX data ≠ Quotex OTC candles (synthetic 24/7 feed) — demo-test first.
- Binary break-even at 85% payout is 54.05% accuracy; this strategy targets
  57–67% — keep 1–2% max risk per trade and stop after 2 consecutive losses.
- Never trade what you cannot afford to lose. Binary options carry a high risk
  of losing your entire stake.

## Development notes

The EA was developed with a strict bug-hunt milestone: static MQL5 syntax
validation (`tools/check_mql5.py`), a tree-sitter MQL5 grammar parse, and a
Python runtime simulation of the EA's exact resolution semantics
(entry-at-bar-close, expiry-bar lookup, weekend-gap cancellation) validated
against the backtest engine — engine 66.54% vs EA-simulation 66.39% (delta =
weekend-gap cancels, by design).
