#!/usr/bin/env python3
"""Validate the Micro-Fix rule (NY pre-settlement dip, PUT) on 19 years of
1-minute HistData (riknv/fx-m1-data mirror, 2000-2018) + the 2026 dataset.

Part 1: the exact current anchor (entries at NY 16:40/16:45/16:50/16:55,
        +25-min expiry, no Fridays, Sundays excluded) per pair-year.
Part 2: era scan - for each era, find the best 15-minute PUT window in
        NY 15:00..18:00 (5-min steps) to see whether/when the effect exists.

NY local -> UTC uses America/New_York (zoneinfo), correct pre-2007 DST.

Data setup (GitHub mirror of HistData M1):
  git clone --depth 1 --filter=blob:none --sparse \
      https://github.com/riknv/fx-m1-data.git backtest/data/histdata_m1
  cd backtest/data/histdata_m1
  git sparse-checkout set eurusd gbpusd usdjpy eurjpy eurgbp audusd
"""
import os
import sys
import zipfile
import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "backtest", "data", "histdata_m1")
OUT1 = os.path.join(ROOT, "backtest", "out", "long_history_microfix.csv")
OUT2 = os.path.join(ROOT, "backtest", "out", "long_history_scan.csv")
NY = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

PAIRS = ["eurusd", "gbpusd", "usdjpy", "eurjpy", "eurgbp", "audusd"]
EXPIRY_MIN = 25


def entry_minute_utc(date_ny, ny_min):
    loc = dt.datetime(date_ny.year, date_ny.month, date_ny.day, ny_min // 60, ny_min % 60, tzinfo=NY)
    return int(loc.astimezone(UTC).timestamp() // 60)


def load_year(pair, year):
    """Load one HistData year zip -> (uniq_min, close_of_min)."""
    if pair in ("eurusd", "gbpusd", "usdjpy", "audusd"):
        fname = f"DAT_ASCII_{pair.upper()}_M1_{year}.zip"
    else:
        fname = f"DAT_ASCII_{pair.upper()}_M1_{year}.zip"
    path = os.path.join(SRC, pair, fname)
    if not os.path.exists(path):
        return None
    with zipfile.ZipFile(path) as zf:
        member = [m for m in zf.namelist() if m.lower().endswith(".csv")][0]
        df = pd.read_csv(zf.open(member), sep=";", header=None, usecols=[0, 4], names=["dt", "c"])
    t = pd.to_datetime(df["dt"], format="%Y%m%d %H%M%S", utc=True)
    opens_min = (t.astype("int64") // 10**6 // 60).to_numpy()
    closes = df["c"].to_numpy(dtype=float)
    uniq_min, uniq_pos = np.unique(opens_min, return_index=True)
    return uniq_min, closes[uniq_pos]


def close_at(uniq_min, close_of_min, minute):
    j = np.searchsorted(uniq_min, minute)
    if j < len(uniq_min) and uniq_min[j] == minute:
        return close_of_min[j]
    return np.nan


def eval_window(uniq_min, close_of_min, year, entry_times, expiry_min=EXPIRY_MIN, no_fri=True, no_sun=True):
    """entry_times: list of NY minutes-of-day. Returns (n, wins, losses)."""
    n = w = l = 0
    first_day = dt.datetime.fromtimestamp(int(uniq_min[0]) * 60, tz=UTC).date()
    last_day = dt.datetime.fromtimestamp(int(uniq_min[-1]) * 60, tz=UTC).date()
    d = first_day
    while d <= last_day:
        wd = d.weekday()
        if no_fri and wd == 4:
            d += dt.timedelta(days=1)
            continue
        if no_sun and wd == 6:
            d += dt.timedelta(days=1)
            continue
        for m in entry_times:
            em = entry_minute_utc(d, m)
            p_entry = close_at(uniq_min, close_of_min, em - 1)
            if np.isnan(p_entry):
                continue
            p_exp = close_at(uniq_min, close_of_min, em + expiry_min - 1)
            if np.isnan(p_exp):
                continue
            n += 1
            if p_exp < p_entry:
                w += 1
            elif p_exp > p_entry:
                l += 1
        d += dt.timedelta(days=1)
    return n, w, l


def load_2026(pair):
    """Load getdata 2026 1m csv -> (uniq_min, close_of_min)."""
    path = os.path.join(ROOT, "backtest", "data", f"{pair.upper()}_1m.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, usecols=["datetime", "close"])
    t = pd.to_datetime(df["datetime"], utc=True)
    opens_min = (t.astype("int64") // 10**6 // 60).to_numpy()
    closes = df["close"].to_numpy(dtype=float)
    uniq_min, uniq_pos = np.unique(opens_min, return_index=True)
    return uniq_min, closes[uniq_pos]


def main():
    anchor = [16 * 60 + 40, 16 * 60 + 45, 16 * 60 + 50, 16 * 60 + 55]
    rows = []
    scan_rows = []
    eras = {"2000-2006": (2000, 2006), "2007-2012": (2007, 2012), "2013-2018": (2013, 2018)}

    for pair in PAIRS:
        print(f"== {pair}", flush=True)
        year_files = [f for f in os.listdir(os.path.join(SRC, pair)) if f.endswith(".zip")]
        years = sorted({int(f.split("_")[-1].split(".")[0][:4]) for f in year_files})
        era_stats = {e: [0, 0, 0] for e in eras}  # n, w, l per era
        for year in years:
            data = load_year(pair, year)
            if data is None:
                continue
            uniq_min, close_of_min = data
            n, w, l = eval_window(uniq_min, close_of_min, year, anchor)
            if n == 0:
                continue
            acc = w / n * 100
            for e, (y0, y1) in eras.items():
                if y0 <= year <= y1:
                    era_stats[e][0] += n
                    era_stats[e][1] += w
                    era_stats[e][2] += l
            rows.append({"pair": pair.upper(), "year": year, "n": n, "wins": w,
                         "losses": l, "acc": round(acc, 2)})
            print(f"   {year}: n={n:5d} acc={acc:5.1f}%", flush=True)
        # era scan: best 15-min window in NY 15:00..18:00
        for era, (y0, y1) in eras.items():
            agg = {}
            for year in years:
                if not (y0 <= year <= y1):
                    continue
                data = load_year(pair, year)
                if data is None:
                    continue
                uniq_min, close_of_min = data
                for start in range(15 * 60, 18 * 60, 5):
                    entries = [start, start + 5, start + 10, start + 15]
                    n, w, l = eval_window(uniq_min, close_of_min, year, entries)
                    agg.setdefault(start, [0, 0, 0])
                    agg[start][0] += n
                    agg[start][1] += w
                    agg[start][2] += l
            best = sorted(((w / n * 100, n, start) for start, (n, w, l) in agg.items() if n >= 60),
                          reverse=True)[:3]
            for acc, n, start in best:
                scan_rows.append({"pair": pair.upper(), "era": era, "best_window": f"{start//60}:{start%60:02d}",
                                  "acc": round(acc, 2), "n": n})
            e = era_stats[era]
            print(f"   era {era}: anchor acc={e[1]/e[0]*100:5.1f}% (n={e[0]}) best windows: " +
                  " | ".join(f"{s[2]//60}:{s[2]%60:02d} {s[0]:.1f}% (n={s[1]})" for s in best))

    # 2026 era
    for pair in PAIRS:
        data = load_2026(pair)
        if data is None:
            continue
        uniq_min, close_of_min = data
        n, w, l = eval_window(uniq_min, close_of_min, 2026, anchor)
        if n:
            print(f"== {pair} 2026: n={n} acc={w/n*100:.1f}%")
            rows.append({"pair": pair.upper(), "year": 2026, "n": n, "wins": w,
                         "losses": l, "acc": round(w / n * 100, 2)})
        agg = {}
        for start in range(15 * 60, 18 * 60, 5):
            entries = [start, start + 5, start + 10, start + 15]
            nn, ww, ll = eval_window(uniq_min, close_of_min, 2026, entries)
            agg[start] = [nn, ww, ll]
        best = sorted(((w / n * 100, n, start) for start, (n, w, l) in agg.items() if n >= 60),
                      reverse=True)[:3]
        for acc, n, start in best:
            scan_rows.append({"pair": pair.upper(), "era": "2026", "best_window": f"{start//60}:{start%60:02d}",
                              "acc": round(acc, 2), "n": n})

    pd.DataFrame(rows).to_csv(OUT1, index=False)
    pd.DataFrame(scan_rows).to_csv(OUT2, index=False)
    print("saved:", OUT1, len(rows))
    print("saved:", OUT2, len(scan_rows))


if __name__ == "__main__":
    main()
