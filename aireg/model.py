"""Loading: the AI use case register (register.csv), what discovery finds in the tenant (discovered.csv: Copilot Studio agents,
enterprise apps, cloud app discovery…), the people directory with the AI training date (people.csv), the AI incidents
(incidents.csv) and the AI policy (settings.json). Forgiving column names, into plain dataclasses. register.csv is required; every
other file adds its checks when it is there."""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

USE_ALIASES = {
    "id": ["Id", "UseCase", "Use case id", "Ref", "Reference"],
    "name": ["Name", "Use case", "Title"],
    "purpose": ["Purpose", "Description", "What it does"],
    "owner": ["Owner", "Business owner", "Accountable"],
    "department": ["Department", "Business unit", "Team"],
    "tool": ["Tool", "Platform", "Product", "Model"],
    "vendor": ["Vendor", "Supplier", "Provider"],
    "status": ["Status", "Stage", "Lifecycle"],
    "area": ["Area", "Use", "Domain", "Category"],
    "audience": ["Audience", "Used by", "Facing"],
    "decides": ["DecidesAboutPeople", "Decides about people", "Affects people", "Decisions about"],
    "data": ["DataClasses", "Data classes", "Data", "Data classification"],
    "declared": ["DeclaredTier", "Declared tier", "Risk tier", "Tier", "Risk"],
    "oversight": ["HumanOversight", "Human oversight", "Oversight"],
    "notice": ["TransparencyNotice", "Transparency notice", "Notice"],
    "dpia": ["DPIA", "Data protection impact assessment"],
    "risk": ["RiskAssessment", "Risk assessment"],
    "tests": ["TestEvidence", "Test evidence", "Testing"],
    "logging": ["Logging", "Logs", "Audit log"],
    "dpa": ["VendorDPA", "Vendor DPA", "DPA", "Contract"],
    "trains": ["VendorTrainsOnData", "Vendor trains on data", "Trains on our data"],
    "started": ["PilotStart", "Pilot start", "Started", "Start"],
    "reviewed": ["LastReview", "Last review", "Reviewed"],
    "case": ["BusinessCase", "Business case"],
    "est_hours": ["EstimatedHoursMonth", "Estimated hours", "Hours estimated"],
    "hours": ["MeasuredHoursMonth", "Measured hours", "Hours saved"],
    "cost": ["MonthlyCost", "Monthly cost", "Cost"],
    "active": ["ActiveUsers", "Active users"],
    "licensed": ["LicensedUsers", "Licensed users", "Licences", "Seats"],
}
DISC_ALIASES = {
    "source": ["Source", "Discovery source", "Tool"],
    "name": ["Name", "DisplayName", "App", "Agent"],
    "publisher": ["Publisher", "Vendor", "PublisherName"],
    "owner": ["Owner", "CreatedBy", "Created by", "Maker"],
    "department": ["Department", "Team"],
    "users": ["Users", "UserCount", "Assigned users", "Active users"],
    "data": ["DataSeen", "Data seen", "Sensitivity", "Labels"],
    "last": ["LastActivity", "Last activity", "LastSeen", "Last used"],
}
PEOPLE_ALIASES = {
    "id": ["User", "UserPrincipalName", "SamAccountName", "Username", "Id"],
    "name": ["Name", "DisplayName", "Display name"],
    "enabled": ["Enabled", "Active", "AccountEnabled", "Status"],
    "department": ["Department", "Team"],
    "trained": ["AITraining", "AI training", "AI literacy", "Trained"],
}
INC_ALIASES = {
    "id": ["Incident", "Id", "Number", "Ticket"],
    "use": ["UseCase", "Use case", "AI use case", "Ref"],
    "opened": ["Opened", "Created", "Date"],
    "severity": ["Severity", "Priority", "Impact"],
    "summary": ["Summary", "Title", "Description"],
    "state": ["State", "Status"],
    "closed": ["Closed", "Resolved", "Closed on"],
}
YES = {"yes", "y", "true", "1", "x", "si", "done", "in place", "enabled", "active", "on"}
NO = {"no", "n", "false", "0", "none", "-", "n/a", "na", "pending", "todo", "missing"}
FILES = {"register.csv": "AI use case register", "discovered.csv": "Discovery", "people.csv": "People directory", "incidents.csv": "AI incidents"}
TIERS = ["minimal", "limited", "high", "prohibited"]                         # in order of risk
TIER_LABEL = {"minimal": "Minimal", "limited": "Limited (transparency)", "high": "High", "prohibited": "Prohibited by policy"}
DATA = ["public", "internal", "confidential", "personal", "special"]         # special: health, biometric and other special categories
STAGES = ["idea", "pilot", "production", "retired"]


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def key(s) -> str:
    """A name to match on: lower case, letters and digits only."""
    return re.sub(r"[^a-z0-9]+", "", _norm(s))


def yes(v) -> bool:
    return _norm(v) in YES


def done(v) -> bool:
    """A control is in place when it says yes, a date or a reference (a link, a document number), not when it is empty or 'no'."""
    n = _norm(v)
    return bool(n) and n not in NO


def parse_d(v) -> date | None:
    s = str(v or "").strip()[:19]
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s if "%H" in fmt else s[:10], fmt).date()
        except ValueError:
            pass
    return None


def num(v) -> float | None:
    s = str(v or "").strip().replace("€", "").replace(" ", "")
    if not s:
        return None
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def tier(v) -> str:
    n = _norm(v)
    if not n:
        return ""
    if n.startswith("prohib") or "unacceptable" in n:
        return "prohibited"
    if n.startswith("high") or n in ("3", "tier 3"):
        return "high"
    if n.startswith("limit") or "transparen" in n or n in ("2", "tier 2"):
        return "limited"
    if n.startswith("min") or n.startswith("low") or n in ("1", "tier 1"):
        return "minimal"
    return ""


def stage(v) -> str:
    n = _norm(v)
    if any(w in n for w in ("retir", "stopped", "decommission", "closed")):
        return "retired"
    if any(w in n for w in ("prod", "live", "rolled out", "in use", "operational")):
        return "production"
    if any(w in n for w in ("pilot", "poc", "trial", "test")):
        return "pilot"
    return "idea"


def data_classes(v) -> list[str]:
    out = []
    for part in re.split(r"[;,/|]+", _norm(v)):
        p = part.strip()
        hit = ("special" if any(w in p for w in ("special", "health", "biometric", "medical")) else
               "personal" if any(w in p for w in ("personal", "pii", "customer data", "employee data")) else
               "confidential" if any(w in p for w in ("confidential", "restricted", "secret")) else
               "internal" if "internal" in p else "public" if "public" in p else "")
        if hit and hit not in out:
            out.append(hit)
    return sorted(out, key=DATA.index)


def audience(v) -> str:
    n = _norm(v)
    return "public" if "public" in n else "customers" if any(w in n for w in ("customer", "client", "external", "broker")) else "staff" if n else ""


def decides(v) -> str:
    n = _norm(v)
    if not n or n in NO:
        return ""
    return "employees" if any(w in n for w in ("employee", "staff", "candidate", "applicant", "worker")) else "customers"


@dataclass
class UseCase:
    id: str
    name: str
    purpose: str = ""
    owner: str = ""
    department: str = ""
    tool: str = ""
    vendor: str = ""
    status: str = "idea"
    area: str = ""
    audience: str = ""
    decides: str = ""
    data: list[str] = field(default_factory=list)
    declared: str = ""
    controls: dict = field(default_factory=dict)       # control -> raw value
    trains: bool = False
    started: date | None = None
    reviewed: date | None = None
    case: bool = False
    est_hours: float | None = None
    hours: float | None = None
    cost: float | None = None
    active: float | None = None
    licensed: float | None = None


@dataclass
class Found:
    source: str
    name: str
    publisher: str = ""
    owner: str = ""
    department: str = ""
    users: int = 0
    data: list[str] = field(default_factory=list)
    last: date | None = None


@dataclass
class Person:
    id: str
    name: str
    enabled: bool = True
    department: str = ""
    trained: date | None = None


@dataclass
class Incident:
    id: str
    use: str
    opened: date | None
    severity: str = ""
    summary: str = ""
    open: bool = True
    closed: date | None = None


@dataclass
class Settings:
    organisation: str = "Your organisation"
    review_date: date = field(default_factory=date.today)
    # The AI policy: what each tier means here and what each one needs. The defaults are an example, not legal advice.
    prohibited: list = field(default_factory=lambda: ["emotion recognition at work", "social scoring", "manipulation"])
    high_risk_areas: list = field(default_factory=lambda: ["hiring", "staff evaluation", "creditworthiness", "insurance pricing",
                                                           "claims decisions", "biometric identification"])
    controls: dict = field(default_factory=lambda: {
        "high": ["owner", "oversight", "dpia", "risk", "tests", "logging", "dpa", "notice", "training"],
        "limited": ["owner", "notice", "dpa", "training"],
        "minimal": ["owner", "dpa"]})
    review_months: dict = field(default_factory=lambda: {"high": 3, "limited": 6, "minimal": 12})
    approved_tools: dict = field(default_factory=dict)     # tool -> data classes allowed in it; empty: every tool is allowed
    pilot_max_days: int = 90
    adoption_min: float = 60.0              # % of licensed users active before the licences are worth a look
    value_min: float = 50.0                 # % of the estimated hours actually measured before the case is worth a look
    shadow_users_red: int = 25              # an unregistered AI tool with this many users (or confidential data) is red
    incident_days: int = 14                 # an AI incident open longer than this is a finding
    training_months: int = 12               # the AI training is valid this long
    score_amber: float = 90.0
    score_red: float = 80.0
    previous_score: float | None = None
    owners: dict = field(default_factory=lambda: {"register": "AI governance lead", "security": "Information security",
                                                  "privacy": "Data protection officer", "value": "AI programme manager"})


@dataclass
class Data:
    uses: list[UseCase]
    found: list[Found] = field(default_factory=list)
    people: list[Person] = field(default_factory=list)
    incidents: list[Incident] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)
    sources: dict = field(default_factory=dict)       # file -> rows read


CONTROLS = {"owner": "Named owner", "oversight": "Human oversight", "dpia": "DPIA", "risk": "Risk assessment", "tests": "Test evidence",
            "logging": "Logging", "dpa": "Vendor DPA", "notice": "Transparency notice", "training": "Owner trained"}


def _read(path: Path) -> list[dict]:
    raw = path.read_bytes()
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig")
    sample = text[:2000]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    return list(csv.DictReader(text.splitlines(), delimiter=delim))


def _rows(path: Path, aliases: dict) -> list[dict]:
    rows = _read(path)
    fields = list(rows[0].keys()) if rows else []
    lower = {_norm(f): f for f in fields if f}
    pick = {}
    for k, names in aliases.items():
        for n in names:
            if _norm(n) in lower:
                pick[k] = lower[_norm(n)]
                break
    return [{k: str(r.get(col) or "").strip() for k, col in pick.items()} for r in rows]


def _settings(path: Path) -> Settings:
    s = Settings()
    if not path.exists():
        return s
    raw = json.loads(path.read_text(encoding="utf-8"))
    for k, v in raw.items():
        if k == "review_date":
            s.review_date = parse_d(v) or s.review_date
        elif k in ("controls", "review_months", "owners") and isinstance(v, dict):
            getattr(s, k).update(v)
        elif hasattr(s, k):
            setattr(s, k, v)
    s.approved_tools = {key(t): [c for c in DATA if c in [_norm(x) for x in v]] for t, v in (s.approved_tools or {}).items()}
    return s


def load(folder: Path) -> Data:
    folder = Path(folder)
    p = folder / "register.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} not found: export the AI use case register to register.csv (docs/data-format.md)")
    d = Data(uses=[], settings=_settings(folder / "settings.json"))
    for r in _rows(p, USE_ALIASES):
        if not r.get("id") and not r.get("name"):
            continue
        n = lambda k: num(r.get(k))
        d.uses.append(UseCase(
            id=r.get("id") or r.get("name"), name=r.get("name") or r.get("id"), purpose=r.get("purpose", ""), owner=r.get("owner", ""),
            department=r.get("department", ""), tool=r.get("tool", ""), vendor=r.get("vendor", ""), status=stage(r.get("status")),
            area=_norm(r.get("area")), audience=audience(r.get("audience")), decides=decides(r.get("decides")), data=data_classes(r.get("data")),
            declared=tier(r.get("declared")), controls={c: r.get(c, "") for c in ("oversight", "notice", "dpia", "risk", "tests", "logging", "dpa")},
            trains=yes(r.get("trains")), started=parse_d(r.get("started")), reviewed=parse_d(r.get("reviewed")), case=done(r.get("case")),
            est_hours=n("est_hours"), hours=n("hours"), cost=n("cost"), active=n("active"), licensed=n("licensed")))
    d.sources["register.csv"] = len(d.uses)
    readers = (
        ("discovered.csv", DISC_ALIASES, lambda r: Found(r.get("source", ""), r.get("name", ""), r.get("publisher", ""), r.get("owner", ""),
                                                          r.get("department", ""), int(num(r.get("users")) or 0), data_classes(r.get("data")),
                                                          parse_d(r.get("last")))),
        ("people.csv", PEOPLE_ALIASES, lambda r: Person(r.get("id", ""), r.get("name", ""), yes(r.get("enabled", "yes")), r.get("department", ""),
                                                         parse_d(r.get("trained")))),
        ("incidents.csv", INC_ALIASES, lambda r: Incident(r.get("id", ""), r.get("use", ""), parse_d(r.get("opened")), _norm(r.get("severity")),
                                                           r.get("summary", ""), _norm(r.get("state")) not in ("closed", "resolved", "done"),
                                                           parse_d(r.get("closed")))))
    target = {"discovered.csv": d.found, "people.csv": d.people, "incidents.csv": d.incidents}
    for name, aliases, make in readers:
        f = folder / name
        if f.exists():
            rows = [make(r) for r in _rows(f, aliases)]
            target[name].extend(x for x in rows if (x.id if isinstance(x, Incident) else x.name))
            d.sources[name] = len(target[name])
    return d
