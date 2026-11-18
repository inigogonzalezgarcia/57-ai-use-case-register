"""The review: every AI use case in the register against the organisation's AI policy (settings.json), what discovery finds in the
tenant, the people directory and the AI incidents. Register (AI in use that nobody registered, gaps, owners who left), risk (the
tier the policy gives each use case against the one declared, practices the policy prohibits, incidents), controls (what each tier
needs: oversight, DPIA, risk assessment, tests, logging, vendor DPA, transparency notice, trained owner; reviews on time), data and
vendors (data classes a tool is not approved for, vendors that train on the data) and value (pilots with no decision, no business
case, licences nobody uses, hours saved below the estimate). Each finding has a severity, an owner and a due date; a governance
score per use case and department; and the choices become decisions."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from .model import CONTROLS, TIER_LABEL, TIERS, Data, Person, UseCase, _norm, key

AREAS = {"register": "Register", "risk": "Risk", "controls": "Controls", "data": "Data and vendors", "value": "Value"}
SENSITIVE = {"confidential", "personal", "special"}
FIELDS = {"owner": "owner", "purpose": "purpose", "tool": "tool", "data": "data classes", "declared": "declared tier", "audience": "audience"}


@dataclass
class Finding:
    code: str
    severity: str              # RED or AMBER
    area: str
    subject: str
    text: str
    items: list[str] = field(default_factory=list)
    owner: str = ""
    due: date | None = None
    action: str = ""


@dataclass
class Review:
    findings: list[Finding] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)            # one per use case
    unregistered: list[dict] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    reviews: list[dict] = field(default_factory=list)
    value: list[dict] = field(default_factory=list)
    departments: list[dict] = field(default_factory=list)
    tiers: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    untrained: list[str] = field(default_factory=list)
    score: float = 0.0
    status: str = "GREEN"


def low(x: str) -> str:
    """'Risk assessment' -> 'risk assessment', 'DPIA' stays 'DPIA'."""
    return x if x[:2].isupper() else x[:1].lower() + x[1:]


def _due(rd: date, sev: str) -> date:
    return rd + timedelta(days=7 if sev == "RED" else 30)


def _months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            pass
    return d


def _matches(area: str, phrases: list) -> str:
    for p in phrases:
        if _norm(p) and (_norm(p) == area or _norm(p) in area):
            return p
    return ""


def classify(u: UseCase, s) -> tuple[str, str]:
    """The tier the policy gives a use case, and why."""
    hit = _matches(u.area, s.prohibited)
    if hit:
        return "prohibited", f"policy prohibits {hit}"
    hit = _matches(u.area, s.high_risk_areas)
    if hit:
        return "high", f"high-risk area in the policy: {hit}"
    if u.audience in ("customers", "public"):
        return "limited", f"{u.audience} talk to it or see what it produces"
    if u.decides:
        return "limited", f"its output feeds decisions about {u.decides}"
    return "minimal", "internal use, no decisions about people"


def required(u: UseCase, t: str, s, has_people: bool) -> list[str]:
    """The controls the policy asks of this tier, the ones that apply to this use case."""
    out = []
    for c in s.controls.get(t, []):
        if c == "dpa" and not u.vendor:
            continue
        if c == "notice" and t == "high" and u.audience == "staff" and not u.decides:
            continue
        if c == "training" and not has_people:
            continue
        out.append(c)
    return out


def control_ok(c: str, u: UseCase, people: dict[str, Person], s, rd: date) -> bool:
    if c == "owner":
        p = people.get(key(u.owner))
        return bool(u.owner) and (not people or (p is not None and p.enabled))
    if c == "training":
        p = people.get(key(u.owner))
        return p is not None and p.trained is not None and _months(p.trained, s.training_months) >= rd
    return bool(u.controls.get(c)) and _norm(u.controls.get(c)) not in ("no", "n", "false", "0", "none", "-", "n/a", "na", "pending", "todo", "missing")


def review(d: Data) -> Review:
    s = d.settings
    rd = s.review_date
    rv = Review()
    people = {key(p.id): p for p in d.people}
    people.update({key(p.name): p for p in d.people if p.name and key(p.name) not in people})
    has_people = bool(d.people)
    live = [u for u in d.uses if u.status != "retired"]
    active = [u for u in live if u.status in ("pilot", "production")]
    by_id = {u.id: u for u in d.uses}
    per_use: dict[str, list[str]] = defaultdict(list)
    missed: dict[str, int] = Counter()
    tiers = {u.id: classify(u, s) for u in d.uses}

    def add(f: Finding, uses: list[str] | None = None) -> None:
        f.due = f.due or _due(rd, f.severity)
        rv.findings.append(f)
        for i in uses if uses is not None else f.items:
            per_use[i].append(f.code)

    # --- register: AI in the tenant that nobody registered
    names = {key(u.name) for u in d.uses} | {key(u.tool) for u in d.uses if u.tool}
    for f in d.found:
        if key(f.name) in names:
            continue
        sens = [c for c in f.data if c in SENSITIVE]
        sev = "RED" if f.users >= s.shadow_users_red or sens else "AMBER"
        rv.unregistered.append({"name": f.name, "source": f.source, "publisher": f.publisher, "owner": f.owner, "department": f.department,
                                "users": f.users, "data": ", ".join(f.data), "last_activity": f.last.isoformat() if f.last else ""})
        add(Finding("REG-UNREGISTERED", sev, "register", f.name,
                    f"{f.name} ({f.source}{', ' + f.publisher if f.publisher else ''}) is in use by {f.users} people"
                    + (f" with {', '.join(sens)} data" if sens else "") + " and is not in the register",
                    [], s.owners.get("register", ""), action="Register it with an owner and a tier, or block it"), [])

    # --- register: gaps and owners who left
    for u in active:
        gaps = [label for k, label in FIELDS.items() if not getattr(u, k)]
        if gaps:
            t = tiers[u.id][0]
            add(Finding("REG-MISSING", "RED" if t in ("high", "prohibited") else "AMBER", "register", u.id,
                        f"{u.name}: no {', '.join(gaps)}", [u.id], u.owner or s.owners.get("register", ""),
                        action="Complete the register entry"))
            missed[u.id] += len(gaps)
    if has_people:
        gone = defaultdict(list)
        for u in live:
            p = people.get(key(u.owner))
            if u.owner and (p is None or not p.enabled):
                gone[u.owner].append(u.id)
        for owner, ids in sorted(gone.items()):
            sev = "RED" if any(tiers[i][0] in ("high", "prohibited") and by_id[i].status == "production" for i in ids) else "AMBER"
            add(Finding("REG-OWNER-LEFT", sev, "register", owner,
                        f"{owner} is no longer in the directory and owns {len(ids)} use case{'s' if len(ids) > 1 else ''}: "
                        + ", ".join(by_id[i].name for i in ids), ids, s.owners.get("register", ""), action="Name a new owner"))

    # --- risk: tiers, prohibited practices, incidents
    for u in live:
        t, why = tiers[u.id]
        if t == "prohibited":
            add(Finding("RISK-PROHIBITED", "RED", "risk", u.id, f"{u.name} ({u.status}): {why}", [u.id], s.owners.get("register", ""),
                        action="Stop it and record the decision"))
            missed[u.id] += 1
        elif u.declared and TIERS.index(u.declared) < TIERS.index(t):
            add(Finding("RISK-TIER", "RED" if t == "high" else "AMBER", "risk", u.id,
                        f"{u.name} is declared {u.declared} risk and the policy makes it {t} risk: {why}",
                        [u.id], u.owner or s.owners.get("register", ""), action=f"Reclassify it as {t} risk and add the controls"))
            missed[u.id] += 1
    known = {u.id for u in d.uses} | {key(u.name) for u in d.uses}
    for i in d.incidents:
        u = by_id.get(i.use) or next((x for x in d.uses if key(x.name) == key(i.use)), None)
        if i.open and i.opened and (rd - i.opened).days > s.incident_days:
            sev = "RED" if i.severity.startswith(("high", "crit", "1", "p1")) else "AMBER"
            add(Finding("RISK-INCIDENT", sev, "risk", i.id, f"{i.id} on {u.name if u else i.use or 'no use case'} open for {(rd - i.opened).days} days: {i.summary}",
                        [u.id] if u else [], (u.owner if u else "") or s.owners.get("register", ""), action="Close it or escalate it to the AI governance committee"))
        if u and u.status == "production" and i.opened and (not u.reviewed or i.opened > u.reviewed):
            add(Finding("RISK-REVIEW-AFTER", "AMBER", "risk", u.id, f"{u.name} had incident {i.id} ({i.opened:%d %b}) after its last review",
                        [u.id], u.owner or s.owners.get("register", ""), action="Review it again before the next cycle"))
        if i.use and i.use not in known and key(i.use) not in known:
            add(Finding("REG-MISSING", "AMBER", "register", i.id, f"Incident {i.id} is logged against {i.use}, which is not in the register", [],
                        s.owners.get("register", ""), action="Register the use case or fix the incident"), [])

    # --- controls: what each tier needs, and reviews on time
    for u in active:
        t = tiers[u.id][0]
        if t == "prohibited":
            continue
        need = required(u, t, s, has_people)
        miss = [c for c in need if not control_ok(c, u, people, s, rd)]
        for c in need:
            rv.gaps.append({"use_case": u.id, "name": u.name, "tier": TIER_LABEL[t], "status": u.status, "control": CONTROLS.get(c, c),
                            "in_place": "yes" if c not in miss else "no"})
        if miss:
            sev = "RED" if t == "high" and u.status == "production" and any(c not in ("training",) for c in miss) else "AMBER"
            add(Finding("CTRL-MISSING", sev, "controls", u.id, f"{u.name} ({t} risk, {u.status}): no "
                        + ", ".join(low(CONTROLS.get(c, c)) for c in miss), [u.id], u.owner or s.owners.get("register", ""),
                        action="Put the missing controls in place" + (" before it goes live" if u.status == "pilot" else "")))
            missed[u.id] += len(miss)
        months = s.review_months.get(t, 12)
        base = u.reviewed or u.started
        nxt = _months(base, months) if base else None
        state = "never reviewed" if not base else "overdue" if nxt < rd else f"due in {(nxt - rd).days} days"
        if not base or nxt <= rd + timedelta(days=60):
            rv.reviews.append({"use_case": u.id, "name": u.name, "tier": TIER_LABEL[t], "owner": u.owner,
                               "last_review": u.reviewed.isoformat() if u.reviewed else "", "next_review": nxt.isoformat() if nxt else "", "state": state})
        if not base or nxt < rd:
            add(Finding("CTRL-REVIEW", "RED" if t == "high" else "AMBER", "controls", u.id,
                        f"{u.name}: {state}" + (f" (last {u.reviewed:%d %b %Y}, every {months} months for {t} risk)" if u.reviewed else
                                                f" (in {u.status} since {u.started:%d %b %Y}, every {months} months for {t} risk)" if base else ""),
                        [u.id], u.owner or s.owners.get("register", ""), action="Review it with its owner"))
            missed[u.id] += 1
    if has_people:
        untrained = sorted({u.owner for u in active if tiers[u.id][0] in ("high", "limited") and u.owner and people.get(key(u.owner))
                            and people[key(u.owner)].enabled and not control_ok("training", u, people, s, rd)})
        # (owners are already in CTRL-MISSING; this line is the list HR and the AI lead need)
        rv.untrained = untrained
    else:
        rv.untrained = []

    # --- data and vendors
    allowed = s.approved_tools
    for u in active:
        if allowed:
            ok = allowed.get(key(u.tool))
            if ok is None:
                sens = [c for c in u.data if c in SENSITIVE]
                add(Finding("DATA-TOOL", "RED" if sens else "AMBER", "data", u.id, f"{u.name} runs on {u.tool or 'an unnamed tool'}, which is not an approved AI tool"
                            + (f", with {', '.join(sens)} data" if sens else ""), [u.id], s.owners.get("security", ""),
                            action="Approve the tool for this data or move the use case to an approved one"))
                missed[u.id] += 1
            else:
                extra = [c for c in u.data if c not in ok]
                if extra:
                    add(Finding("DATA-TOOL", "RED" if any(c in SENSITIVE for c in extra) else "AMBER", "data", u.id,
                                f"{u.name} puts {', '.join(extra)} data in {u.tool}, approved only for {', '.join(ok)}", [u.id],
                                s.owners.get("security", ""), action="Keep that data out of it, or approve the tool for it"))
                    missed[u.id] += 1
        if u.trains and any(c in SENSITIVE for c in u.data):
            add(Finding("DATA-VENDOR", "RED", "data", u.id, f"{u.name}: {u.vendor or 'the vendor'} can train its models on the data, which includes "
                        + ", ".join(c for c in u.data if c in SENSITIVE), [u.id], s.owners.get("privacy", ""),
                        action="Switch off training on customer data in the contract or the admin settings"))
            missed[u.id] += 1

    # --- value
    for u in active:
        row = {"use_case": u.id, "name": u.name, "status": u.status, "department": u.department, "monthly_cost": u.cost,
               "licensed": u.licensed, "active": u.active, "adoption_pct": None, "estimated_hours": u.est_hours, "measured_hours": u.hours,
               "value_pct": None, "cost_per_hour": None, "seats_to_reclaim": None, "monthly_saving": None, "business_case": "yes" if u.case else "no"}
        if u.status == "pilot" and u.started and (rd - u.started).days > s.pilot_max_days:
            add(Finding("VAL-PILOT", "AMBER", "value", u.id, f"{u.name} has been a pilot for {(rd - u.started).days} days with no decision",
                        [u.id], u.owner or s.owners.get("value", ""), action="Decide: go live, extend with a date, or stop"))
        if u.status == "production" and not u.case:
            add(Finding("VAL-NO-CASE", "AMBER", "value", u.id, f"{u.name} is in production with no business case", [u.id],
                        u.owner or s.owners.get("value", ""), action="Write the business case: cost, hours saved, risks"))
        if u.licensed and u.active is not None:
            pct = round(100 * u.active / u.licensed, 1)
            row["adoption_pct"] = pct
            if pct < s.adoption_min:
                seats = int(u.licensed - u.active)
                row["seats_to_reclaim"] = seats
                if u.cost:
                    row["monthly_saving"] = round(u.cost / u.licensed * seats, 2)
                add(Finding("VAL-ADOPTION", "AMBER", "value", u.id, f"{u.name}: {int(u.active)} of {int(u.licensed)} licensed users active ({pct} %)"
                            + (f", {row['monthly_saving']:,.0f} € a month on unused seats" if row["monthly_saving"] else ""), [u.id],
                            s.owners.get("value", ""), action="Reclaim the unused seats or plan adoption with the department"))
        if u.est_hours and u.hours is not None:
            vp = round(100 * u.hours / u.est_hours, 1)
            row["value_pct"] = vp
            if vp < s.value_min:
                add(Finding("VAL-SHORTFALL", "AMBER", "value", u.id, f"{u.name}: {u.hours:g} hours a month saved against {u.est_hours:g} estimated ({vp} %)",
                            [u.id], u.owner or s.owners.get("value", ""), action="Find out why with the users and revise the case"))
        if u.cost and u.hours:
            row["cost_per_hour"] = round(u.cost / u.hours, 2)
        rv.value.append(row)

    # --- score per use case, department and tier
    for u in d.uses:
        t, why = tiers[u.id]
        need = required(u, t, s, has_people) if u.status in ("pilot", "production") and t != "prohibited" else []
        total = len(FIELDS) + len(need) + 2           # +2: the tier and the review
        score = None
        if u.status in ("pilot", "production"):
            score = round(max(0.0, 100 * (total - missed[u.id]) / total), 1)
            if t == "prohibited":
                score = 0.0
        rv.rows.append({"use_case": u.id, "name": u.name, "department": u.department, "status": u.status, "tool": u.tool, "owner": u.owner,
                        "declared_tier": TIER_LABEL.get(u.declared, ""), "policy_tier": TIER_LABEL[t], "why": why, "data": ", ".join(u.data),
                        "controls_missing": ", ".join(CONTROLS.get(c, c) for c in need if not control_ok(c, u, people, s, rd)),
                        "score": score, "findings": " ".join(sorted(set(per_use.get(u.id, []))))})
    scored = [r for r in rv.rows if r["score"] is not None]
    rv.score = round(sum(r["score"] for r in scored) / len(scored), 1) if scored else 0.0
    agg = defaultdict(list)
    for r in scored:
        agg[r["department"] or "(none)"].append(r)
    for k, rows in sorted(agg.items(), key=lambda kv: sum(r["score"] for r in kv[1]) / len(kv[1])):
        rv.departments.append({"department": k, "use_cases": len(rows), "score": round(sum(r["score"] for r in rows) / len(rows), 1),
                               "with_findings": sum(1 for r in rows if r["findings"]),
                               "red": sum(1 for r in rows if any(f.severity == "RED" and r["use_case"] in f.items for f in rv.findings))})
    for t in reversed(TIERS):
        us = [u for u in live if tiers[u.id][0] == t]
        rv.tiers.append({"tier": TIER_LABEL[t], "use_cases": len(us), "production": sum(1 for u in us if u.status == "production"),
                         "pilot": sum(1 for u in us if u.status == "pilot"), "idea": sum(1 for u in us if u.status == "idea"),
                         "declared_lower": sum(1 for u in us if u.declared and TIERS.index(u.declared) < TIERS.index(t))})

    # --- decisions
    own = s.owners
    for f in [f for f in rv.findings if f.code == "RISK-PROHIBITED"]:
        u = by_id[f.items[0]]
        rv.decisions.append({"decision": f"Stop {u.name}", "detail": f"{u.status}, {u.department}: {tiers[u.id][1]}", "owner": own.get("register", ""), "due": f.due})
    up = [f for f in rv.findings if f.code == "RISK-TIER" and f.severity == "RED"]
    if up:
        rv.decisions.append({"decision": f"Reclassify {len(up)} use case{'s' if len(up) > 1 else ''} as high risk and complete the controls",
                             "detail": ", ".join(by_id[f.items[0]].name for f in up), "owner": own.get("register", ""), "due": _due(rd, "RED")})
    if rv.unregistered:
        rv.decisions.append({"decision": f"Register or block {len(rv.unregistered)} AI tools found in the tenant",
                             "detail": ", ".join(f"{x['name']} ({x['users']} users)" for x in rv.unregistered), "owner": own.get("register", ""),
                             "due": _due(rd, "RED" if any(f.code == "REG-UNREGISTERED" and f.severity == "RED" for f in rv.findings) else "AMBER")})
    stopped = {f.items[0] for f in rv.findings if f.code == "RISK-PROHIBITED"}
    data = [f for f in rv.findings if f.area == "data" and f.severity == "RED" and not set(f.items) & stopped]
    n = len({i for f in data for i in f.items})
    if data:
        rv.decisions.append({"decision": f"Take sensitive data out of {n} use case{'s' if n > 1 else ''} or change the tool",
                             "detail": "; ".join(f.text for f in data), "owner": own.get("security", ""), "due": _due(rd, "RED")})
    pilots = [f for f in rv.findings if f.code == "VAL-PILOT"]
    if pilots:
        rv.decisions.append({"decision": f"Go or stop for {len(pilots)} pilot{'s' if len(pilots) > 1 else ''} with no decision",
                             "detail": ", ".join(by_id[f.items[0]].name for f in pilots), "owner": own.get("value", ""), "due": _due(rd, "AMBER")})
    seats = [r for r in rv.value if r["seats_to_reclaim"]]
    if seats:
        saving = sum(r["monthly_saving"] or 0 for r in seats)
        rv.decisions.append({"decision": f"Reclaim {sum(r['seats_to_reclaim'] for r in seats)} unused AI licences"
                             + (f" ({saving:,.0f} € a month)" if saving else ""),
                             "detail": ", ".join(f"{r['name']}: {r['seats_to_reclaim']}" for r in seats), "owner": own.get("value", ""), "due": _due(rd, "AMBER")})
    left = [f for f in rv.findings if f.code == "REG-OWNER-LEFT"]
    if left:
        rv.decisions.append({"decision": f"New owners for {sum(len(f.items) for f in left)} use cases of people who left",
                             "detail": "; ".join(f"{f.subject}: {', '.join(by_id[i].name for i in f.items)}" for f in left),
                             "owner": own.get("register", ""), "due": _due(rd, "RED" if any(f.severity == "RED" for f in left) else "AMBER")})

    red = any(f.severity == "RED" for f in rv.findings)
    amber = any(f.severity == "AMBER" for f in rv.findings)
    rv.status = "RED" if red or rv.score < s.score_red else "AMBER" if amber or rv.score < s.score_amber else "GREEN"
    order = {"RED": 0, "AMBER": 1}
    rv.findings.sort(key=lambda f: (order[f.severity], list(AREAS).index(f.area), f.code, f.subject))
    return rv


def summary(d: Data, rv: Review) -> dict:
    count = Counter(f.code for f in rv.findings)
    live = [u for u in d.uses if u.status != "retired"]
    return {"status": rv.status, "score": rv.score, "previous": d.settings.previous_score, "uses": len(d.uses), "live": len(live),
            "production": sum(1 for u in live if u.status == "production"), "pilot": sum(1 for u in live if u.status == "pilot"),
            "high": sum(1 for r in rv.rows if r["policy_tier"] == TIER_LABEL["high"] and r["status"] != "retired"),
            "unregistered": len(rv.unregistered), "reclassify": count["RISK-TIER"], "prohibited": count["RISK-PROHIBITED"],
            "red": sum(1 for f in rv.findings if f.severity == "RED"), "amber": sum(1 for f in rv.findings if f.severity == "AMBER"),
            "decisions": len(rv.decisions)}
