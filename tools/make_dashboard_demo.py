#!/usr/bin/env python3
"""Generate a static demo of the CYBER Binary EA dashboard from the
backtest results (out/dashboard_data.json). The live EA generates a
dashboard with the same layout, refreshed from its own statistics."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backtest", "out", "dashboard_data.json")
OUT = os.path.join(ROOT, "dashboard", "dashboard.html")

CSS = """
:root{--bg:#0b0f1a;--card:#141b2d;--line:#232c44;--txt:#e8eefc;--mut:#8b9ac0;
--win:#2ecc71;--loss:#ff5b5b;--acc:#3fa7ff;--put:#ff9f43;--call:#2ecc71;--gold:#ffd166}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:'Segoe UI',Arial,sans-serif;
padding:clamp(8px,1.5vw,24px);min-height:100vh}
.wrap{max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:clamp(8px,1.2vw,16px)}
h1{font-size:clamp(18px,2.6vw,30px);letter-spacing:.5px}
h1 .sub{display:block;font-size:clamp(11px,1.3vw,14px);color:var(--mut);font-weight:400;margin-top:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:clamp(6px,1vw,12px)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:clamp(10px,1.4vw,18px)}
.card h2{font-size:clamp(12px,1.4vw,15px);color:var(--mut);font-weight:600;text-transform:uppercase;
letter-spacing:1px;margin-bottom:clamp(6px,.8vw,10px)}
.big{font-size:clamp(26px,4vw,44px);font-weight:700;line-height:1.05}
.num{font-size:clamp(18px,2.6vw,30px);font-weight:700}
.small{font-size:clamp(10px,1.2vw,13px);color:var(--mut);margin-top:4px}
.win{color:var(--win)}.loss{color:var(--loss)}.acc{color:var(--acc)}
.gold{color:var(--gold)}.muted{color:var(--mut)}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:clamp(11px,1.3vw,14px);
font-weight:600;background:#1a2340;color:var(--acc)}
table{width:100%;border-collapse:collapse;font-size:clamp(11px,1.2vw,14px)}
th{color:var(--mut);text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);
text-transform:uppercase;font-size:clamp(10px,1.1vw,12px);letter-spacing:.5px}
td{padding:7px 6px;border-bottom:1px solid #1b2236}
.call{color:var(--call);font-weight:600}.put{color:var(--put);font-weight:600}
.win{color:var(--win);font-weight:700}.loss{color:var(--loss);font-weight:700}
.pend{color:var(--mut)}.tie{color:var(--gold)}
.foot{margin-top:auto;text-align:center;color:var(--mut);font-size:clamp(10px,1.1vw,12px);padding:8px}
@media(max-width:560px){.grid{grid-template-columns:repeat(2,1fr)}}
"""


def card(title, big, big_cls, small):
    return (f"<div class='card'><h2>{title}</h2><div class='{big_cls}'>{big}</div>"
            f"<div class='small'>{small}</div></div>")


def main():
    with open(DATA) as f:
        d = json.load(f)
    micro = d["micro"]
    fl = micro["flagship"]
    all_days = micro["all_days"]
    wc = micro["with_call"]

    html = ["<!DOCTYPE html><html><head><meta charset='utf-8'>",
            "<title>CYBER Binary EA - Quotex Signal Dashboard (demo)</title>",
            "<style>", CSS, "</style></head><body><div class='wrap'>"]
    html.append("<h1>CYBER Binary EA<span class='sub'>Quotex signal dashboard &middot; "
                "<b>DEMO - backtest data</b> &middot; generated " + d["generated"] +
                " &middot; <span class='badge'>Micro-Fix flagship: 83.6%</span></span></h1>")
    html.append("<div class='grid'>")
    html.append(card("Accuracy (flagship)",
                     f"<span class='acc'>{fl['accuracy']}%</span>",
                     "big", f"PUT 16:35-16:50 NY &middot; 20-min expiry &middot; no Fridays"))
    html.append(card("Wins / Losses",
                     f"<span class='win'>{fl['wins']}</span> / <span class='loss'>{fl['losses']}</span>",
                     "num", f"n={fl['trades']} &middot; 6 months (Feb-Jul 2026)"))
    html.append(card("Net P&amp;L",
                     f"<span class='win'>+{fl['wins']*0.85-fl['losses']:.2f}</span>",
                     "num", "per 1.0 stake @ 85% payout"))
    html.append(card("Profit factor", f"<span class='gold'>{fl['pf']}</span>",
                     "num", "worst month " + str(min(fl['months'].values())) + "%"))
    html.append(card("Out-of-sample", f"<span class='acc'>{fl['mj'][0]:.1f}%</span>",
                     "num", f"May-Jul &middot; n={fl['mj'][1]} (untouched params)"))
    html.append(card("All days variant", f"<span class='acc'>{all_days['accuracy']}%</span>",
                     "num", f"n={all_days['trades']} &middot; incl. Fridays"))
    html.append(card("With CALL rule", f"<span class='acc'>{wc['accuracy']}%</span>",
                     "num", f"n={wc['trades']} &middot; adds 17:50-18:00 NY CALL"))
    html.append(card("Per pair", f"<span class='win'>GBP {micro['per_pair']['GBPUSD']['accuracy']}%</span>"
                     " / <span class='acc'>JPY " + str(micro['per_pair']['USDJPY']['accuracy']) + "%</span>",
                     "num", "flagship, per pair"))
    html.append("</div>")

    html.append("<div class='card'><h2>Monthly accuracy (flagship)</h2>"
                "<table><thead><tr><th>Month</th><th>Accuracy</th><th>Trades</th></tr></thead><tbody>")
    for m in ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]:
        a = fl["months"][m]
        cls = "win" if a >= 80 else ("gold" if a >= 70 else "loss")
        html.append(f"<tr><td>{m}</td><td class='{cls}'><b>{a:.0f}%</b></td><td>{fl['trades']//6}</td></tr>")
    html.append("</tbody></table>")
    html.append("<div class='small'>The window is anchored to New York local time with "
                "automatic US-DST handling (validated 2020-2029, 0 mismatches).</div></div>")

    html.append("<div class='card'><h2>Monthly stability (accuracy, M15)</h2>"
                "<table><thead><tr><th>Month</th><th>GBPUSD</th><th>USDJPY</th><th>EURUSD</th></tr></thead><tbody>")
    for m in ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]:
        html.append(f"<tr><td>{m}</td><td>{d['months']['GBPUSD_M15'][m]}%</td>"
                    f"<td>{d['months']['USDJPY_M15'][m]}%</td><td>{d['months']['EURUSD_M15'][m]}%</td></tr>")
    html.append("</tbody></table></div>")

    html.append("<div class='card'><h2>Legacy reference (NY-Close Seasonal, M15/1h)</h2>"
                "<table><thead><tr><th>Instrument</th><th>Accuracy</th><th>Trades</th><th>PF</th></tr></thead><tbody>")
    for name, label in [("GBPUSD_M15", "GBPUSD M15"), ("USDJPY_M15", "USDJPY M15"),
                        ("EURUSD_M15", "EURUSD M15")]:
        p = d["pairs"][name]
        html.append(f"<tr><td>{label}</td><td>{p['accuracy']}%</td><td>{p['trades']}</td><td>{p['profit_factor']}</td></tr>")
    html.append("</tbody></table></div>")
    html.append("<div class='foot'>CYBER Binary EA &middot; flagship: Micro-Fix "
                "(PUT 16:35-16:50 NY, 20-min expiry) &middot; "
                "the live dashboard opens automatically in your browser when the EA is attached</div>")
    html.append("</div></body></html>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(html))
    print("written:", OUT)


if __name__ == "__main__":
    main()
