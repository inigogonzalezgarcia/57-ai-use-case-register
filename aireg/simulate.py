"""The fictional demo: Humongous Insurance, an insurer with its head office in Madrid and offices in Barcelona and Seville, and the
monthly review of its AI use case register on Wednesday 18 November 2026. 24 use cases, what discovery finds in the tenant, 30
people and 5 AI incidents. Every name, figure and ticket is made up; the problems are placed on purpose among use cases that are fine.
The output is deterministic: the same files every run."""
from __future__ import annotations

import csv
import json
from pathlib import Path

REVIEW_DATE = "2026-11-18"

HEADER = ["Id", "Name", "Purpose", "Owner", "Department", "Tool", "Vendor", "Status", "Area", "Audience", "DecidesAboutPeople",
          "DataClasses", "DeclaredTier", "HumanOversight", "TransparencyNotice", "DPIA", "RiskAssessment", "TestEvidence", "Logging",
          "VendorDPA", "VendorTrainsOnData", "PilotStart", "LastReview", "BusinessCase", "EstimatedHoursMonth", "MeasuredHoursMonth",
          "MonthlyCost", "ActiveUsers", "LicensedUsers"]
FULL = {"HumanOversight": "Reviewer signs off every output", "TransparencyNotice": "NOTICE-", "DPIA": "DPIA-", "RiskAssessment": "RA-",
        "TestEvidence": "TEST-", "Logging": "Prompts and outputs kept 12 months"}


def uc(i, name, purpose, owner, dept, tool, vendor, status, area, audience, decides, data, tier, full=False, **kw):
    row = dict.fromkeys(HEADER, "")
    row.update({"Id": i, "Name": name, "Purpose": purpose, "Owner": owner, "Department": dept, "Tool": tool, "Vendor": vendor, "Status": status,
                "Area": area, "Audience": audience, "DecidesAboutPeople": decides, "DataClasses": data, "DeclaredTier": tier,
                "VendorDPA": "Yes" if vendor else "", "VendorTrainsOnData": "No" if vendor else ""})
    if full:
        row.update({k: (v + i if v.endswith("-") else v) for k, v in FULL.items()})
    row.update(kw)
    return row


REGISTER = [
    uc("UC-01", "Microsoft 365 Copilot for staff", "Drafting, summaries and search in Outlook, Teams, Word and Excel", "Marta Ruiz", "IT",
       "Microsoft 365 Copilot", "Microsoft", "Production", "productivity", "Staff", "No", "Internal; Confidential; Personal", "Minimal",
       HumanOversight="Users check every output", LastReview="2026-08-20", BusinessCase="BC-2025-14", EstimatedHoursMonth="3000",
       MeasuredHoursMonth="2100", ActiveUsers="301", LicensedUsers="420"),
    uc("UC-02", "Customer service chatbot", "Answers policy and claim status questions on the website", "Javier Soto", "Customer Service",
       "Copilot Studio", "Microsoft", "Production", "customer service", "Customers", "No", "Personal", "Limited",
       HumanOversight="Hand-off to an agent on request", Logging="Conversation transcripts", LastReview="2026-09-01", BusinessCase="BC-2026-02",
       EstimatedHoursMonth="600", MeasuredHoursMonth="540"),
    uc("UC-03", "CV screening assistant", "Ranks applicants for contact-centre roles against the job profile", "Lucía Navarro", "HR",
       "Azure OpenAI", "Microsoft", "Production", "hiring", "Staff", "Candidates", "Personal", "Limited",
       HumanOversight="Recruiter reads every CV it ranks", TransparencyNotice="Careers page notice", Logging="Rankings kept 12 months",
       LastReview="2026-10-05", BusinessCase="BC-2026-05", EstimatedHoursMonth="160", MeasuredHoursMonth="150"),
    uc("UC-04", "Health policy pricing assistant", "Suggests the premium band for new individual health policies", "Pablo Ortega", "Underwriting",
       "Azure OpenAI", "Microsoft", "Pilot", "insurance pricing", "Staff", "Customers", "Personal; Special (health)", "Limited",
       HumanOversight="Underwriter decides the premium", DPIA="DPIA-2026-07", RiskAssessment="RA-2026-07", PilotStart="2026-07-01"),
    uc("UC-05", "Agent emotion scoring on calls", "Scores the emotional state of contact-centre agents from call recordings", "Elena Prieto",
       "Contact Centre", "Fabrikam Voice Analytics", "Fabrikam", "Pilot", "emotion recognition at work", "Staff", "Employees",
       "Personal; Special (biometric)", "Limited", PilotStart="2026-10-12"),
    uc("UC-06", "Motor claims triage", "Sorts new motor claims into fast track, standard and specialist review", "Carlos Gil", "Claims",
       "Azure OpenAI", "Microsoft", "Production", "claims decisions", "Staff", "Customers", "Personal", "High", full=True,
       LastReview="2026-09-15", BusinessCase="BC-2025-21", EstimatedHoursMonth="900", MeasuredHoursMonth="820"),
    uc("UC-07", "Sales meeting notes", "Records and summarises calls with brokers and corporate clients", "Diego Herrera", "Sales",
       "Trey Transcribe", "Trey Research", "Production", "meeting notes", "Staff", "No", "Confidential; Personal", "Minimal",
       VendorTrainsOnData="Yes", LastReview="2026-06-30", BusinessCase="BC-2026-04"),
    uc("UC-08", "Marketing copy assistant", "Drafts campaign copy, web pages and social posts", "Sara Molina", "Marketing", "Litware Writer",
       "Litware", "Production", "content generation", "Public", "No", "Public; Internal", "Minimal",
       HumanOversight="Editor approves before publishing", TransparencyNotice="AI-assisted label on posts", LastReview="2026-07-15",
       BusinessCase="BC-2026-01", MonthlyCost="1500", ActiveUsers="19", LicensedUsers="60"),
    uc("UC-09", "IT knowledge base agent", "Answers how-to questions from the IT knowledge base in Teams", "Marta Ruiz", "IT", "Copilot Studio",
       "Microsoft", "Production", "it support", "Staff", "No", "Internal", "Minimal", LastReview="2026-06-01", BusinessCase="BC-2026-03"),
    uc("UC-10", "GitHub Copilot for developers", "Code suggestions in the IDE for the internal development team", "Raúl Campos", "IT",
       "GitHub Copilot", "GitHub", "Production", "software development", "Staff", "No", "Internal; Confidential", "Minimal",
       LastReview="2026-03-10", BusinessCase="BC-2025-30", ActiveUsers="41", LicensedUsers="45"),
    uc("UC-11", "Broker email triage", "Sorts and routes broker emails to the right team", "Ana Vidal", "Commercial", "Copilot Studio",
       "Microsoft", "Production", "email triage", "Staff", "No", "Personal", "Minimal", LastReview="2025-09-30", BusinessCase="BC-2025-09"),
    uc("UC-12", "Fraud signals summary", "Summarises the fraud signals of a claim for the investigator", "Carlos Gil", "Claims",
       "Copilot Studio", "Microsoft", "Production", "fraud investigation support", "Staff", "Customers", "Personal", "Minimal",
       HumanOversight="Investigator decides", Logging="Summaries kept with the claim", LastReview="2026-08-03", BusinessCase="BC-2026-06"),
    uc("UC-13", "Policy document translation", "Translates policy wordings and letters for the Barcelona office", "Irene Castro", "Operations",
       "Northwind Translate", "Northwind", "Production", "translation", "Staff", "No", "Confidential", "Minimal", LastReview="2026-05-20",
       BusinessCase="BC-2025-27"),
    uc("UC-14", "Contract clause review", "Flags unusual clauses in supplier contracts for the legal team", "Tomás Rey", "Legal",
       "Microsoft 365 Copilot", "Microsoft", "Production", "contract review", "Staff", "No", "Confidential", "Minimal", LastReview="2026-09-22"),
    uc("UC-15", "Finance report drafting", "First draft of the monthly management report commentary", "Nuria Pons", "Finance",
       "Microsoft 365 Copilot", "Microsoft", "Production", "reporting", "Staff", "No", "Confidential", "Minimal", LastReview="2026-07-01",
       BusinessCase="BC-2026-08", EstimatedHoursMonth="120", MeasuredHoursMonth="40"),
    uc("UC-16", "Staff performance summaries", "Summarises a year of objectives and feedback for the appraisal", "Lucía Navarro", "HR",
       "Copilot Studio", "Microsoft", "Pilot", "staff evaluation", "Staff", "Employees", "Personal", "High",
       HumanOversight="Manager writes the appraisal", TransparencyNotice="Employee notice NOTICE-UC-16", DPIA="Pending", RiskAssessment="RA-2026-11",
       TestEvidence="TEST-UC-16", Logging="Summaries kept with the appraisal", PilotStart="2026-10-01"),
    uc("UC-17", "Customer letter drafting", "Drafts replies to customer complaints for an agent to edit", "Javier Soto", "Customer Service",
       "Microsoft 365 Copilot", "Microsoft", "Production", "letter drafting", "Customers", "No", "Personal", "Limited",
       HumanOversight="Agent edits and sends", TransparencyNotice="Letter footer", LastReview="2026-05-10", BusinessCase="BC-2026-02"),
    uc("UC-18", "HR policy Q&A agent", "Answers questions on leave, expenses and travel policy", "Laura Méndez", "HR", "Copilot Studio",
       "Microsoft", "Production", "employee questions", "Staff", "No", "Internal", "Minimal", LastReview="2026-10-20", BusinessCase="BC-2026-09"),
    uc("UC-19", "Underwriting document extraction", "Reads medical questionnaires into the underwriting system", "Pablo Ortega", "Underwriting",
       "Azure OpenAI", "Microsoft", "Production", "document extraction", "Staff", "No", "Personal; Special (health)", "Minimal",
       HumanOversight="Underwriter checks every field", Logging="Extractions kept with the case", LastReview="2026-04-01",
       BusinessCase="BC-2025-18", EstimatedHoursMonth="400", MeasuredHoursMonth="380"),
    uc("UC-20", "Sales forecasting assistant", "Quarterly sales forecast from the CRM pipeline", "Ana Vidal", "Commercial", "Copilot Studio",
       "Microsoft", "Pilot", "forecasting", "Staff", "No", "Internal; Confidential", "Minimal", PilotStart="2026-06-15"),
    uc("UC-21", "Campaign image generation", "Images for social campaigns", "Sara Molina", "Marketing", "", "", "Idea", "image generation",
       "Public", "No", "Public", "Limited"),
    uc("UC-22", "Claims line voice bot", "First answer on the claims phone line", "Carlos Gil", "Claims", "", "", "Idea", "customer service",
       "Customers", "No", "Personal", ""),
    uc("UC-23", "Code review bot", "Comments on pull requests", "Raúl Campos", "IT", "Azure OpenAI", "Microsoft", "Retired",
       "software development", "Staff", "No", "Internal", "Minimal", LastReview="2025-12-01"),
    uc("UC-24", "Expense receipt reading", "", "Nuria Pons", "Finance", "Azure OpenAI", "Microsoft", "Production", "document extraction",
       "Staff", "No", "Personal", "", LastReview="2026-09-10", BusinessCase="BC-2026-10"),
]

DISCOVERED = [  # Source, Name, Publisher, Owner, Department, Users, DataSeen, LastActivity
    ("Copilot Studio", "Customer service chatbot", "", "Javier Soto", "Customer Service", 0, "Personal", "2026-11-17"),
    ("Copilot Studio", "IT knowledge base agent", "", "Marta Ruiz", "IT", 388, "Internal", "2026-11-17"),
    ("Copilot Studio", "Broker email triage", "", "Ana Vidal", "Commercial", 12, "Personal", "2026-11-16"),
    ("Copilot Studio", "Fraud signals summary", "", "Carlos Gil", "Claims", 18, "Personal", "2026-11-17"),
    ("Copilot Studio", "HR policy Q&A agent", "", "Laura Méndez", "HR", 296, "Internal", "2026-11-17"),
    ("Copilot Studio", "Staff performance summaries", "", "Lucía Navarro", "HR", 9, "Personal", "2026-11-13"),
    ("Copilot Studio", "Sales forecasting assistant", "", "Ana Vidal", "Commercial", 4, "Confidential", "2026-10-28"),
    ("Copilot Studio", "Claims FAQ bot", "", "Rosa Lara", "Claims", 142, "Confidential", "2026-11-17"),
    ("Copilot Studio", "Proposal writer agent", "", "Iván Serrano", "Commercial", 6, "Internal", "2026-11-12"),
    ("Enterprise apps", "Trey Transcribe", "Trey Research", "", "Sales", 34, "Confidential", "2026-11-17"),
    ("Enterprise apps", "Litware Writer", "Litware", "", "Marketing", 19, "Internal", "2026-11-16"),
    ("Enterprise apps", "Northwind Translate", "Northwind", "", "Operations", 22, "Confidential", "2026-11-17"),
    ("Enterprise apps", "GitHub Copilot", "GitHub", "", "IT", 41, "Internal", "2026-11-17"),
    ("Enterprise apps", "Fabrikam Voice Analytics", "Fabrikam", "", "Contact Centre", 12, "Personal", "2026-11-14"),
    ("Enterprise apps", "Lucerne Note Taker", "Lucerne", "", "Sales", 23, "Confidential; Personal", "2026-11-17"),
    ("Cloud app discovery", "Adatum Slides AI", "Adatum", "", "Commercial", 31, "", "2026-11-17"),
    ("Cloud app discovery", "Coho Chat", "Coho", "", "Marketing", 14, "Personal", "2026-11-15"),
    ("Cloud app discovery", "Wingtip Translate", "Wingtip", "", "Operations", 9, "", "2026-11-10"),
]

PEOPLE = [  # User, Name, Enabled, Department, AITraining
    ("mruiz", "Marta Ruiz", True, "IT", "2026-02-10"), ("jsoto", "Javier Soto", True, "Customer Service", ""),
    ("lnavarro", "Lucía Navarro", True, "HR", "2025-06-01"), ("portega", "Pablo Ortega", True, "Underwriting", "2026-03-04"),
    ("eprieto", "Elena Prieto", True, "Contact Centre", "2026-01-20"), ("cgil", "Carlos Gil", True, "Claims", "2026-02-12"),
    ("dherrera", "Diego Herrera", False, "Sales", "2025-11-03"), ("smolina", "Sara Molina", True, "Marketing", "2026-04-22"),
    ("rcampos", "Raúl Campos", True, "IT", "2026-02-10"), ("avidal", "Ana Vidal", False, "Commercial", "2025-12-01"),
    ("icastro", "Irene Castro", True, "Operations", "2026-05-06"), ("trey", "Tomás Rey", True, "Legal", "2026-03-18"),
    ("npons", "Nuria Pons", True, "Finance", "2026-06-09"), ("lmendez", "Laura Méndez", True, "HR", "2026-02-24"),
    ("rlara", "Rosa Lara", True, "Claims", ""), ("iserrano", "Iván Serrano", True, "Commercial", "2026-09-15"),
    ("bmarin", "Beatriz Marín", True, "Compliance", "2026-01-15"), ("fdominguez", "Fernando Domínguez", True, "Information Security", "2026-01-15"),
    ("cbravo", "Clara Bravo", True, "Data Protection", "2026-01-15"), ("hsantos", "Hugo Santos", True, "IT", "2026-02-10"),
    ("mflores", "Mónica Flores", True, "Claims", "2026-07-01"), ("acortes", "Álvaro Cortés", True, "Underwriting", "2026-03-04"),
    ("pvega", "Paula Vega", True, "Customer Service", "2026-05-12"), ("jmora", "Jorge Mora", True, "Sales", "2026-04-02"),
    ("ecano", "Eva Cano", True, "Marketing", ""), ("sfuentes", "Sergio Fuentes", True, "Finance", "2026-06-09"),
    ("rsolis", "Rocío Solís", True, "Legal", "2026-03-18"), ("gibanez", "Gonzalo Ibáñez", True, "Operations", "2026-05-06"),
    ("aparra", "Adriana Parra", True, "Contact Centre", "2026-01-20"), ("mleon", "Miguel León", True, "Commercial", ""),
]

INCIDENTS = [  # Incident, UseCase, Opened, Severity, Summary, State, Closed
    ("AI-101", "UC-02", "2026-10-21", "High", "Chatbot told a customer that a dental treatment was covered by a policy that excludes it",
     "Open", ""),
    ("AI-102", "UC-01", "2026-09-10", "Medium", "A Copilot answer quoted an HR file the user could open through a sharing link left from 2023",
     "Closed", "2026-09-12"),
    ("AI-103", "UC-06", "2026-08-02", "Medium", "Triage sent two windscreen claims to specialist review", "Closed", "2026-08-05"),
    ("AI-104", "UC-15", "2026-11-09", "Low", "Draft commentary quoted last year's claims ratio", "Open", ""),
    ("AI-105", "Claims FAQ bot", "2026-11-03", "Medium", "Bot gave staff an out-of-date claims authority limit", "Open", ""),
]

SETTINGS = {
    "organisation": "Humongous Insurance",
    "review_date": REVIEW_DATE,
    "previous_score": 82.6,
    "prohibited": ["emotion recognition at work", "social scoring", "manipulation"],
    "high_risk_areas": ["hiring", "staff evaluation", "creditworthiness", "insurance pricing", "claims decisions", "biometric identification"],
    "controls": {"high": ["owner", "oversight", "dpia", "risk", "tests", "logging", "dpa", "notice", "training"],
                 "limited": ["owner", "notice", "dpa", "training"], "minimal": ["owner", "dpa"]},
    "review_months": {"high": 3, "limited": 6, "minimal": 12},
    "approved_tools": {
        "Microsoft 365 Copilot": ["public", "internal", "confidential", "personal"],
        "Copilot Studio": ["public", "internal", "confidential", "personal"],
        "Azure OpenAI": ["public", "internal", "confidential", "personal", "special"],
        "GitHub Copilot": ["public", "internal", "confidential"],
        "Litware Writer": ["public", "internal"],
        "Northwind Translate": ["public", "internal", "confidential"],
    },
    "pilot_max_days": 90,
    "adoption_min": 60,
    "value_min": 50,
    "shadow_users_red": 25,
    "incident_days": 14,
    "training_months": 12,
    "owners": {"register": "Beatriz Marín (AI governance lead)", "security": "Fernando Domínguez (Information security)",
               "privacy": "Clara Bravo (Data protection officer)", "value": "Marta Ruiz (AI programme manager)"},
}


def _csv(path: Path, header: list[str], rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow([r[h] for h in header] if isinstance(r, dict) else ["Yes" if v is True else "No" if v is False else v for v in r])


def write(folder: Path) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    _csv(folder / "register.csv", HEADER, REGISTER)
    _csv(folder / "discovered.csv", ["Source", "Name", "Publisher", "Owner", "Department", "Users", "DataSeen", "LastActivity"], DISCOVERED)
    _csv(folder / "people.csv", ["User", "Name", "Enabled", "Department", "AITraining"], PEOPLE)
    _csv(folder / "incidents.csv", ["Incident", "UseCase", "Opened", "Severity", "Summary", "State", "Closed"], INCIDENTS)
    (folder / "settings.json").write_text(json.dumps(SETTINGS, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return folder
