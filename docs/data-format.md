# Data format

Every file is CSV (comma or semicolon, UTF-8 or UTF-16), column names are matched without case, spaces or accents, and the usual
names work (Use case, Business owner, Platform, Stage, Risk…). Only `register.csv` is required; each other file turns on its checks.

## register.csv (required): the AI use case register

| Column | Also read as | Notes |
|---|---|---|
| Id | Use case id, Ref, Reference | Unique id; the name is used when empty |
| Name | Use case, Title | Also matched against discovery |
| Purpose | Description, What it does | Required for pilots and production |
| Owner | Business owner, Accountable | Name or user id, checked against people.csv |
| Department | Business unit, Team | Used for the department scores |
| Tool | Platform, Product, Model | Checked against `approved_tools`; also matched against discovery |
| Vendor | Supplier, Provider | When filled, a vendor DPA is required |
| Status | Stage, Lifecycle | idea; pilot / PoC / trial; production / live; retired / stopped |
| Area | Use, Domain, Category | What it is used for, compared with the policy lists (`prohibited`, `high_risk_areas`) |
| Audience | Used by, Facing | staff; customers / clients / external; public |
| DecidesAboutPeople | Affects people | No, or who: candidates / employees / staff → employees; anyone else → customers |
| DataClasses | Data, Data classification | Separated by `;` or `,`: public, internal, confidential (restricted), personal (PII), special (health, biometric) |
| DeclaredTier | Risk tier, Tier, Risk | minimal / low, limited / transparency, high, prohibited / unacceptable |
| HumanOversight, TransparencyNotice, DPIA, RiskAssessment, TestEvidence, Logging, VendorDPA | | A control is in place when the cell has yes, a date or a reference; empty, no, pending or n/a means missing |
| VendorTrainsOnData | Trains on our data | Yes with confidential, personal or special data is red |
| PilotStart | Started | Pilots older than `pilot_max_days` need a decision |
| LastReview | Reviewed | The next review is this date plus `review_months` for the tier |
| BusinessCase | | A reference or yes |
| EstimatedHoursMonth, MeasuredHoursMonth | Hours saved | Measured below `value_min` % of the estimate is a finding |
| MonthlyCost, ActiveUsers, LicensedUsers | Seats, Licences | Adoption below `adoption_min` %: the unused seats and what they cost |

## discovered.csv: what discovery finds in the tenant

| Column | Also read as | Notes |
|---|---|---|
| Source | Tool | Copilot Studio, Enterprise apps, Cloud app discovery… |
| Name | DisplayName, App, Agent | Matched against the use case names and tools of the register |
| Publisher, Owner, Department | Vendor, CreatedBy, Maker | Shown in the report |
| Users | UserCount, Assigned users | `shadow_users_red` users or more is red |
| DataSeen | Sensitivity, Labels | Confidential, personal or special is red |
| LastActivity | Last used, LastSeen | |

`scripts/Export-AIDiscoveryEntra.ps1` writes the enterprise apps. Copilot Studio agents (from the Power Platform admin center
inventory) and the AI apps of your cloud app discovery tool go in the same file with the same columns.

## people.csv

User (UserPrincipalName, SamAccountName), Name, Enabled (AccountEnabled), Department, AITraining (the date of the last AI training;
valid for `training_months`). Owners not found or disabled are owners who left.

## incidents.csv

Incident, UseCase (id or name), Opened, Severity (high / critical / 1 is red when open too long), Summary, State (closed or resolved
= closed), Closed.

## settings.json: the AI policy

| Key | Default | Meaning |
|---|---|---|
| organisation, review_date | | Title of the outputs; the date the review runs as |
| prohibited | emotion recognition at work, social scoring, manipulation | Areas the policy does not allow |
| high_risk_areas | hiring, staff evaluation, creditworthiness, insurance pricing, claims decisions, biometric identification | Areas the policy treats as high risk |
| controls | high: owner, oversight, dpia, risk, tests, logging, dpa, notice, training · limited: owner, notice, dpa, training · minimal: owner, dpa | Controls each tier needs |
| review_months | high 3, limited 6, minimal 12 | How often each tier is reviewed |
| approved_tools | (none: every tool allowed) | Tool → data classes allowed in it |
| pilot_max_days, adoption_min, value_min | 90, 60, 50 | Value thresholds |
| shadow_users_red, incident_days, training_months | 25, 14, 12 | |
| score_amber, score_red, previous_score | 90, 80, none | Status and trend |
| owners | register, security, privacy, value | Who owns each kind of finding |

## How the tier is worked out

1. The area matches `prohibited` → prohibited by policy.
2. The area matches `high_risk_areas` → high.
3. Customers or the public talk to it or see what it produces, or its output feeds decisions about people → limited.
4. Otherwise → minimal.

A declared tier below the policy tier is a finding (red when the policy makes it high). The lists are the organisation's own: the
defaults are an example built on a risk-based approach, not legal advice, and the review does not decide whether a law applies.

## How the score is calculated

For each pilot and production use case: the register fields (owner, purpose, tool, data classes, declared tier, audience), the
controls its tier needs, the tier declared as the policy gives it, and the review on time. Score = items met / items × 100; a use
case the policy prohibits scores 0. The overall score is the average; the departments are the average of their use cases. Status:
RED with any red finding or a score below `score_red`, AMBER with any amber finding or below `score_amber`, GREEN otherwise.
