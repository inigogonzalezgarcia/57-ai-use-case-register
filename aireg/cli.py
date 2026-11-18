"""Command line: `demo` writes the fictional Humongous Insurance register to sample_data/ and builds the outputs; `review` runs on
your own files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import report, simulate
from .checks import review, summary
from .model import load

OUTPUTS = ("report.html", "committee-pack.md", "register-review.csv", "unregistered.csv", "controls-gaps.csv", "reviews-due.csv",
           "value.csv", "departments.csv", "findings.csv", "actions.csv")


def run(data: Path, out: Path, title: str | None = None) -> dict:
    d = load(data)
    rv = review(d)
    title = title or f"{d.settings.organisation} · AI use case register review"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.html").write_text(report.render_html(d, rv, title), encoding="utf-8")
    (out / "committee-pack.md").write_text(report.pack_md(d, rv, title), encoding="utf-8")
    report.write_csv(out / "register-review.csv", rv.rows)
    report.write_csv(out / "unregistered.csv", rv.unregistered, ["name", "source", "publisher", "owner", "department", "users", "data", "last_activity"])
    report.write_csv(out / "controls-gaps.csv", rv.gaps, ["use_case", "name", "tier", "status", "control", "in_place"])
    report.write_csv(out / "reviews-due.csv", rv.reviews, ["use_case", "name", "tier", "owner", "last_review", "next_review", "state"])
    report.write_csv(out / "value.csv", rv.value)
    report.write_csv(out / "departments.csv", rv.departments, ["department", "use_cases", "score", "with_findings", "red"])
    report.write_findings(rv, out / "findings.csv")
    report.write_actions(rv, out / "actions.csv")
    return summary(d, rv)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aireg", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    dm = sub.add_parser("demo", help="write the fictional register to sample_data/ and build the outputs")
    dm.add_argument("--data", type=Path, default=Path("sample_data"))
    dm.add_argument("--out", type=Path, default=Path("output"))
    rv = sub.add_parser("review", help="build the outputs from your own files")
    rv.add_argument("data", type=Path, help="folder with register.csv and the optional exports")
    rv.add_argument("--out", type=Path, default=Path("output"))
    rv.add_argument("--title", help="title of the report and the pack")
    a = p.parse_args(argv)
    try:
        if a.cmd == "demo":
            simulate.write(a.data)
            sm = run(a.data, a.out)
        else:
            sm = run(a.data, a.out, a.title)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{sm['status']}: governance {sm['score']} % across {sm['live']} live use cases ({sm['production']} in production, {sm['pilot']} "
          f"pilots), {sm['high']} high risk, {sm['unregistered']} AI tools not in the register, {sm['reclassify']} to reclassify, "
          f"{sm['red']} red and {sm['amber']} amber findings, {sm['decisions']} decisions")
    print(f"outputs in {a.out}/: {', '.join(OUTPUTS)}")
    return 0
