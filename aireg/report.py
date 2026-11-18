"""Outputs: report.html (score and tiles, decisions, the register by tier, departments, every finding by area, AI tools nobody
registered, control gaps, reviews due and value), committee-pack.md (the page for the monthly AI governance committee) and the CSVs:
register-review, unregistered, controls-gaps, reviews-due, value, departments, findings and actions."""
from __future__ import annotations

import csv
import html
from pathlib import Path

from .checks import AREAS, Review, summary
from .model import FILES, Data

e = html.escape


def write_csv(path: Path, rows: list[dict], header: list[str] | None = None) -> None:
    header = header or (list(rows[0].keys()) if rows else ["ci"])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows([{k: ("" if r.get(k) is None else r.get(k)) for k in header} for r in rows])


def write_findings(rv: Review, path: Path) -> None:
    write_csv(path, [{"severity": f.severity, "area": AREAS[f.area], "code": f.code, "subject": f.subject, "finding": f.text,
                      "items": " ".join(f.items), "owner": f.owner, "due": f.due.isoformat() if f.due else "", "action": f.action}
                     for f in rv.findings], ["severity", "area", "code", "subject", "finding", "items", "owner", "due", "action"])


def write_actions(rv: Review, path: Path) -> None:
    rows = [{"ref": f"A{n:03d}", "severity": f.severity, "action": f.action, "subject": f.subject, "owner": f.owner,
             "due": f.due.isoformat() if f.due else "", "done": ""} for n, f in enumerate(rv.findings, 1)]
    write_csv(path, rows, ["ref", "severity", "action", "subject", "owner", "due", "done"])


def _day(x) -> str:
    return "" if not x else f"{x:%d %b %Y}"


def _trend(d: Data, rv: Review) -> str:
    p = d.settings.previous_score
    if p is None:
        return ""
    diff = round(rv.score - p, 1)
    return f"{'+' if diff >= 0 else ''}{diff} points on last month ({p} %)"


def pack_md(d: Data, rv: Review, title: str) -> str:
    s, sm = d.settings, summary(d, rv)
    out = [f"# {title}", "", f"Review of {_day(s.review_date)} · {sm['live']} live use cases ({sm['production']} in production, {sm['pilot']} pilots)", "",
           f"**Result: {rv.status}** · governance **{rv.score} %**" + (f" · {_trend(d, rv)}" if _trend(d, rv) else ""), "",
           "## Headlines", "",
           f"- {sm['unregistered']} AI tool{'s' if sm['unregistered'] != 1 else ''} in use that {'are' if sm['unregistered'] != 1 else 'is'} not in the register; "
           f"{sm['prohibited']} use case{'s' if sm['prohibited'] != 1 else ''} the policy prohibits.",
           f"- {sm['high']} use cases are high risk under the policy; {sm['reclassify']} are declared in a lower tier.",
           f"- {sm['red']} red and {sm['amber']} amber findings, {sm['decisions']} decisions.", "", "## Decisions", ""]
    out += [f"{n}. **{x['decision']}** — {x['detail']} · {x['owner']} · by {_day(x['due'])}" for n, x in enumerate(rv.decisions, 1)] or ["None this month."]
    out += ["", "## The register by tier", "", "| Tier (policy) | Use cases | Production | Pilot | Idea | Declared lower |", "|---|---:|---:|---:|---:|---:|"]
    out += [f"| {t['tier']} | {t['use_cases']} | {t['production']} | {t['pilot']} | {t['idea']} | {t['declared_lower']} |" for t in rv.tiers]
    out += ["", "## Departments (lowest score first)", "", "| Department | Use cases | Score | With findings |", "|---|---:|---:|---:|"]
    out += [f"| {g['department']} | {g['use_cases']} | {g['score']} % | {g['with_findings']} |" for g in rv.departments]
    out += ["", "## Red findings", ""]
    out += [f"- **{f.code}** {f.text} → {f.action} ({f.owner}, {_day(f.due)})" for f in rv.findings if f.severity == "RED"] or ["None."]
    out += ["", "## Reviews due", "", "| Use case | Tier | Owner | Last review | Next review | State |", "|---|---|---|---|---|---|"]
    out += [f"| {r['name']} | {r['tier']} | {r['owner']} | {r['last_review']} | {r['next_review']} | {r['state']} |" for r in rv.reviews]
    if rv.untrained:
        out += ["", "## Owners without current AI training", "", ", ".join(rv.untrained)]
    out += ["", "## Sources", ""] + [f"- {FILES[k]} ({k}): {v} rows" for k, v in d.sources.items()]
    out += ["", "## Notes", "", "- The tiers and controls are this organisation's AI policy (settings.json). The review does not decide whether a law applies.",
            "- Amber findings and actions: findings.csv and actions.csv.", ""]
    return "\n".join(out)


CSS = """
:root{--bg:#f6f7f8;--card:#fff;--ink:#1b2128;--muted:#66717c;--line:#e2e5e9;--ok:#1e7a4c;--warn:#a46200;--bad:#b42318;--track:#e9ecef}
@media (prefers-color-scheme:dark){:root{--bg:#13171b;--card:#1b2127;--ink:#e7eaee;--muted:#9aa5b0;--line:#2b333b;--ok:#4cc38a;
--warn:#f0a83a;--bad:#f2685c;--track:#2b333b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:28px 18px 60px}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:34px 0 12px}
.muted{color:var(--muted)}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:20px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}.tile b{display:block;font-size:24px}
.overall{display:inline-block;margin-top:14px;padding:6px 14px;border-radius:99px;font-weight:700;border:2px solid currentColor}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}tr:last-child td{border-bottom:0}.wrap{overflow-x:auto}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pill{display:inline-block;white-space:nowrap;padding:1px 8px;border-radius:99px;font-size:12px;font-weight:600;border:1px solid currentColor}
.red{color:var(--bad)}.amber{color:var(--warn)}.green{color:var(--ok)}td.fix{font-size:13px;color:var(--muted);min-width:200px;max-width:340px}
.bar{display:inline-block;width:90px;height:8px;border-radius:4px;background:var(--track);vertical-align:middle;margin-right:8px;overflow:hidden}
.bar i{display:block;height:100%}.brk{overflow-wrap:anywhere;word-break:break-word}footer{margin-top:40px;font-size:13px}
"""


def _pill(x: str) -> str:
    return f"<span class='pill {x.lower()}'>{e(x)}</span>"


def _table(head: list[str], rows: list[str], empty: str = "Nothing to show.") -> str:
    if not rows:
        rows = [f"<tr><td colspan='{len(head)}'>{e(empty)}</td></tr>"]
    return "<div class='wrap'><table><tr>" + "".join(f"<th>{e(h)}</th>" for h in head) + "</tr>" + "".join(rows) + "</table></div>"


def _bar(score: float, s) -> str:
    cls = "ok" if score >= s.score_amber else "warn" if score >= s.score_red else "bad"
    return f"<span class='bar'><i style='width:{max(0, min(100, score)):.0f}%;background:var(--{cls})'></i></span>{score} %"


def _n(v, suffix: str = "") -> str:
    return "" if v is None else f"{v:,.0f}{suffix}" if isinstance(v, float) and v >= 100 else f"{v:g}{suffix}" if isinstance(v, (int, float)) else e(str(v))


def render_html(d: Data, rv: Review, title: str) -> str:
    s, sm = d.settings, summary(d, rv)
    h = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         f"<title>{e(title)}</title><style>{CSS}</style></head><body><main>",
         f"<h1>{e(title)}</h1><p class='muted'>Review of {_day(s.review_date)} · {sm['live']} live use cases out of {sm['uses']} in the register · "
         + ", ".join(f"{FILES[k]} ({v})" for k, v in d.sources.items()) + "</p>",
         f"<span class='overall {rv.status.lower()}'>{rv.status} · governance {rv.score} %</span>"
         + (f" <span class='muted'>{e(_trend(d, rv))}</span>" if _trend(d, rv) else ""),
         "<div class='tiles'>"]
    tiles = [("Governance", f"{rv.score} %"), ("Live use cases", sm["live"]), ("In production", sm["production"]), ("High risk", sm["high"]),
             ("Not in the register", sm["unregistered"]), ("Red findings", sm["red"]), ("Amber findings", sm["amber"]), ("Decisions", sm["decisions"])]
    h += [f"<div class='tile'><span class='muted'>{e(k)}</span><b>{e(str(v))}</b></div>" for k, v in tiles] + ["</div>"]
    h.append("<h2>Decisions</h2>")
    h.append(_table(["Decision", "Detail", "Owner", "Due"], [f"<tr><td><b>{e(x['decision'])}</b></td><td class='brk'>{e(x['detail'])}</td>"
                    f"<td>{e(x['owner'])}</td><td class='num'>{_day(x['due'])}</td></tr>" for x in rv.decisions], "No decisions this month."))
    h.append("<h2>The register by tier</h2>")
    h.append(_table(["Tier (policy)", "Use cases", "Production", "Pilot", "Idea", "Declared lower"], [f"<tr><td>{e(t['tier'])}</td>"
                    f"<td class='num'>{t['use_cases']}</td><td class='num'>{t['production']}</td><td class='num'>{t['pilot']}</td>"
                    f"<td class='num'>{t['idea']}</td><td class='num'>{t['declared_lower']}</td></tr>" for t in rv.tiers]))
    h.append("<h2>Departments</h2>")
    h.append(_table(["Department", "Use cases", "Score", "With findings", "In a red finding"], [f"<tr><td>{e(g['department'])}</td>"
                    f"<td class='num'>{g['use_cases']}</td><td>{_bar(g['score'], s)}</td><td class='num'>{g['with_findings']}</td>"
                    f"<td class='num'>{g['red']}</td></tr>" for g in rv.departments]))
    for area, label in AREAS.items():
        fs = [f for f in rv.findings if f.area == area]
        h.append(f"<h2>{e(label)} <span class='muted'>({len(fs)})</span></h2>")
        h.append(_table(["", "Code", "Finding", "Action", "Owner", "Due"], [f"<tr><td>{_pill(f.severity)}</td><td class='num'>{e(f.code)}</td>"
                        f"<td class='brk'>{e(f.text)}</td><td class='fix'>{e(f.action)}</td><td>{e(f.owner)}</td><td class='num'>{_day(f.due)}</td></tr>"
                        for f in fs], "Nothing to report."))
    h.append("<h2>AI in use, not in the register</h2>")
    h.append(_table(["Name", "Found by", "Publisher", "Owner", "Department", "Users", "Data", "Last activity"], [f"<tr><td>{e(u['name'])}</td>"
                    f"<td>{e(u['source'])}</td><td>{e(u['publisher'])}</td><td>{e(u['owner'])}</td><td>{e(u['department'])}</td>"
                    f"<td class='num'>{u['users']}</td><td>{e(u['data'])}</td><td class='num'>{e(u['last_activity'])}</td></tr>" for u in rv.unregistered],
                    "Everything discovery finds is in the register."))
    h.append("<h2>Reviews due in the next 60 days</h2>")
    h.append(_table(["Use case", "Tier", "Owner", "Last review", "Next review", "State"], [f"<tr><td>{e(r['name'])}</td><td>{e(r['tier'])}</td>"
                    f"<td>{e(r['owner'])}</td><td class='num'>{e(r['last_review'])}</td><td class='num'>{e(r['next_review'])}</td><td>{e(r['state'])}</td></tr>"
                    for r in rv.reviews], "No reviews due."))
    h.append("<h2>Value</h2>")
    h.append(_table(["Use case", "Status", "Cost / month", "Adoption", "Hours saved / month", "Of the estimate", "Business case"],
                    [f"<tr><td>{e(v['name'])}</td><td>{e(v['status'])}</td><td class='num'>{_n(v['monthly_cost'], ' €')}</td>"
                     f"<td class='num'>{'' if v['adoption_pct'] is None else _n(v['adoption_pct'], ' %')}</td><td class='num'>{_n(v['measured_hours'])}</td>"
                     f"<td class='num'>{'' if v['value_pct'] is None else _n(v['value_pct'], ' %')}</td><td>{e(v['business_case'])}</td></tr>"
                     for v in rv.value if any(v[k] is not None for k in ("monthly_cost", "adoption_pct", "measured_hours")) or v['business_case'] == 'no']))
    h.append("<footer class='muted'>Score per use case: the register fields filled in, the controls its tier needs in place, the tier declared "
             "as the policy gives it and the review on time. The tiers and the controls are this organisation's AI policy (settings.json); "
             "the review does not decide whether a law applies. register-review.csv has every use case.</footer></main></body></html>")
    return "\n".join(h)
