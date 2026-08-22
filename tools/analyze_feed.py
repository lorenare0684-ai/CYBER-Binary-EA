#!/usr/bin/env python3
"""Analyze a broker's EURJPY M5 history export (from CYBER_Export_History.mq5)
against the research data.

Usage:
    python3 tools/analyze_feed.py <broker_csv> [--pair EURJPY]

Output:
  - basic bar stats (range, gaps)
  - the NY window profile (PUT, 20-min expiry, 15-min NY slots 14:00-18:00)
    under BOTH the broker's claimed offset and the offset detected by
    matching prices against the real market data
  - the EA-equivalent painted-history statistics for the configured window
    (16:40-16:45 NY, 4-bar expiry, Friday skip) - should reproduce the
    on-chart panel numbers
  - a verdict: real feed (and true server offset) vs synthetic/OTC feed
"""
import sys, datetime
import pandas as pd

sys.path.insert(0, "backtest")
from engine import load_csv, resample

# ---------------------------------------------------------------------------
# US-DST helpers (identical to the EA: naive UTC timestamps)
# ---------------------------------------------------------------------------
def mql_is_dst(y, mon, day, hour, minute):
    if mon < 3 or mon > 11:
        return False
    if 3 < mon < 11:
        return True
    def wd(y, m, d):
        return (datetime.date(y, m, d).weekday() + 1) % 7
    if mon == 3:
        ss = 8 + ((7 - wd(y, 3, 1)) % 7)
        return (day * 1440 + hour * 60 + minute) >= (ss * 1440 + 7 * 60)
    fs = 1 + ((7 - wd(y, 11, 1)) % 7)
    return (day * 1440 + hour * 60 + minute) < (fs * 1440 + 6 * 60)

def ny_minute(utc_dt):
    off = -4 if mql_is_dst(utc_dt.year, utc_dt.month, utc_dt.day,
                           utc_dt.hour, utc_dt.minute) else -5
    t = utc_dt + datetime.timedelta(hours=off)
    return t.hour * 60 + t.minute, t.weekday()

# ---------------------------------------------------------------------------
# Load the broker export
# ---------------------------------------------------------------------------
def load_broker_csv(path):
    meta = {}
    with open(path) as f:
        first = f.readline()
        if first.startswith("#"):
            pass
    raw = pd.read_csv(path, comment="#")
    cols = {c.lower().strip(): c for c in raw.columns}
    tcol = cols.get("time(server)") or cols.get("time")
    ccol = cols.get("close")
    ocol = cols.get("open")
    times = pd.to_datetime(raw[tcol])
    closes = raw[ccol].astype(float)
    opens = raw[ocol].astype(float) if ocol else None
    # meta from comment rows
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                parts = line.strip().lstrip("#").split(",")
                if parts and parts[0] in ("offset_hours", "export_gmt", "bars"):
                    meta[parts[0]] = ",".join(parts[1:])
    return times, closes, opens, meta

# ---------------------------------------------------------------------------
# Window profile: PUT +20min, exact-expiry, NY 15-min slots 14:00-18:00
# ---------------------------------------------------------------------------
def window_profile(times, closes, utc_offset_h):
    """times: naive broker server timestamps; utc_offset_h: server-GMT hours."""
    n = len(times)
    prof = {}
    wins = losses = 0
    for shift in range(n - 4):
        sv = times[shift].to_pydatetime()
        utc = sv - datetime.timedelta(hours=utc_offset_h)
        ny_m, wd = ny_minute(utc)
        if wd == 4:
            continue
        if not (840 <= ny_m < 1080):
            continue
        exp = sv + datetime.timedelta(minutes=20)
        if times[shift + 4].to_pydatetime() != exp:
            continue
        b = (ny_m - 840) // 15
        s = prof.setdefault(b, [0, 0])
        if closes[shift + 4] < closes[shift]:
            s[0] += 1
        elif closes[shift + 4] > closes[shift]:
            s[1] += 1
    return prof

def prof_str(prof):
    out = []
    best = None
    for b in sorted(prof):
        w, l = prof[b]
        nb = w + l
        a = 100.0 * w / nb
        st = 840 + 15 * b
        out.append(f"{st//60:02d}:{st%60:02d} {a:5.1f}% (n={nb})")
        if nb >= 8 and (best is None or a > best[0]):
            best = (a, b, nb)
    return " | ".join(out), best

# ---------------------------------------------------------------------------
# EA-equivalent configured-window stats (16:40-16:45 NY, 4-bar, Fri skip)
# ---------------------------------------------------------------------------
def ea_stats(times, closes, utc_offset_h):
    n = len(times)
    w = l = t = 0
    for shift in range(1, n - 4):
        sv = times[shift].to_pydatetime()
        utc = sv - datetime.timedelta(hours=utc_offset_h)
        ny_m, wd = ny_minute(utc)
        if wd == 4:
            continue
        if not (1000 <= ny_m <= 1005):
            continue
        exp = sv + datetime.timedelta(minutes=20)
        if times[shift + 4].to_pydatetime() != exp:
            continue
        t += 1
        if closes[shift + 4] < closes[shift]:
            w += 1
        elif closes[shift + 4] > closes[shift]:
            l += 1
    return t, w, l

# ---------------------------------------------------------------------------
# Offset detection: match closes against the real market data
# ---------------------------------------------------------------------------
def detect_offset(times, closes, real_times, real_closes, claimed):
    real = dict(zip(real_times, real_closes))
    # sample for speed: every 25th bar, middle section
    step = 25
    start = len(times) // 10
    cands = [round(claimed, 1)]
    for k in [x / 2.0 for x in range(-10, 19)]:      # -5.0 .. +9.0 step 0.5
        cands.append(k)
    results = []
    for k in sorted(set(cands)):
        ok = tot = 0
        diffs = []
        for i in range(start, len(times), step):
            utc = (times[i] - pd.Timedelta(hours=k)).round("5min")
            if utc not in real:
                continue
            tot += 1
            d = abs(closes[i] - real[utc])
            if d <= max(0.0003, 0.0003 * real[utc]):
                ok += 1
            diffs.append(d)
        if tot >= 50:
            med = sorted(diffs)[len(diffs) // 2]
            results.append((ok / tot, tot, med, k))
    results.sort(reverse=True)
    return results

# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]

    times, closes, opens, meta = load_broker_csv(path)
    claimed = float(meta.get("offset_hours", "0") or 0)
    print(f"Broker file: {path}")
    print(f"  bars: {len(times)} | range: {times.iloc[0]} .. {times.iloc[-1]}")
    print(f"  claimed server offset: {claimed:+.2f}h | export GMT: {meta.get('export_gmt','?')}")
    gaps = times.diff().dt.total_seconds().dropna()
    print(f"  bar gaps > 5min: {(gaps > 305).sum()} (max {gaps.max()/60:.0f} min)")

    # --- profile under the claimed offset (what the EA used) ----------------
    prof = window_profile(times, closes.values, claimed)
    prof_line, best = prof_str(prof)
    print(f"\nNY window profile under CLAIMED offset {claimed:+.1f}h (what the EA used):")
    print("  " + prof_line)
    if best:
        print(f"  best slot: {best[0]:.1f}% (n={best[2]})")

    # --- EA-equivalent stats (should match the on-chart panel) --------------
    t, w, l = ea_stats(times, closes.values, claimed)
    acc = 100.0 * w / (w + l) if w + l else 0.0
    print(f"\nEA-equivalent painted stats (16:40-16:45 NY, 20-min, Fri skip): "
          f"{w}W/{l}L (n={t}) acc={acc:.1f}%  [panel comparison: 123W/151L, 44.9%]")

    # --- real market data ----------------------------------------------------
    dd = resample(load_csv("backtest/data/EURJPY_1m.csv"), "5min")
    real_times = pd.to_datetime(dd["dt"])
    if getattr(real_times, "tz", None) is not None:
        real_times = real_times.tz_localize(None)
    real_closes = dd["c"]

    # --- offset detection ----------------------------------------------------
    print("\nOffset detection (matching closes against real market data):")
    res = detect_offset(times, closes.values, real_times, real_closes, claimed)
    for frac, tot, med, k in res[:6]:
        print(f"  offset {k:+5.1f}h: match {100*frac:5.1f}% (n={tot}, median |diff| {med:.4f})")
    if res and res[0][0] >= 0.8:
        true_k = res[0][3]
        print(f"\n-> FEED IS REAL. True server offset ≈ {true_k:+.1f}h "
              f"(EA used {claimed:+.1f}h)")
        prof2 = window_profile(times, closes.values, true_k)
        prof2_line, best2 = prof_str(prof2)
        print(f"\nNY window profile under DETECTED offset {true_k:+.1f}h:")
        print("  " + prof2_line)
        if best2:
            print(f"  best slot: {best2[0]:.1f}% (n={best2[2]})")
        t2, w2, l2 = ea_stats(times, closes.values, true_k)
        acc2 = 100.0 * w2 / (w2 + l2) if w2 + l2 else 0.0
        print(f"  configured-window accuracy at true offset: {w2}W/{l2}L (n={t2}) acc={acc2:.1f}%")
        if abs(true_k - claimed) > 0.25:
            print("  -> MISMATCH: the EA's server-offset assumption is off; the windows")
            print("     fire at the wrong time of day on this feed. Fixable.")
        else:
            print("  -> offset matches the EA's assumption - see profile above.")
    else:
        print("\n-> FEED IS NOT THE REAL MARKET (no offset matches prices).")
        print("   Likely an OTC/synthetic feed: the NY settlement pattern is absent,")
        print("   so the 90%+ edge does not apply on this symbol/feed.")

if __name__ == "__main__":
    main()
