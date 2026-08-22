"""
CYBER Binary EA - Backtesting engine
====================================
Vectorized indicator library + binary-options trade simulator.

Trade model (identical to the MQL5 EA):
  * A signal is evaluated on the CLOSE of bar i (indicators use data up to and
    including bar i only - no look-ahead).
  * Entry price = OPEN of bar i+1 (next bar).
  * Expiry = `expiry` bars later; outcome compares CLOSE of bar i+1+expiry
    against the entry price.
  * CALL wins if close[entry+k] > open[entry]; PUT wins if close[entry+k] <
    open[entry]. Equal price = scratch (counted neither win nor loss).
  * Cooldown: no new signal within `cooldown` bars after a trade.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------------

def load_csv(path: str) -> dict:
    """Load a getdata.finance style CSV -> {dt, o, h, l, c} numpy arrays (UTC)."""
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.drop_duplicates(subset="datetime").sort_values("datetime")
    df = df[["datetime", "open", "high", "low", "close"]].dropna()
    return {
        "dt": df["datetime"].to_numpy(),
        "o": df["open"].to_numpy(dtype=np.float64),
        "h": df["high"].to_numpy(dtype=np.float64),
        "l": df["low"].to_numpy(dtype=np.float64),
        "c": df["close"].to_numpy(dtype=np.float64),
    }


def resample(data: dict, rule: str) -> dict:
    """Resample 1m bars to a coarser timeframe (e.g. '5min', '15min')."""
    df = pd.DataFrame({"o": data["o"], "h": data["h"], "l": data["l"], "c": data["c"]},
                      index=pd.to_datetime(data["dt"]))
    agg = df.resample(rule, label="left", closed="left").agg(
        {"o": "first", "h": "max", "l": "min", "c": "last"}
    ).dropna()
    return {
        "dt": agg.index.to_numpy(),
        "o": agg["o"].to_numpy(dtype=np.float64),
        "h": agg["h"].to_numpy(dtype=np.float64),
        "l": agg["l"].to_numpy(dtype=np.float64),
        "c": agg["c"].to_numpy(dtype=np.float64),
    }


# ----------------------------------------------------------------------------
# Indicators (vectorized; all return float64 numpy arrays with NaN warm-up)
# ----------------------------------------------------------------------------

def ema(x: np.ndarray, period: int) -> np.ndarray:
    s = pd.Series(x)
    return s.ewm(span=period, adjust=False).mean().to_numpy()


def rsi(x: np.ndarray, period: int) -> np.ndarray:
    s = pd.Series(x)
    d = s.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    ru = up.ewm(alpha=1.0 / period, adjust=False).mean()
    rd = dn.ewm(alpha=1.0 / period, adjust=False).mean()
    out = 100.0 - 100.0 / (1.0 + ru / rd.replace(0.0, np.nan))
    return out.to_numpy()


def stochastic(h: np.ndarray, l: np.ndarray, c: np.ndarray, k: int, d: int) -> tuple[np.ndarray, np.ndarray]:
    ll = pd.Series(l).rolling(k, min_periods=k).min()
    hh = pd.Series(h).rolling(k, min_periods=k).max()
    rng = (hh - ll).replace(0.0, np.nan)
    kline = 100.0 * (pd.Series(c) - ll) / rng
    dline = kline.rolling(d, min_periods=d).mean()
    return kline.to_numpy(), dline.to_numpy()


def true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    pc = np.empty_like(c)
    pc[0] = c[0]
    pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return tr


def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int) -> np.ndarray:
    tr = pd.Series(true_range(h, l, c))
    return tr.ewm(alpha=1.0 / period, adjust=False).mean().to_numpy()


def adx(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int) -> np.ndarray:
    n = len(c)
    up = np.diff(h, prepend=h[0])
    dn = -np.diff(l, prepend=l[0])
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.Series(true_range(h, l, c)).ewm(alpha=1.0 / period, adjust=False).mean().to_numpy()
    pdi = 100.0 * pd.Series(plus_dm).ewm(alpha=1.0 / period, adjust=False).mean().to_numpy() / tr
    mdi = 100.0 * pd.Series(minus_dm).ewm(alpha=1.0 / period, adjust=False).mean().to_numpy() / tr
    dx = 100.0 * np.abs(pdi - mdi) / np.where((pdi + mdi) == 0.0, np.nan, pdi + mdi)
    adxv = pd.Series(dx).ewm(alpha=1.0 / period, adjust=False).mean().to_numpy()
    return adxv


def cci(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int) -> np.ndarray:
    tp = (h + l + c) / 3.0
    sma = pd.Series(tp).rolling(period, min_periods=period).mean()
    md = pd.Series(tp).rolling(period, min_periods=period).apply(
        lambda w: np.mean(np.abs(w - w.mean())), raw=True
    )
    return ((tp - sma) / (0.015 * md)).to_numpy()


def macd(x: np.ndarray, fast: int, slow: int, sig: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    line = ema(x, fast) - ema(x, slow)
    sigline = pd.Series(line).ewm(span=sig, adjust=False).mean().to_numpy()
    return line, sigline, line - sigline


# ----------------------------------------------------------------------------
# Parameter space
# ----------------------------------------------------------------------------

@dataclass
class StrategyParams:
    name: str = "confluence"
    # trend
    ema_fast: int = 9
    ema_slow: int = 21
    ema_trend: int = 50
    # momentum
    rsi_period: int = 14
    rsi_zone: tuple[float, float] = (45.0, 75.0)      # allowed RSI range at entry
    stoch_k: int = 14
    stoch_d: int = 3
    # strength / volatility
    adx_period: int = 14
    adx_min: float = 18.0
    atr_period: int = 14
    atr_min_pct: float = 0.0        # min ATR as fraction of price
    atr_max_pct: float = 1.0        # max ATR as fraction of price
    # signal gating
    min_conditions: int = 4         # of 5 confluence conditions required
    cooldown: int = 3               # bars between trades
    expiry_bars: int = 3
    pullback_ok: bool = False       # allow counter-trend pullback entries
    rsi_pullback_lo: float = 35.0   # RSI floor for pullback buys
    pullback_dist_atr: float = 0.6  # max distance close->slow EMA (in ATR) for pullback
    require_close_above_ema: bool = False
    trend_day: bool = False         # only trade with the daily (EMA200) trend
    ema_day: int = 200
    session_filter: bool = False    # London/NY only (FX)
    use_cci: bool = False
    cci_floor: float = -100.0
    cci_ceil: float = 100.0
    body_min: float = 0.0           # min |body|/ATR of signal candle (momentum burst)
    entry_mode: str = "close"       # "close": enter at signal-bar close; "next_open": enter at next bar open
    session_window: tuple = (7, 21) # UTC hours [start, end) when trading is allowed (if session_filter)
    mode: str = "trend"             # "trend" | "reversal" | "seasonal"
    seasonal_call: tuple = (21, 23) # seasonal: UTC hours for CALL window [start,end)
    seasonal_put: tuple = (20, 21)  # seasonal: UTC hours for PUT window [start,end)
    rev_rsi: float = 30.0           # reversal: RSI must be below this (CALL) / above 100-this (PUT)
    rev_stoch: float = 25.0         # reversal: stochastic must be below (CALL) / above 100-this (PUT)
    rev_dist_atr: float = 1.0       # reversal: price stretched this many ATR beyond slow EMA
    adx_max: float = 20.0           # reversal: ADX must be below this (no strong trend)

    def to_json(self) -> dict:
        d = asdict(self)
        d["rsi_zone"] = list(self.rsi_zone)
        d["session_window"] = list(self.session_window)
        d["seasonal_call"] = list(self.seasonal_call)
        d["seasonal_put"] = list(self.seasonal_put)
        return d


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# Indicator cache (precompute once per dataset; grid search then only
# evaluates conditions -> fast scanning of thousands of parameter combos)
# ----------------------------------------------------------------------------

def indicator_cache(data: dict, ema_periods=(3, 5, 8, 9, 10, 12, 15, 20, 21, 26, 34, 50, 68, 100, 144, 200),
                    rsi_periods=(5, 7, 9, 14, 21), stoch_specs=((14, 3), (9, 3), (21, 5)),
                    atr_periods=(7, 14, 21), adx_periods=(10, 14, 20, 28)) -> dict:
    o, h, l, c = data["o"], data["h"], data["l"], data["c"]
    cache = {"o": o, "h": h, "l": l, "c": c}
    cache["ema"] = {p: ema(c, p) for p in ema_periods}
    cache["rsi"] = {p: rsi(c, p) for p in rsi_periods}
    cache["stoch"] = {(k, d): stochastic(h, l, c, k, d) for k, d in stoch_specs}
    cache["atr"] = {p: atr(h, l, c, p) for p in atr_periods}
    cache["adx"] = {p: adx(h, l, c, p) for p in adx_periods}
    cache["cci"] = cci(h, l, c, 20)
    return cache


def generate_signals_cached(o, h, l, c, cache: dict, p: StrategyParams,
                            dt: Optional[np.ndarray] = None) -> np.ndarray:
    """Fast VECTORIZED signal generation using a precomputed indicator cache."""
    n = len(c)
    ema_f = cache["ema"][p.ema_fast]
    ema_s = cache["ema"][p.ema_slow]
    ema_t = cache["ema"][p.ema_trend]
    r = cache["rsi"][p.rsi_period]
    sk, sd = cache["stoch"][(p.stoch_k, p.stoch_d)]
    a = cache["atr"][p.atr_period]
    dx = cache["adx"][p.adx_period]
    cc = cache["cci"] if p.use_cci else None

    body = np.abs(c - o) / np.where(a > 0, a, np.nan)

    with np.errstate(invalid="ignore"):
        up_trend = (ema_f > ema_s) & (ema_s > ema_t)
        dn_trend = (ema_f < ema_s) & (ema_s < ema_t)
        if p.require_close_above_ema:
            up_trend = up_trend & (c > ema_s)
            dn_trend = dn_trend & (c < ema_s)

        if p.trend_day:
            ema_d = cache["ema"][p.ema_day]
            up_trend = up_trend & (c > ema_d)
            dn_trend = dn_trend & (c < ema_d)

        if not p.pullback_ok:
            up_mom = (sk > sd) & (sk < 85.0) & (r >= p.rsi_zone[0]) & (r <= p.rsi_zone[1])
            dn_mom = (sk < sd) & (sk > 15.0) & (r >= p.rsi_zone[0]) & (r <= p.rsi_zone[1])
        else:
            # pullback: trend up, price within pullback_dist_atr*ATR of slow EMA,
            # stoch turning up from a low zone, RSI above its oversold floor
            up_mom = (sk > sd) & (sk < 45.0) & (r >= p.rsi_pullback_lo) \
                & (np.abs(c - ema_s) <= p.pullback_dist_atr * a)
            dn_mom = (sk < sd) & (sk > 55.0) & (r <= 100.0 - p.rsi_pullback_lo) \
                & (np.abs(c - ema_s) <= p.pullback_dist_atr * a)

        if p.mode == "reversal":
            # fade stretched prices back toward the mean: RSI + stoch extremes,
            # price extended beyond rev_dist_atr*ATR from slow EMA, weak trend only
            up_mom = (r <= p.rev_rsi) & (sk <= p.rev_stoch) & (c <= ema_s - p.rev_dist_atr * a)
            dn_mom = (r >= 100.0 - p.rev_rsi) & (sk >= 100.0 - p.rev_stoch) & (c >= ema_s + p.rev_dist_atr * a)
            up_trend = up_mom        # reuse slots: "trend" = stretched condition
            dn_trend = dn_mom
            up_str = dx <= p.adx_max
            dn_str = dx <= p.adx_max

        if p.mode == "seasonal":
            # time-of-day seasonality (e.g. NY-close rally 21:00-23:00 UTC).
            # The hour gate below decides direction; these conditions are
            # optional confluence filters layered on top.
            up_trend = (c > ema_s) & (ema_s > ema_t)
            dn_trend = (c < ema_s) & (ema_s < ema_t)
            sk_prev = np.empty_like(sk); sk_prev[0] = sk[0]; sk_prev[1:] = sk[:-1]
            up_mom = (r > 50.0) & (sk > sd) & (sk > sk_prev)
            dn_mom = (r < 50.0) & (sk < sd) & (sk < sk_prev)

        up_str = dx >= p.adx_min
        dn_str = dx >= p.adx_min

        atr_norm = a / np.where(c > 0, c, 1.0)
        up_vol = (atr_norm >= p.atr_min_pct) & (atr_norm <= p.atr_max_pct)
        dn_vol = up_vol

        if p.use_cci and cc is not None:
            up_cci = (cc >= p.cci_floor) & (cc <= p.cci_ceil)
            dn_cci = (cc >= -p.cci_ceil) & (cc <= -p.cci_floor)
        else:
            up_cci = dn_cci = np.ones(n, dtype=bool)

        burst = body >= p.body_min

        up_score = up_trend.astype(np.int8) + up_mom.astype(np.int8) + up_str.astype(np.int8) \
            + up_vol.astype(np.int8) + up_cci.astype(np.int8) + burst.astype(np.int8)
        dn_score = dn_trend.astype(np.int8) + dn_mom.astype(np.int8) + dn_str.astype(np.int8) \
            + dn_vol.astype(np.int8) + dn_cci.astype(np.int8) + burst.astype(np.int8)

        if p.mode == "seasonal":
            # direction comes from the time window; confluence filters are optional
            call = (up_score >= p.min_conditions)
            put = (dn_score >= p.min_conditions)
        else:
            call = (up_score >= p.min_conditions) & (up_score >= dn_score)
            put = (dn_score >= p.min_conditions) & (dn_score > up_score)

        if p.session_filter:
            if dt is None:
                raise ValueError("session_filter=True requires dt timestamps")
            hours = np.array([t.hour for t in pd.to_datetime(dt)])
            h0, h1 = p.session_window
            if h0 <= h1:
                sess = (hours >= h0) & (hours < h1)
            else:  # wraps midnight, e.g. (21, 2)
                sess = (hours >= h0) | (hours < h1)
            call = call & sess
            put = put & sess

        if p.mode == "seasonal":
            # seasonal windows: (h0,h1) = CALL window, (h2,h3) = PUT window
            (h0, h1), (h2, h3) = p.seasonal_call, p.seasonal_put
            if dt is None:
                raise ValueError("seasonal mode requires dt timestamps")
            hours = np.array([t.hour for t in pd.to_datetime(dt)])
            def inwin(h, a, b):
                if a <= b:
                    return (h >= a) & (h < b)
                return (h >= a) | (h < b)
            call = call & inwin(hours, h0, h1)
            put = put & inwin(hours, h2, h3)

        dirs = np.zeros(n, dtype=np.int8)
        dirs[call] = 1
        dirs[put] = -1
        # never signal on the very last bar (need a next bar to enter)
        dirs[n - 1] = 0
        # warm-up: drop signals while any core indicator is still NaN
        warm = max(p.ema_trend, p.rsi_period, p.adx_period, p.atr_period, p.stoch_k + p.stoch_d) + 5
        dirs[:warm] = 0
    return dirs


def generate_signals(o, h, l, c, p: StrategyParams, dt: Optional[np.ndarray] = None):
    """Convenience wrapper: builds a fresh cache then generates signals."""
    cache = indicator_cache(
        {"o": o, "h": h, "l": l, "c": c},
        ema_periods=tuple({p.ema_fast, p.ema_slow, p.ema_trend}),
        rsi_periods=(p.rsi_period,),
        stoch_specs=((p.stoch_k, p.stoch_d),),
        atr_periods=(p.atr_period,),
        adx_periods=(p.adx_period,),
    )
    return generate_signals_cached(o, h, l, c, cache, p, dt=dt)


def apply_cooldown(dirs: np.ndarray, cooldown: int) -> np.ndarray:
    """Zero out signals that occur within `cooldown` bars of a kept signal."""
    out = np.zeros_like(dirs)
    last = -10**9
    n = len(dirs)
    for i in range(n):
        if dirs[i] != 0 and i - last >= cooldown:
            out[i] = dirs[i]
            last = i
    return out


# ----------------------------------------------------------------------------
# Trade simulation
# ----------------------------------------------------------------------------

@dataclass
class Trade:
    idx: int
    ts: str
    direction: int      # +1 CALL / -1 PUT
    entry: float
    exit: float
    result: int         # +1 win, -1 loss, 0 scratch
    conf: float = 0.0


@dataclass
class BacktestResult:
    trades: list = field(default_factory=list)
    params: dict = field(default_factory=dict)
    label: str = ""
    # stats
    wins: int = 0
    losses: int = 0
    scratches: int = 0
    accuracy: float = 0.0        # wins / (wins + losses)
    net: float = 0.0             # pnl per 1.0 stake at payout 0.85
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    avg_conf: float = 0.0

    def stats(self) -> dict:
        return {
            "label": self.label,
            "trades": len(self.trades),
            "wins": self.wins,
            "losses": self.losses,
            "scratches": self.scratches,
            "accuracy": round(self.accuracy * 100.0, 2),
            "net_per_stake": round(self.net, 3),
            "profit_factor": round(self.profit_factor, 3),
            "max_drawdown": round(self.max_drawdown, 3),
            "avg_conf": round(self.avg_conf, 2),
        }


def run_backtest(data: dict, p: StrategyParams, payout: float = 0.85,
                 label: str = "", start: Optional[int] = None, end: Optional[int] = None,
                 cooldown: Optional[int] = None, cache: Optional[dict] = None) -> BacktestResult:
    o, h, l, c = data["o"], data["h"], data["l"], data["c"]
    n = len(c)
    s, e = (0, n) if start is None else (start, end if end is not None else n)
    o, h, l, c = o[s:e], h[s:e], l[s:e], c[s:e]
    dt = data["dt"][s:e] if "dt" in data else None

    if cache is not None:
        # slice cache arrays to the requested window
        sub = {k: (v[s:e] if isinstance(v, np.ndarray) else v) for k, v in cache.items()}
        for key in ("ema", "rsi", "atr", "adx"):
            sub[key] = {p2: arr[s:e] for p2, arr in cache[key].items()}
        sub["stoch"] = {k2: (a[s:e], b[s:e]) for k2, (a, b) in cache["stoch"].items()}
        if "cci" in cache:
            sub["cci"] = cache["cci"][s:e]
        dirs = generate_signals_cached(o, h, l, c, sub, p, dt=dt)
    else:
        dirs = generate_signals(o, h, l, c, p, dt=dt)
    k = p.expiry_bars
    cd = cooldown if cooldown is not None else p.cooldown
    dirs = apply_cooldown(dirs, cd)

    res = BacktestResult(label=label, params=p.to_json())
    m = len(c)
    for i in range(m):
        d = int(dirs[i])
        if d == 0:
            continue
        if p.entry_mode == "next_open":
            entry_idx = i + 1
            exit_idx = entry_idx + k
            if exit_idx >= m:
                continue
            entry = o[entry_idx]
        else:  # "close": buy at the signal-bar close (instant execution)
            entry_idx = i
            exit_idx = i + k
            if exit_idx >= m:
                continue
            entry = c[i]
        exitp = c[exit_idx]
        result = 0
        if d == 1:
            result = 1 if exitp > entry else (-1 if exitp < entry else 0)
        else:
            result = 1 if exitp < entry else (-1 if exitp > entry else 0)
        res.trades.append(Trade(
            idx=s + i,
            ts=str(pd.Timestamp(data["dt"][s + i])),
            direction=d, entry=entry, exit=exitp, result=result,
        ))

    # stats
    wins = [t for t in res.trades if t.result == 1]
    losses = [t for t in res.trades if t.result == -1]
    scratches = [t for t in res.trades if t.result == 0]
    res.wins, res.losses, res.scratches = len(wins), len(losses), len(scratches)
    total = res.wins + res.losses
    res.accuracy = res.wins / total if total else 0.0
    pnl = 0.0
    eq = 0.0
    peak = 0.0
    for t in res.trades:
        pnl += (payout if t.result == 1 else (-1.0 if t.result == -1 else 0.0))
        eq += (payout if t.result == 1 else (-1.0 if t.result == -1 else 0.0))
        peak = max(peak, eq)
        res.max_drawdown = min(res.max_drawdown, eq - peak)
    res.net = pnl
    if losses:
        res.profit_factor = sum(payout for t in wins) / sum(1.0 for t in losses)
    res.avg_conf = float(np.mean([t.conf for t in res.trades])) if res.trades else 0.0
    return res


# ----------------------------------------------------------------------------
# Grid search
# ----------------------------------------------------------------------------

def grid_search(data: dict, base: StrategyParams, grid: dict,
                min_trades: int = 100, top_n: int = 12,
                payout: float = 0.85, verbose: bool = True) -> list[dict]:
    """grid: {field: [values]}. Returns ranked results with stats."""
    import itertools

    keys = list(grid.keys())
    combos = list(itertools.product(*[grid[k] for k in keys]))
    results = []
    t0 = time.time()
    cache = indicator_cache(data)
    for ci, combo in enumerate(combos):
        p = StrategyParams(**{**base.to_json(), **dict(zip(keys, combo))})
        r = run_backtest(data, p, payout=payout, label=str(combo), cache=cache)
        acc = r.accuracy * 100.0
        if r.wins + r.losses >= min_trades and acc >= 50.0:
            results.append({**r.stats(), "combo": dict(zip(keys, combo))})
    results.sort(key=lambda x: (x["accuracy"], x["trades"]), reverse=True)
    if verbose:
        print(f"grid: {len(combos)} combos in {time.time()-t0:.1f}s, {len(results)} pass filters")
        for row in results[:top_n]:
            print(f"  {row['accuracy']:6.2f}%  n={row['trades']:5d}  pf={row['profit_factor']:.2f}  {row['combo']}")
    return results[:top_n]


def walk_forward(data: dict, p: StrategyParams, splits: list[float],
                 payout: float = 0.85, label: str = "") -> list[dict]:
    """Evaluate the SAME params on successive out-of-sample windows."""
    n = len(data["c"])
    out = []
    for fr in splits:
        s = int(n * fr[0])
        e = int(n * fr[1])
        r = run_backtest(data, p, payout=payout, start=s, end=e,
                         label=f"{label} [{fr[0]:.2f}-{fr[1]:.2f}]")
        out.append(r.stats())
    return out
