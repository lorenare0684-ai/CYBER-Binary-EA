#!/usr/bin/env python3
"""Download the OHLCV datasets used by the CYBER Binary EA backtests.

Source: getdata.finance (GitHub mirror: github.com/getdata-finance).
Each repo contains one CSV (datetime, open, high, low, close, volume), UTC.

Usage:  python3 backtest/download_data.py
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

WANTED = {
    "EURUSD_1m":  "eurusd-1m-ohlcv-forex-historical-data",
    "EURUSD_5m":  "eurusd-5m-ohlcv-forex-historical-data",
    "EURUSD_15m": "eurusd-15m-ohlcv-forex-historical-data",
    "EURUSD_1h":  "eurusd-1h-ohlcv-forex-historical-data",
    "GBPUSD_1m":  "gbpusd-1m-ohlcv-forex-historical-data",
    "GBPUSD_1h":  "gbpusd-1h-ohlcv-forex-historical-data",
    "GBPUSD_30m": "gbpusd-30m-ohlcv-forex-historical-data",
    "USDJPY_1m":  "usdjpy-1m-ohlcv-forex-historical-data",
    "USDJPY_5m":  "usdjpy-5m-ohlcv-forex-historical-data",
    "USDJPY_15m": "usdjpy-15m-ohlcv-forex-historical-data",
    "XAUUSD_1m":  "xauusd-1m-ohlcv-metals-historical-data",
    "XAUUSD_5m":  "xauusd-5m-ohlcv-metals-historical-data",
}


def download(out_name: str, repo: str) -> None:
    dest = os.path.join(DATA, f"{out_name}.csv")
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"  {out_name}: already present, skipping")
        return
    for branch in ("main", "master"):
        url = f"https://codeload.github.com/getdata-finance/{repo}/zip/refs/heads/{branch}"
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                blob = r.read()
            # the zip contains a single CSV at <repo>-<branch>/<name>.csv
            import io
            import zipfile
            zf = zipfile.ZipFile(io.BytesIO(blob))
            member = [m for m in zf.namelist() if m.lower().endswith(".csv")]
            if not member:
                raise RuntimeError("no csv in archive")
            with open(dest, "wb") as f:
                f.write(zf.read(member[0]))
            print(f"  {out_name}: ok ({os.path.getsize(dest)//1024} KB)")
            return
        except Exception as e:
            last = e
    print(f"  {out_name}: FAILED ({last})")


def main():
    print("Downloading getdata.finance OHLCV datasets into", DATA)
    for out, repo in WANTED.items():
        download(out, repo)
    print("Done.")


if __name__ == "__main__":
    main()
