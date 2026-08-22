#!/usr/bin/env python3
"""Generate a static demo of the CYBER Binary EA dashboard from the
backtest results (out/dashboard_data.json). The live EA generates a
dashboard with the same layout, refreshed from its own statistics."""
import json
import os

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
    no_mon = micro["no_monday"]
    wc = micro["with_call"]
    all_days = micro["all_days"]
    pp = micro["per_pair"]

    html = ["<!DOCTYPE html><html><head><meta charset='utf-8'>",
            "<title>CYBER Binary EA - Quotex Signal Dashboard (demo)</title>",
            "<style>", CSS, "</style></head><body><div class='wrap'>"]
    html.append("<h1>CYBER Binary EA<span class='sub'>Quotex signal dashboard &middot; "
                "<b>DEMO - backtest data</b> &middot; generated " + d["generated"] +
                " &middot; <span class='badge'>Micro-Fix flagship: 86.6%</span></span></h1>")
    html.append("<div class='grid'>")
    html.append(card("Accuracy (flagship)",
                     f"<span class='acc'>{fl['accuracy']}%</span>",
                     "big", "PUT 16:35-16:50 NY &middot; 25-min expiry &middot; 4 assets &middot; no Fridays"))
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
    html.append(card("Signals / day", f"<span class='num'>16</span>",
                     "num", "4 assets &times; 4 bars &middot; Mon-Thu"))
    html.append(card("Skip Mondays", f"<span class='acc'>{no_mon['accuracy']}%</span>",
                     "num", f"n={no_mon['trades']} &middot; +1.1 pp"))
    html.append(card("With CALL rule", f"<span class='acc'>{wc['accuracy']}%</span>",
                     "num", f"n={wc['trades']} &middot; adds 17:50-18:00 NY CALL"))
    html.append("</div>")

    html.append("<div class='card'><h2>Per-asset accuracy (flagship)</h2>"
                "<table><thead><tr><th>Asset</th><th>Accuracy</th><th>Trades</th></tr></thead><tbody>")
    for name, label in [("EURJPY", "EURJPY - BEST"), ("GBPUSD", "GBPUSD"), ("USDJPY", "USDJPY"),
                        ("EURGBP", "EURGBP"), ("AUDUSD", "AUDUSD"), ("EURUSD", "EURUSD")]:
        p = pp[name]
        cls = "win" if p["accuracy"] >= 85 else ("gold" if p["accuracy"] >= 75 else "loss")
        html.append(f"<tr><td>{label}</td><td class='{cls}'><b>{p['accuracy']}%</b></td><td>{p['trades']}</td></tr>")
    html.append("</tbody></table></div>")

    html.append("<div class='card'><h2>Monthly accuracy (flagship)</h2>"
                "<table><thead><tr><th>Month</th><th>Accuracy</th></tr></thead><tbody>")
    for m in ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]:
        a = fl["months"][m]
        cls = "win" if a >= 85 else ("gold" if a >= 75 else "loss")
        html.append(f"<tr><td>{m}</td><td class='{cls}'><b>{a:.0f}%</b></td></tr>")
    html.append("</tbody></table>")
    html.append("<div class='small'>Windows anchored to New York local time with automatic "
                "US-DST handling (validated 2020-2029, 0 mismatches).</div></div>")

    html.append("<div class='card'><h2>Variants</h2>"
                "<table><thead><tr><th>Variant</th><th>Trades</th><th>Accuracy</th><th>PF</th></tr></thead><tbody>")
    for key, label in [("flagship", "4 assets, no Fridays (default)"),
                       ("no_monday", "Flagship + skip Mondays"),
                       ("with_call", "PUT + CALL rule"),
                       ("with_aud", "5 assets (incl. AUDUSD)"),
                       ("all_days", "4 assets, all days")]:
        v = micro[key]
        html.append(f"<tr><td>{label}</td><td>{v['trades']}</td>"
                    f"<td class='win'><b>{v['accuracy']}%</b></td><td>{v['pf']}</td></tr>")
    html.append("</tbody></table></div>")

    html.append("<div class='foot'>CYBER Binary EA &middot; flagship: Micro-Fix "
                "(PUT 16:35-16:50 NY, 25-min expiry, EURJPY/GBPUSD/USDJPY/EURGBP) &middot; "
                "the live dashboard opens automatically in your browser when the EA is attached</div>")
    html.append("</div></body></html>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(html))
    print("written:", OUT)


if __name__ == "__main__":
    main()
