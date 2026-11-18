import csv
import json
from datetime import date
from pathlib import Path

from aireg import simulate
from aireg.checks import classify, review, summary
from aireg.cli import OUTPUTS, run
from aireg.model import Settings, data_classes, decides, load, stage, tier

RD = "2026-11-18"
POLICY = {"approved_tools": {"Copilot Studio": ["public", "internal", "confidential", "personal"], "Azure OpenAI": ["public", "internal", "personal"]}}


def write(folder: Path, files: dict, settings: dict | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, rows in files.items():
        with (folder / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    (folder / "settings.json").write_text(json.dumps({"organisation": "Test", "review_date": RD, **(settings or {})}))
    return folder


def use(i="UC-1", name="HR Q&A agent", **kw):
    row = {"Id": i, "Name": name, "Purpose": "Answers policy questions", "Owner": "Ana", "Department": "HR", "Tool": "Copilot Studio",
           "Vendor": "", "Status": "Production", "Area": "employee questions", "Audience": "Staff", "DecidesAboutPeople": "No",
           "DataClasses": "Internal", "DeclaredTier": "Minimal", "HumanOversight": "", "TransparencyNotice": "", "DPIA": "", "RiskAssessment": "",
           "TestEvidence": "", "Logging": "", "VendorDPA": "", "VendorTrainsOnData": "", "PilotStart": "", "LastReview": "2026-10-01",
           "BusinessCase": "BC-1", "EstimatedHoursMonth": "", "MeasuredHoursMonth": "", "MonthlyCost": "", "ActiveUsers": "", "LicensedUsers": ""}
    row.update(kw)
    return row


def person(user="ana", name="Ana", enabled="True", trained="2026-05-01"):
    return {"User": user, "Name": name, "Enabled": enabled, "Department": "HR", "AITraining": trained}


def codes(folder):
    d = load(folder)
    rv = review(d)
    return d, rv, [f.code for f in rv.findings]


def test_parsers():
    assert tier("High risk") == "high" and tier("Limited / transparency") == "limited" and tier("Low") == "minimal" and tier("") == ""
    assert tier("Unacceptable") == "prohibited"
    assert stage("Live") == "production" and stage("PoC") == "pilot" and stage("Decommissioned") == "retired" and stage("") == "idea"
    assert data_classes("Personal; Special (health); internal") == ["internal", "personal", "special"]
    assert data_classes("PII, Restricted") == ["confidential", "personal"]
    assert decides("Candidates") == "employees" and decides("Policyholders") == "customers" and decides("No") == ""


def test_classify_by_policy():
    s = Settings()
    from aireg.model import UseCase
    assert classify(UseCase("1", "x", area="hiring"), s)[0] == "high"
    assert classify(UseCase("1", "x", area="emotion recognition at work"), s)[0] == "prohibited"
    assert classify(UseCase("1", "x", area="faq", audience="customers"), s)[0] == "limited"
    assert classify(UseCase("1", "x", area="fraud support", decides="customers"), s)[0] == "limited"
    assert classify(UseCase("1", "x", area="it support", audience="staff"), s)[0] == "minimal"


def test_clean_register_has_no_findings(tmp_path):
    f = write(tmp_path, {"register.csv": [use()], "people.csv": [person()]}, POLICY)
    d, rv, c = codes(f)
    assert c == [] and rv.status == "GREEN" and rv.score == 100.0


def test_unregistered_ai(tmp_path):
    disc = [{"Source": "Copilot Studio", "Name": "HR Q&A agent", "Users": "40", "DataSeen": "Internal"},
            {"Source": "Copilot Studio", "Name": "Claims bot", "Users": "8", "DataSeen": "Confidential"},
            {"Source": "Cloud app discovery", "Name": "Slides AI", "Users": "3", "DataSeen": ""},
            {"Source": "Enterprise apps", "Name": "Copilot Studio", "Users": "90", "DataSeen": ""}]       # the registered tool itself
    f = write(tmp_path, {"register.csv": [use()], "discovered.csv": disc})
    d, rv, c = codes(f)
    assert [u["name"] for u in rv.unregistered] == ["Claims bot", "Slides AI"]
    sev = {x.subject: x.severity for x in rv.findings if x.code == "REG-UNREGISTERED"}
    assert sev == {"Claims bot": "RED", "Slides AI": "AMBER"}                  # confidential data makes it red


def test_missing_fields_and_owner_left(tmp_path):
    f = write(tmp_path, {"register.csv": [use(Purpose="", DeclaredTier=""), use("UC-2", "Forecast", Owner="Bob")],
                         "people.csv": [person(), person("bob", "Bob", "False")]})
    d, rv, c = codes(f)
    m = next(x for x in rv.findings if x.code == "REG-MISSING")
    assert m.subject == "UC-1" and "purpose, declared tier" in m.text
    left = next(x for x in rv.findings if x.code == "REG-OWNER-LEFT")
    assert left.subject == "Bob" and left.items == ["UC-2"]


def test_tier_below_policy_and_prohibited(tmp_path):
    f = write(tmp_path, {"register.csv": [use(Area="hiring", DeclaredTier="Limited", DecidesAboutPeople="Candidates"),
                                          use("UC-2", "Mood score", Area="emotion recognition at work", Status="Pilot", DeclaredTier="Limited"),
                                          use("UC-3", "Web bot", Area="faq", Audience="Customers", DeclaredTier="Minimal", TransparencyNotice="Yes")]})
    d, rv, c = codes(f)
    t = {x.subject: x.severity for x in rv.findings if x.code == "RISK-TIER"}
    assert t == {"UC-1": "RED", "UC-3": "AMBER"}
    assert [x.subject for x in rv.findings if x.code == "RISK-PROHIBITED"] == ["UC-2"]
    assert rv.decisions[0]["decision"] == "Stop Mood score"


def test_high_risk_controls(tmp_path):
    full = {"HumanOversight": "Yes", "TransparencyNotice": "N-1", "DPIA": "DPIA-1", "RiskAssessment": "RA-1", "TestEvidence": "T-1", "Logging": "Yes"}
    f = write(tmp_path, {"register.csv": [use(Area="claims decisions", DeclaredTier="High", DecidesAboutPeople="Customers", **full),
                                          use("UC-2", "Pricing", Area="insurance pricing", DeclaredTier="High", DecidesAboutPeople="Customers",
                                              **dict(full, DPIA="Pending", TestEvidence=""))],
                         "people.csv": [person()]})
    d, rv, c = codes(f)
    miss = [x for x in rv.findings if x.code == "CTRL-MISSING"]
    assert [x.subject for x in miss] == ["UC-2"] and miss[0].severity == "RED"
    assert "DPIA, test evidence" in miss[0].text                               # 'Pending' is not a DPIA
    gaps = [g for g in rv.gaps if g["use_case"] == "UC-2" and g["in_place"] == "no"]
    assert {g["control"] for g in gaps} == {"DPIA", "Test evidence"}


def test_training_expired(tmp_path):
    f = write(tmp_path, {"register.csv": [use(Area="faq", Audience="Customers", DeclaredTier="Limited", TransparencyNotice="Yes")],
                         "people.csv": [person(trained="2025-06-01")]})
    d, rv, c = codes(f)
    assert "owner trained" in next(x for x in rv.findings if x.code == "CTRL-MISSING").text and rv.untrained == ["Ana"]


def test_reviews_overdue_by_tier(tmp_path):
    f = write(tmp_path, {"register.csv": [use(LastReview="2025-10-01"), use("UC-2", "Pricing", Area="insurance pricing", DeclaredTier="High",
                                                                         LastReview="2026-07-01", Status="Pilot")]})
    d, rv, c = codes(f)
    r = {x.subject: x.severity for x in rv.findings if x.code == "CTRL-REVIEW"}
    assert r == {"UC-1": "AMBER", "UC-2": "RED"}                               # 12 months for minimal, 3 for high
    assert {x["use_case"] for x in rv.reviews} == {"UC-1", "UC-2"}


def test_data_and_vendor(tmp_path):
    f = write(tmp_path, {"register.csv": [use(Tool="Azure OpenAI", DataClasses="Personal; Special (health)"),
                                          use("UC-2", "Notes", Tool="Note SaaS", Vendor="Acme", VendorDPA="Yes", VendorTrainsOnData="Yes",
                                              DataClasses="Confidential")]}, POLICY)
    d, rv, c = codes(f)
    tool = {x.subject: x.text for x in rv.findings if x.code == "DATA-TOOL"}
    assert "special" in tool["UC-1"] and "not an approved AI tool" in tool["UC-2"]
    assert next(x for x in rv.findings if x.code == "DATA-VENDOR").severity == "RED"


def test_incidents(tmp_path):
    inc = [{"Incident": "I1", "UseCase": "UC-1", "Opened": "2026-10-20", "Severity": "High", "Summary": "Wrong answer", "State": "Open", "Closed": ""},
           {"Incident": "I2", "UseCase": "Ghost bot", "Opened": "2026-11-15", "Severity": "Low", "Summary": "x", "State": "Open", "Closed": ""}]
    f = write(tmp_path, {"register.csv": [use()], "incidents.csv": inc})
    d, rv, c = codes(f)
    assert next(x for x in rv.findings if x.code == "RISK-INCIDENT").severity == "RED"
    assert "RISK-REVIEW-AFTER" in c                                             # the incident came after the last review
    assert any(x.code == "REG-MISSING" and x.subject == "I2" for x in rv.findings)


def test_value(tmp_path):
    f = write(tmp_path, {"register.csv": [use(MonthlyCost="1000", ActiveUsers="10", LicensedUsers="50", EstimatedHoursMonth="100",
                                              MeasuredHoursMonth="30"),
                                          use("UC-2", "Pilot", Status="Pilot", PilotStart="2026-06-01", BusinessCase=""),
                                          use("UC-3", "No case", BusinessCase="")]})
    d, rv, c = codes(f)
    v = next(x for x in rv.value if x["use_case"] == "UC-1")
    assert v["seats_to_reclaim"] == 40 and v["monthly_saving"] == 800.0 and v["value_pct"] == 30.0
    assert {"VAL-ADOPTION", "VAL-SHORTFALL", "VAL-PILOT", "VAL-NO-CASE"} <= set(c)
    assert any(x["decision"].startswith("Reclaim 40") for x in rv.decisions)


def test_other_column_names_and_semicolons(tmp_path):
    (tmp_path / "register.csv").write_text("Reference;Use case;Business owner;Platform;Stage;Domain;Facing;Data classification;Risk\n"
                                           "R1;Bot;Ana;Copilot Studio;Live;faq;External customers;PII;Limited\n", encoding="utf-8")
    u = load(tmp_path).uses[0]
    assert (u.id, u.name, u.owner, u.tool, u.status, u.audience, u.data, u.declared) == ("R1", "Bot", "Ana", "Copilot Studio", "production",
                                                                                         "customers", ["personal"], "limited")


def test_missing_register(tmp_path):
    try:
        load(tmp_path)
    except FileNotFoundError as exc:
        assert "register.csv" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_demo_end_to_end(tmp_path):
    simulate.write(tmp_path / "data")
    sm = run(tmp_path / "data", tmp_path / "out")
    for name in OUTPUTS:
        assert (tmp_path / "out" / name).exists(), name
    assert sm["status"] == "RED" and sm["unregistered"] == 6 and sm["prohibited"] == 1 and sm["high"] == 4 and sm["decisions"] == 7
    d = load(tmp_path / "data")
    assert d.settings.review_date == date(2026, 11, 18)
    pack = (tmp_path / "out" / "committee-pack.md").read_text(encoding="utf-8")
    assert "Stop Agent emotion scoring on calls" in pack and "Result: RED" in pack


def test_demo_is_deterministic(tmp_path):
    simulate.write(tmp_path / "a")
    simulate.write(tmp_path / "b")
    for f in (tmp_path / "a").iterdir():
        assert f.read_bytes() == (tmp_path / "b" / f.name).read_bytes(), f.name
    assert summary(load(tmp_path / "a"), review(load(tmp_path / "a")))["score"] == summary(load(tmp_path / "b"), review(load(tmp_path / "b")))["score"]
