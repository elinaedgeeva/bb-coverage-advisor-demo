# Brown & Brown AI Copilot — Development Plan

## Interview Context
- **Date:** June 15, 2026
- **Role:** Forward Deployed Engineer at LTM
- **Client:** Brown & Brown insurance broker
- **Goal:** Demo two AI use cases that save broker time and improve decisions

---

## Use Case 1 (Priority): Coverage Stress Tester
**What it does:** Broker describes a claim scenario → agent searches the policy → surfaces
coverage gaps, exclusions, and ambiguities → broker makes a human decision.

**Why it matters:** Today a broker manually reads a 40-page policy to answer "what if" questions.
This agent does it in seconds, grounded in actual policy language.

---

## Use Case 2: PDF Schedule Parser
**What it does:** Broker uploads a PDF schedule → agent extracts structured data → outputs
a formatted Excel file ready for AMS import.

**Why it matters:** Brokers spend 2–3 hours per renewal manually re-keying data from PDFs.

---

## User & Business Process

### Persona: Account Manager / Producer at a B&B office
Owns a book of ~150–300 client relationships. Most of the day is renewals, endorsement
requests, and fielding "what if" coverage questions — often on policies they didn't
originally write, for clients in industries they don't deeply specialize in.

### Mode A — Scenario Stress Test ("what if" / reactive)

| | Today (manual) | With the agent |
|---|---|---|
| **Trigger** | Client calls/emails: "what if X happens — are we covered?" | Same trigger — AM opens the copilot |
| **Process** | AM pulls the 40+ page policy PDF, manually searches for the relevant exclusion/endorsement, often doesn't think to also check this client's claims history or carrier-specific patterns, frequently escalates "to be safe" | AM types the scenario in plain English. Agent retrieves THIS client's policy + claims/risk-flag history + carrier risk patterns + playbook, cross-references all three, returns a verdict (COVERED / CONDITIONAL / LIKELY_DENIED) with confidence, cited policy language, and a recommended action |
| **Time** | 30–60 min, sometimes days if escalated | Under 30 seconds |
| **Output** | Verbal/email answer, rarely documented | Structured verdict + logged decision (Accept / Flag for Review / Escalate to Attorney) |

**Business process tie-in:** The decision log becomes part of the client file — a
timestamped record that the AM reviewed the question against current policy language
*and* the client's actual history. That's the AM's own E&O defense file if the handling
of the question is ever questioned later.

### Mode B — Coverage Audit (proactive / renewal prep)

| | Today (manual) | With the agent |
|---|---|---|
| **Trigger** | 60–90 days before renewal, or after a significant claim | Same trigger — part of the renewal prep checklist |
| **Process** | AM (or a junior teammate) works through a generic checklist; quality varies a lot by tenure, and gaps specific to this client's industry/claims history are often missed | One click → agent audits the client's actual policy against their industry's known E&O loss patterns, their own claims history, and the playbook for that policy type; returns a ranked risk list (severity, E&O frequency data, "what could go wrong," fix) |
| **Time** | 1–3 hours, quality-dependent | Under a minute |
| **Output** | Internal notes, maybe a renewal memo | Ranked risk list + immediate actions — becomes the literal agenda for the renewal conversation |

**Business process tie-in:** Surfaced gaps map directly to endorsement/upsell conversations
(higher limits, additional insured, MTC, etc.) — a revenue lever, not just risk reduction.
It also standardizes audit quality across a brokerage that's grown largely through
acquisition of independently-run agencies with inconsistent processes.

---

## Expected Outcomes

**For the broker (AM/producer):**
- Seconds instead of hours for "what if" questions and renewal audits
- Every answer grounded in *this client's* actual policy + history, not generic advice
- A documented decision trail for every judgment call (compliance + E&O defense)

**For Brown & Brown (the business):**
- **E&O loss ratio** — catching repeat exposures (e.g., the $47K E&O pattern surfaced for
  Meridian Freight in both demo scenarios) *before* they recur is directly tied to B&B's
  own E&O insurance costs; B&B is the one that gets sued when a broker misses something
- **Consistency at scale** — B&B has grown through dozens of acquisitions; this gives every
  office the same institutional-knowledge-grounded review, regardless of the legacy
  agency's prior process maturity
- **Revenue** — proactive audit findings become endorsement/upsell conversations at renewal
- **Client retention** — faster, more confident answers to coverage questions build trust
  and reduce E&O exposure for the client too, which reflects on B&B

**For this interview specifically:**
This demo deliberately mirrors a real FDE engagement: find the actual broker workflow
(not a generic chatbot), ground every output in the client's real data + institutional
knowledge, keep a human decision-maker in the loop (regulatory requirement), and design
the integration to slot into the tools brokers already use (Teams/Copilot Studio).

---

## Architecture

```
BROKER (Copilot Studio in Teams)
        |
        v
COPILOT STUDIO AGENT
  - Topics: "Stress Test", "Parse Schedule"
  - Calls backend via HTTP connector
  - Shows results as Adaptive Cards
  - Human-in-the-loop decision buttons
        |
        v
AZURE FUNCTIONS (HTTP triggers)
  - stress_test_function
  - parse_schedule_function
        |
        v
AZURE AI FOUNDRY (Intelligence Layer)
  - Anthropic Claude (LLM reasoning)
  - Azure OpenAI ada-002 (embeddings)
  - Azure Document Intelligence (PDF extraction)
  - Azure AI Search (policy RAG + risk patterns)
  - Azure Blob Storage (docs + playbooks)
```

---

## Knowledge Layer (3 stores)

| Store | What's in it | Purpose |
|---|---|---|
| AI Search: `policy-docs` | Chunked policy text, vectorized | Retrieve exact policy clauses for a scenario |
| AI Search: `risk-patterns` | Structured known risk patterns by scenario type | Surface institutional knowledge (carrier + industry → known issues) |
| Blob Storage: `playbooks/` | YAML scenario procedures per policy type | Explicit broker-editable checklists of what to test |

---

## Day 1 — Knowledge Layer ✅ COMPLETE
- [x] Azure resources provisioned (AI Foundry, AI Search, Doc Intelligence, Storage, OpenAI)
- [x] .env fully configured and validated (12/12 keys)
- [x] LLM client built — configurable provider (Anthropic API for demo, Azure OpenAI swap-ready)
- [x] Create AI Search index schemas (policy-docs + risk-patterns)
- [x] Source 6 real policy PDFs (CA 00 01 ×2, CG 00 01 ×2, WC ×2)
- [x] Build indexing pipeline — Doc Intelligence extracts paragraphs → ada-002 embeds → AI Search stores
      └─ Doc Intelligence ran: prebuilt-layout model, 6 PDFs, 219 chunks total
- [x] Write YAML playbooks (commercial_auto, claims_made, general_liability)
- [x] Seed risk-patterns index — 13 patterns across 4 scenario types
- [x] Validate retrieval end-to-end — 3 tests passed

### Day 1 Known Limitations (fix on Day 2 afternoon)
- Policy PDFs are base ISO forms only — no declarations or endorsements
- "radius" keyword not in base CA 00 01 form (lives in declarations/endorsements)
- Fix: generate 2-3 synthetic full policy packages with LLM, re-index before demo
- Framework is solid — data improvement is independent of agent code

---

## Day 2 — Stress Test Agent (NOW)
- [x] Write prompts/stress_test_system.txt — insurance domain system prompt (use Opus)
- [x] Write agents/stress_tester.py — agentic loop with tools:
      retrieve_policy_clauses, retrieve_risk_patterns, load_playbook,
      retrieve_client_history, retrieve_eo_claims, retrieve_industry_losses,
      retrieve_carrier_decisions, produce_verdict
- [x] Structured JSON output: verdict/risks[], confidence, recommended actions, human_review_required
- [x] Test with Demo Scenario 1 (radius/driver) and Scenario 2 (territory/theft)
- [~] Generate synthetic full policy documents and re-index (fix data quality)
      └─ Attempted: FPDF-generated declarations PDF was truncated by Doc Intelligence's
         2-page-per-document limit (only 2/8 pages extracted, fewer chunks than before).
         Real ISO endorsement specimens (MTC cargo, scheduled-driver restriction) with
         matching language aren't freely available online. CA0001-2013 restored to its
         original working 30-chunk state. Agent already compensates well by citing
         client-history facts (radius, drivers, claims) alongside the real CA 00 01 form —
         audit output remains strong (see last_result.json). Revisit only if time allows;
         not a blocker for the demo.
- [x] Wrap agent in Azure Function (HTTP trigger) — callable from Copilot Studio
      └─ function_app.py (Python v2 model) at project root: POST /api/stress_test
         (audit + scenario modes), GET /api/policies, POST /api/parse_schedule (stub,
         501 — Use Case 2 not yet built). host.json + local.settings.json + .gitignore
         added. Validated locally: routing/error handling tested directly, plus a full
         end-to-end CA0001-2013 audit through the wrapper returned 200 with the same
         4-risk report as the direct agent call.
- [x] Install Azure Functions Core Tools (v4.12.0 via winget) and run `func start` locally
      └─ Fix: must activate the project .venv (`.venv\Scripts\Activate.ps1`) before
         `func start` — otherwise the Functions Python worker falls back to the global
         interpreter, which lacks pyyaml/anthropic/etc. With the venv active, the host
         starts cleanly and indexes all 3 routes (stress_test, policies, parse_schedule).
         GET /api/policies tested live → returns all 6 indexed policies (CA0001-2013,
         CA0001-2010, CG0001-2007/2013, WC000000C, WC-STATEFUND).
         POST /api/stress_test (scenario mode, Demo Scenario 1 — radius/driver) tested
         live via Invoke-RestMethod → returned CONDITIONAL verdict, confidence 0.65,
         6 findings (radius violation, missing CA 01 21 endorsement, E&O exposure
         pattern, etc.), human_review_required: true. Matches expected demo outcome.
- [x] Deploy to Azure Function App
      └─ Installed Azure CLI (winget), `az login`, registered Microsoft.Web provider.
         Created Linux consumption-plan Function App `bb-coverage-stress-tester`
         (resource group bb-copilot-demo, eastus2, Python 3.11, reusing bbcopilotstorage).
         Copied all .env values into Function App settings (az functionapp config
         appsettings set) — secrets live in Azure App Settings, not in source control.
         Published with `func azure functionapp publish bb-coverage-stress-tester`
         (remote Oryx build installs requirements.txt on Python 3.11 — local .venv is
         3.13 but that's fine, deployment builds its own env).
      └─ Fixed a real agent bug found during cloud testing: Demo Scenario 2 burned all
         10 iterations without calling produce_verdict (kept searching for a garaging
         schedule not present in the indexed base CA 00 01 form — the Day 1 known
         limitation). Fix: on the final allowed iteration, force tool_choice to
         produce_verdict with a "summarize what you have, note knowledge_gaps, lower
         confidence" nudge (agents/stress_tester.py, both run_stress_test and
         run_coverage_audit). Redeployed.
      └─ LIVE ENDPOINTS (function key required via ?code=... query param):
         https://bb-coverage-stress-tester.azurewebsites.net/api/policies (GET)
         https://bb-coverage-stress-tester.azurewebsites.net/api/stress_test (POST)
         https://bb-coverage-stress-tester.azurewebsites.net/api/parse_schedule (POST, 501 stub)
         Both demo scenarios verified live: Scenario 1 → CONDITIONAL/0.65, Scenario 2 →
         CONDITIONAL/0.55, both human_review_required: true. Ready for Copilot Studio
         HTTP connector (Day 3) — no tunnel needed now that it's deployed.

## Day 3 — Copilot Studio + Polish
- [ ] Create Copilot Studio agent "B&B Coverage Advisor"
- [ ] Topic: "Coverage Stress Test" → HTTP connector → Azure Function → Adaptive Card result
- [ ] Human-in-the-loop buttons: Accept / Flag for Review / Escalate to Attorney
- [ ] Add PDF Schedule Parser as second topic (Use Case 2)
- [ ] Deploy to Teams channel
- [ ] Demo run-through ×3 with both scripted scenarios
- [ ] Prepare architecture diagram talking points

---

## Demo Script (2 scenarios to run live)

**Scenario 1 — Likely denied:**
> "Driver operating a scheduled vehicle 300 miles outside the stated radius at 1am causes
> a liability loss. Does coverage respond?"
Expected: LIKELY_DENIED or CONDITIONAL → radius exclusion finding → Flag for Review

**Scenario 2 — Ambiguous:**
> "Scheduled vehicle stolen from an unsecured lot in a state not listed in the garaging
> schedule. Client filed police report same day."
Expected: CONDITIONAL → territory/garaging ambiguity → human review required

---

## Post-Demo Learning Queue
- [ ] Once the demo is built, revisit Azure Function Apps from first principles via the
      Portal UI (not CLI/winget): create a Function App manually, understand the
      consumption vs. premium plan tradeoffs, what the linked storage account is for,
      how triggers/bindings work, and how `host.json`/`local.settings.json`/App Settings
      relate to the Portal's "Configuration" blade. Goal: be able to explain the pieces,
      not just run `func azure functionapp publish`.

---

## Key Things to Say in the Interview

**On architecture:**
"I built the foundation layer in Azure AI Foundry — the intelligence lives there.
Copilot Studio is the broker-facing interface that calls it. In production, this publishes
as an M365 Copilot extension so brokers access it directly inside Teams."

**On why not just ChatGPT:**
"ChatGPT doesn't know Brown & Brown's policies. Every finding this agent surfaces is
grounded in actual policy language retrieved from AI Search — it cites the exact clause.
That's the difference between a demo and a production tool."

**On human-in-the-loop:**
"Insurance is regulated. The agent surfaces risk and recommends action, but the broker
makes the final call. Every decision is logged. That's intentional design, not a limitation."

**On the knowledge graph (Layer 2):**
"For the prototype I modeled institutional knowledge as structured records in AI Search.
In production this evolves into a graph in Azure Cosmos DB where we encode B&B's
historical E&O cases as relationships — carrier + industry + loss type → known pitfalls."
