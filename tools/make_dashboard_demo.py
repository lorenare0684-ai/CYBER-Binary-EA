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
    gbp = d["pairs"]["GBPUSD_M15"]
    usd = d["pairs"]["USDJPY_M15"]
    eur = d["pairs"]["EURUSD_M15"]

    html = ["<!DOCTYPE html><html><head><meta charset='utf-8'>",
            "<title>CYBER Binary EA - Quotex Signal Dashboard (demo)</title>",
            "<style>", CSS, "</style></head><body><div class='wrap'>"]
    html.append("<h1>CYBER Binary EA<span class='sub'>Quotex signal dashboard &middot; "
                "<b>DEMO - backtest data</b> &middot; generated " + d["generated"] +
                " &middot; <span class='badge'>demo mode</span></span></h1>")
    html.append("<div class='grid'>")
    html.append(card("Accuracy (GBPUSD)", f"<span class='acc'>{gbp['accuracy']}%</span>",
                     "big", f"n={gbp['trades']} trades &middot; wins/(wins+losses)"))
    html.append(card("Win rate (GBPUSD)", f"<span class='win'>{gbp['accuracy']}%</span>",
                     "num", "wins / all closed trades"))
    html.append(card("Wins / Losses (GBPUSD)",
                     f"<span class='win'>{gbp['wins']}</span> / <span class='loss'>{gbp['losses']}</span>",
                     "num", "6 months &middot; Feb-Jul 2026"))
    html.append(card("Net P&amp;L (GBPUSD)",
                     f"<span class='win'>+{gbp['net_per_stake']:.2f}</span>",
                     "num", "per 1.0 stake @ 85% payout"))
    html.append(card("Profit factor", f"<span class='gold'>{gbp['profit_factor']}</span>",
                     "num", "max drawdown " + str(gbp['max_drawdown'])))
    html.append(card("Accuracy (USDJPY)", f"<span class='acc'>{usd['accuracy']}%</span>",
                     "big", f"n={usd['trades']} trades &middot; 6 months"))
    html.append(card("Accuracy (EURUSD)", f"<span class='acc'>{eur['accuracy']}%</span>",
                     "num", f"n={eur['trades']} trades &middot; 6 months"))
    html.append("</div>")

    html.append("<div class='card'><h2>Walk-forward (same parameters, untouched windows)</h2>"
                "<table><thead><tr><th>Instrument</th><th>Feb-Apr</th><th>May-Jul (out-of-sample)</th></tr></thead><tbody>")
    for name, label in [("GBPUSD_M15", "GBPUSD M15"), ("USDJPY_M15", "USDJPY M15"),
                        ("EURUSD_M15", "EURUSD M15")]:
        wf = d["walk_forward"][name]
        a = wf["Feb-Apr"]; b = wf["May-Jul"]
        html.append(f"<tr><td>{label}</td><td>{a['accuracy']}% (n={a['trades']})</td>"
                    f"<td class='win'><b>{b['accuracy']}%</b> (n={b['trades']})</td></tr>")
    html.append("</tbody></table></div>")

    html.append("<div class='card'><h2>Monthly stability (accuracy, M15)</h2>"
                "<table><thead><tr><th>Month</th><th>GBPUSD</th><th>USDJPY</th><th>EURUSD</th></tr></thead><tbody>")
    for m in ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]:
        html.append(f"<tr><td>{m}</td><td>{d['months']['GBPUSD_M15'][m]}%</td>"
                    f"<td>{d['months']['USDJPY_M15'][m]}%</td><td>{d['months']['EURUSD_M15'][m]}%</td></tr>")
    html.append("</tbody></table></div>")

    html.append("<div class='foot'>CYBER Binary EA &middot; strategy: NY-Close Seasonal "
                "(PUT 20-21 UTC, CALL 21-23 UTC, 1h expiry on M15) &middot; "
                "the live dashboard opens automatically in your browser when the EA is attached</div>")
    html.append("</div></body></html>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(html))
    print("written:", OUT)


if __name__ == "__main__":
    main()
