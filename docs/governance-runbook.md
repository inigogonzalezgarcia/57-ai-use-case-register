# Monthly AI use case register review

## The cycle

| When | What | Who |
|---|---|---|
| First week | Export the register, the AI enterprise apps (`Export-AIDiscoveryEntra.ps1`), the Copilot Studio agents, cloud app discovery, the directory with the AI training dates and the AI incidents | AI governance lead |
| Same day | `python -m aireg review data/`; send report.html to the use case owners | AI governance lead |
| Within a week | Reds: use cases the policy prohibits, high-risk use cases declared lower or missing controls, AI tools in use with sensitive data and no entry, vendors that can train on the data, high incidents still open | Owners, information security, data protection |
| Committee | committee-pack.md: decisions, the register by tier, departments, reviews due | AI governance committee |
| After | Actions with owner and date; this month's score kept as `previous_score` | Owners |

## Reading the result

1. **Do we know what AI is in use?** Tools discovery finds that nobody registered. Register them with an owner and a tier, or block them; a tool many people already use needs a quick decision and a message to them, not a silent block.
2. **Is each use case in the right tier?** The tier comes from the policy, not from the person who registered it. A use case that ranks candidates or prices a policy is high risk whatever the form said.
3. **Does each tier have its controls?** Human oversight, DPIA, risk assessment, test evidence, logging, vendor DPA, a notice for the people it talks to or decides about, an owner who took the AI training. A pilot with real data needs them before it goes live.
4. **Is the data where the policy allows it?** Sensitive data in a tool not approved for it, and vendors that can train their models on it.
5. **Is it worth it?** Pilots with no decision, production with no business case, licences nobody uses, hours saved far below the estimate.

## Fixing without surprises

- **Stopping a use case:** the owner and the department head hear it before the users; record the decision and the date, keep the register entry as retired.
- **Shadow AI:** find who uses it and for what; offer the approved tool that does the same job, then block the app.
- **Reclassifying:** the owner completes the controls of the new tier with a date; until then the use case stays in pilot or keeps a human decision on every output.
- **Incidents:** an AI incident reopens the review of its use case; a high one goes to the committee.
- **Licences:** look at adoption with the department before reclaiming; a training session sometimes does more than a reclaim.

## Evidence

findings.csv and actions.csv with their dates, the decisions in committee-pack.md, register-review.csv, controls-gaps.csv and
reviews-due.csv are the record of the month; keep them with the committee minutes for the audit.
