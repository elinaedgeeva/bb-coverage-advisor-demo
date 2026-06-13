"""
Coverage Stress Test Agent
--------------------------
Agentic reasoning loop that analyzes a claim scenario against policy documents.

Flow:
  1. Load playbook for the policy type
  2. Retrieve known risk patterns
  3. Retrieve relevant policy clauses (coverage + exclusions)
  4. Reason over all findings → structured JSON verdict

Tools: retrieve_policy_clauses, retrieve_risk_patterns, load_playbook
"""

import os, json, yaml
from dotenv import load_dotenv
load_dotenv(override=True)

import anthropic
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# ── Clients ───────────────────────────────────────────────────────────

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

policy_search = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_POLICY_INDEX"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

patterns_search = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_PATTERNS_INDEX"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

PLAYBOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "playbooks")

# ── Tool definitions ──────────────────────────────────────────────────

TOOLS = [
    {
        "name": "retrieve_policy_clauses",
        "description": (
            "Search the SUBJECT POLICY for clauses relevant to a risk area. "
            "In audit mode, you MUST always pass the policy_id of the policy being audited — "
            "never search across all policies. "
            "In scenario test mode, policy_id is optional but recommended. "
            "Use this multiple times: once per major risk area, once for coverage language, "
            "once for exclusions. Returns verbatim policy text with section type."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The coverage question or risk area to search for in the policy"
                },
                "policy_id": {
                    "type": "string",
                    "description": "The policy ID to search within. REQUIRED in audit mode. E.g. CA0001-2013, CG0001-2007"
                },
                "section_type": {
                    "type": "string",
                    "description": "Optional: filter by section type. One of: exclusions, conditions, insuring_agreement, definitions, declarations, endorsement"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return. Default 4.",
                    "default": 4
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "retrieve_risk_patterns",
        "description": (
            "Retrieve known institutional risk patterns for a given scenario type and industry. "
            "These are pre-encoded patterns based on common E&O claims and coverage disputes. "
            "Always call this before reading policy clauses to know what to look for."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_type": {
                    "type": "string",
                    "description": "Policy/scenario type. One of: commercial_auto, general_liability, claims_made, workers_comp, umbrella"
                },
                "industry": {
                    "type": "string",
                    "description": "Optional: filter by industry (e.g. trucking, construction, professional_services)"
                },
                "severity": {
                    "type": "string",
                    "description": "Optional: filter by severity. One of: CRITICAL, HIGH, MEDIUM"
                }
            },
            "required": ["scenario_type"]
        }
    },
    {
        "name": "retrieve_eo_claims",
        "description": (
            "Search the raw E&O claims dataset (10,000 individual broker E&O claim records, "
            "filed 2015-2024) for records matching a policy type / industry / coverage area. "
            "Returns the matching count, a breakdown of outcomes (denied, paid, litigated, "
            "settled, withdrawn) computed live across all matching records, and a sample of "
            "case narratives and settlement amounts for you to read. "
            "You must compute denial rates and typical settlement ranges yourself from this "
            "data — nothing here is pre-summarized."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_type":   {"type": "string", "description": "commercial_auto | general_liability | claims_made | workers_comp | commercial_property | umbrella"},
                "industry":      {"type": "string", "description": "Optional: trucking | construction | professional_services | etc."},
                "coverage_area": {"type": "string", "description": "Optional: e.g. radius_restriction, unlisted_driver, completed_operations, retroactive_date_gap"},
                "top_k": {"type": "integer", "description": "Number of sample narratives to return. Default 10.", "default": 10}
            },
            "required": ["policy_type"]
        }
    },
    {
        "name": "retrieve_industry_losses",
        "description": (
            "Search the raw commercial loss event dataset (10,000 individual loss records, "
            "2015-2024) for records matching an industry / policy type / loss type. "
            "Returns the matching count, a breakdown of how often coverage responded "
            "(yes / partial / no) computed live across all matching records, and a sample "
            "of loss narratives with severity and paid amounts. "
            "Use this to determine real loss frequency and severity for an industry — "
            "compute the figures yourself from the records returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "industry":  {"type": "string", "description": "trucking | construction | professional_services | etc."},
                "policy_type": {"type": "string", "description": "Optional: commercial_auto | general_liability | claims_made | workers_comp | commercial_property | umbrella"},
                "loss_type": {"type": "string", "description": "Optional: bodily_injury | property_damage | cargo_theft | physical_damage | workers_comp | professional_liability | pollution"},
                "top_k": {"type": "integer", "description": "Number of sample narratives to return. Default 10.", "default": 10}
            },
            "required": ["industry"]
        }
    },
    {
        "name": "retrieve_carrier_decisions",
        "description": (
            "Search the raw carrier coverage decision dataset (10,000 individual decisions, "
            "2015-2024) for records matching a policy type / coverage area / carrier type. "
            "Returns the matching count, a breakdown of decisions (upheld_denial, "
            "reversed_denial, partial_coverage, settled, paid_in_full) computed live across "
            "all matching records, and a sample of decision narratives explaining the "
            "carrier's reasoning. Use this to determine how strictly a given carrier type "
            "enforces a coverage issue — compute the enforcement rate yourself from the data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_type":   {"type": "string", "description": "commercial_auto | general_liability | claims_made | workers_comp | commercial_property | umbrella"},
                "coverage_area": {"type": "string", "description": "Optional: e.g. radius_restriction, unlisted_driver, completed_operations, retroactive_date_gap"},
                "carrier_type":  {"type": "string", "description": "Optional: standard_market | excess_surplus | specialty | admitted | non_admitted"},
                "top_k": {"type": "integer", "description": "Number of sample narratives to return. Default 10.", "default": 10}
            },
            "required": ["policy_type"]
        }
    },
    {
        "name": "retrieve_client_history",
        "description": (
            "Retrieve this client's prior claims, risk flags, renewal history, and CURRENT POLICY "
            "(policy_id, policy_type, industry, stated operating parameters) from the broker's records. "
            "Use this to personalize the analysis — a client with a prior radius denial gets "
            "a different risk severity than a clean account. ALWAYS call this FIRST in both audit "
            "mode and scenario mode — in scenario mode it is how you discover which policy_id and "
            "policy_type to search."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "The client ID. Use DEMO-CLIENT-001 for the demo account."}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "list_indexed_policies",
        "description": (
            "List all policy documents currently indexed and available for analysis. "
            "Call this if you need to confirm what policy_id to use."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "produce_verdict",
        "description": (
            "Call this when you have gathered sufficient information to produce your verdict. "
            "This ends the analysis and returns your structured findings to the broker. "
            "You MUST call this after: loading the playbook, retrieving risk patterns, "
            "and performing at least 2 policy clause searches."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "verdict_json": {
                    "type": "string",
                    "description": "Your complete verdict as a JSON string matching the required output format"
                }
            },
            "required": ["verdict_json"]
        }
    },
    {
        "name": "load_playbook",
        "description": (
            "Load the scenario playbook for a policy type. "
            "The playbook lists mandatory scenarios to test and why they matter. "
            "Always call this first to understand what checks are required."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_type": {
                    "type": "string",
                    "description": "One of: commercial_auto, claims_made, general_liability, workers_comp"
                }
            },
            "required": ["policy_type"]
        }
    }
]

# ── Tool implementations ──────────────────────────────────────────────

def _embed(text: str) -> list:
    response = openai_client.embeddings.create(
        input=text[:8000],
        model=os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
    )
    return response.data[0].embedding


def retrieve_policy_clauses(query: str, policy_id: str = None,
                            section_type: str = None, top_k: int = 4) -> dict:
    vector = _embed(query)
    vector_query = VectorizedQuery(
        vector=vector,
        k_nearest_neighbors=top_k,
        fields="content_vector"
    )

    filters = []
    if policy_id:
        filters.append(f"policy_id eq '{policy_id}'")
    if section_type:
        filters.append(f"section_type eq '{section_type}'")
    filter_str = " and ".join(filters) if filters else None

    results = list(policy_search.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=filter_str,
        top=top_k,
        select=["content", "section_type", "policy_id", "form_number", "page_number"]
    ))

    if not results:
        return {"found": False, "message": "No relevant policy clauses found for this query."}

    return {
        "found": True,
        "count": len(results),
        "clauses": [
            {
                "policy_id": r["policy_id"],
                "form_number": r.get("form_number", "unknown"),
                "section_type": r["section_type"],
                "page_number": r.get("page_number", 0),
                "content": r["content"]
            }
            for r in results
        ]
    }


def retrieve_risk_patterns(scenario_type: str, industry: str = None,
                           severity: str = None) -> dict:
    filters = [f"scenario_type eq '{scenario_type}'"]
    if industry and industry != "any":
        filters.append(f"industry eq '{industry}' or industry eq 'any'")
    if severity:
        filters.append(f"severity eq '{severity}'")
    filter_str = " and ".join(filters)

    results = list(patterns_search.search(
        search_text="*",
        filter=filter_str,
        top=10,
        select=["risk_title", "description", "severity", "exclusion_reference",
                "recommended_check", "eo_frequency"]
    ))

    if not results:
        return {"found": False, "message": f"No risk patterns found for {scenario_type}"}

    return {
        "found": True,
        "count": len(results),
        "patterns": [
            {
                "risk_title": r["risk_title"],
                "severity": r["severity"],
                "description": r["description"],
                "exclusion_reference": r.get("exclusion_reference", ""),
                "recommended_check": r["recommended_check"],
                "eo_frequency": r.get("eo_frequency", "unknown")
            }
            for r in results
        ]
    }


def load_playbook(policy_type: str) -> dict:
    path = os.path.join(PLAYBOOKS_DIR, f"{policy_type}.yaml")
    if not os.path.exists(path):
        return {
            "found": False,
            "message": f"No playbook found for policy type '{policy_type}'. Available: commercial_auto, claims_made, general_liability"
        }
    with open(path, "r") as f:
        playbook = yaml.safe_load(f)
    return {"found": True, "playbook": playbook}


def _intel_client(index_name: str) -> SearchClient:
    return SearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name=index_name,
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
    )


def _filter_value(v: str):
    """Returns v unless it's empty or the placeholder 'any', in which case None (no filter)."""
    if not v or v == "any":
        return None
    return v


def retrieve_eo_claims(policy_type: str, industry: str = None,
                       coverage_area: str = None, top_k: int = 10) -> dict:
    client = _intel_client("eo-claims-raw")
    industry, coverage_area = _filter_value(industry), _filter_value(coverage_area)
    filters = [f"policy_type eq '{policy_type}'"]
    if industry:
        filters.append(f"industry eq '{industry}'")
    if coverage_area:
        filters.append(f"coverage_area eq '{coverage_area}'")
    filter_str = " and ".join(filters)

    results = client.search(
        search_text="*",
        filter=filter_str,
        top=top_k,
        facets=["claim_outcome,count:10"],
        include_total_count=True,
        select=["id", "claim_year", "industry", "coverage_area", "carrier_type",
                "claim_outcome", "eo_settlement_usd", "insured_loss_usd",
                "broker_error_type", "case_narrative"]
    )
    records = [dict(r) for r in results]
    total = results.get_count()
    facets = results.get_facets() or {}

    if total == 0:
        return {"found": False, "message": f"No E&O claim records for {policy_type}"
                                             + (f" / {industry}" if industry else "")
                                             + (f" / {coverage_area}" if coverage_area else "")}
    return {
        "found": True,
        "total_matching_claims": total,
        "outcome_breakdown": facets.get("claim_outcome", []),
        "sample_claims": records
    }


def retrieve_industry_losses(industry: str, policy_type: str = None,
                             loss_type: str = None, top_k: int = 10) -> dict:
    client = _intel_client("industry-losses")
    industry, policy_type, loss_type = (_filter_value(industry), _filter_value(policy_type),
                                         _filter_value(loss_type))
    filters = []
    if industry:
        filters.append(f"industry eq '{industry}'")
    if policy_type:
        filters.append(f"policy_type eq '{policy_type}'")
    if loss_type:
        filters.append(f"loss_type eq '{loss_type}'")
    filter_str = " and ".join(filters) if filters else None

    results = client.search(
        search_text="*",
        filter=filter_str,
        top=top_k,
        facets=["coverage_responded,count:5", "denial_reason,count:10"],
        include_total_count=True,
        select=["id", "loss_year", "naics_code", "policy_type", "loss_type",
                "carrier_type", "coverage_responded", "loss_severity_usd",
                "paid_usd", "denial_reason", "loss_narrative"]
    )
    records = [dict(r) for r in results]
    total = results.get_count()
    facets = results.get_facets() or {}

    if total == 0:
        return {"found": False, "message": f"No loss records for {industry}"
                                             + (f" / {policy_type}" if policy_type else "")
                                             + (f" / {loss_type}" if loss_type else "")}
    return {
        "found": True,
        "total_matching_losses": total,
        "coverage_response_breakdown": facets.get("coverage_responded", []),
        "denial_reason_breakdown": facets.get("denial_reason", []),
        "sample_losses": records
    }


def retrieve_carrier_decisions(policy_type: str, coverage_area: str = None,
                               carrier_type: str = None, top_k: int = 10) -> dict:
    client = _intel_client("carrier-decisions")
    coverage_area, carrier_type = _filter_value(coverage_area), _filter_value(carrier_type)
    filters = [f"policy_type eq '{policy_type}'"]
    if coverage_area:
        filters.append(f"coverage_area eq '{coverage_area}'")
    if carrier_type:
        filters.append(f"carrier_type eq '{carrier_type}'")
    filter_str = " and ".join(filters)

    results = client.search(
        search_text="*",
        filter=filter_str,
        top=top_k,
        facets=["decision,count:10"],
        include_total_count=True,
        select=["id", "decision_year", "carrier_type", "industry", "coverage_area",
                "decision", "endorsement_issue", "claim_amount_usd",
                "paid_amount_usd", "decision_narrative"]
    )
    records = [dict(r) for r in results]
    total = results.get_count()
    facets = results.get_facets() or {}

    if total == 0:
        return {"found": False, "message": f"No carrier decision records for {policy_type}"
                                             + (f" / {coverage_area}" if coverage_area else "")
                                             + (f" / {carrier_type}" if carrier_type else "")}
    return {
        "found": True,
        "total_matching_decisions": total,
        "decision_breakdown": facets.get("decision", []),
        "sample_decisions": records
    }


def retrieve_client_history(client_id: str) -> dict:
    from azure.storage.blob import BlobServiceClient
    blob_service = BlobServiceClient.from_connection_string(
        os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    )
    try:
        blob = blob_service.get_blob_client(
            container="client-history", blob=f"{client_id}.json"
        )
        data = json.loads(blob.download_blob().readall())
        return {"found": True, "client": data}
    except Exception as e:
        return {"found": False, "message": f"No history found for client {client_id}: {str(e)}"}


def list_client_histories() -> dict:
    """Returns a summary of every client record in the client-history container —
    used to populate client pickers in the UI. Reads each blob's top-level fields only."""
    from azure.storage.blob import BlobServiceClient
    blob_service = BlobServiceClient.from_connection_string(
        os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    )
    container = blob_service.get_container_client("client-history")

    clients = []
    for blob in container.list_blobs():
        if not blob.name.endswith(".json"):
            continue
        data = json.loads(container.download_blob(blob.name).readall())
        subject_policy = data["policy_history"][0]
        clients.append({
            "client_id": data["client_id"],
            "client_name": data["client_name"],
            "industry": data["industry"],
            "primary_policy_type": data["primary_policy_type"],
            "policy_id": subject_policy["policy_id"],
            "carrier": subject_policy["carrier"],
            "annual_premium": data["annual_premium"],
        })

    clients.sort(key=lambda c: c["client_id"])
    return {"count": len(clients), "clients": clients}


def list_indexed_policies() -> dict:
    """Returns all unique policy IDs currently in the policy-docs index."""
    results = list(policy_search.search(
        search_text="*",
        top=1000,
        select=["policy_id", "form_number", "section_type"]
    ))
    seen = {}
    for r in results:
        pid = r["policy_id"]
        if pid not in seen:
            seen[pid] = r.get("form_number", "unknown")

    policies = [{"policy_id": k, "form_number": v} for k, v in seen.items()]
    return {"count": len(policies), "policies": policies}


def get_policy_chunks(policy_id: str, top: int = 200) -> dict:
    """Returns every indexed chunk for a policy_id, as stored — raw, unranked,
    no relevance scoring or aggregation. Used by the Data Explorer UI to show
    exactly what the agent's retrieve_policy_clauses searches over."""
    results = list(policy_search.search(
        search_text="*",
        filter=f"policy_id eq '{policy_id}'",
        top=top,
        select=["content", "section_type", "policy_id", "form_number", "page_number"]
    ))
    return {"count": len(results), "chunks": results}


def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name == "retrieve_policy_clauses":
        return retrieve_policy_clauses(**tool_input)
    elif tool_name == "retrieve_risk_patterns":
        return retrieve_risk_patterns(**tool_input)
    elif tool_name == "load_playbook":
        return load_playbook(**tool_input)
    elif tool_name == "retrieve_eo_claims":
        return retrieve_eo_claims(**tool_input)
    elif tool_name == "retrieve_industry_losses":
        return retrieve_industry_losses(**tool_input)
    elif tool_name == "retrieve_carrier_decisions":
        return retrieve_carrier_decisions(**tool_input)
    elif tool_name == "retrieve_client_history":
        return retrieve_client_history(**tool_input)
    elif tool_name == "list_indexed_policies":
        return list_indexed_policies()
    elif tool_name == "produce_verdict":
        return {"status": "verdict_received"}
    else:
        return {"error": f"Unknown tool: {tool_name}"}

# ── Main agent function ───────────────────────────────────────────────

def run_stress_test(scenario: str, client_id: str = "DEMO-CLIENT-001",
                   verbose: bool = False) -> dict:
    """
    Run a coverage stress test for a given scenario against a SPECIFIC CLIENT's policy.

    Args:
        scenario:  The claim scenario / "what if" question, described in plain English
        client_id: The client whose policy this scenario is being checked against
        verbose:   Print agent reasoning steps

    Returns:
        Structured dict with verdict, confidence, findings, recommended_action —
        evaluated against this client's actual policy and claims/risk history.
    """
    system_prompt = open(
        os.path.join(os.path.dirname(__file__), "..", "prompts", "stress_test_system.txt")
    ).read()

    user_message = f"""MODE 2 — SCENARIO TEST

A broker is asking whether coverage responds to the following scenario FOR THIS SPECIFIC CLIENT:

SCENARIO: {scenario}

CLIENT ID: {client_id}

STEP 1 — Call retrieve_client_history(client_id="{client_id}") FIRST. This gives you the
client's subject policy_id, policy_type, industry, stated operating parameters (e.g. radius,
territory, driver schedule), and prior claims/risk flags.

STEP 2 — Load the playbook for the policy_type from step 1, then retrieve risk patterns for
that policy_type and industry.

STEP 3 — Search THIS CLIENT'S SUBJECT POLICY (pass policy_id from step 1 on every call) for
clauses relevant to the scenario — both the coverage that might apply and any exclusions or
conditions that could deny it.

STEP 4 — Cross-reference the scenario against:
  - What the client's policy actually says (cited clauses)
  - The client's actual stated operating parameters (e.g. if the scenario describes operating
    beyond a stated radius, compare the exact numbers from client history)
  - Whether this client has prior claims or risk flags matching this exact issue — if so,
    this is a REPEAT exposure and should be called out explicitly in scenario_summary and
    recommended_action

Produce your verdict as a JSON object matching the MODE 2 output format, including the
client_id and policy_id fields."""

    messages = [{"role": "user", "content": user_message}]

    # ── Agentic loop ──────────────────────────────────────────────────
    iteration = 0
    max_iterations = 10  # safety limit

    while iteration < max_iterations:
        iteration += 1
        force_verdict = iteration == max_iterations

        if force_verdict:
            messages.append({
                "role": "user",
                "content": "You have reached the maximum number of research steps. "
                            "Call produce_verdict now with your best-available analysis "
                            "based on everything retrieved so far. Note any missing "
                            "information in 'knowledge_gaps' and lower 'confidence' accordingly."
            })

        response = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            tool_choice={"type": "tool", "name": "produce_verdict"} if force_verdict else {"type": "auto"},
            messages=messages
        )

        if verbose:
            print(f"\n[Iteration {iteration}] stop_reason: {response.stop_reason}")

        # Model wants to call tools
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            verdict_json = None

            for block in response.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"  Tool: {block.name}({json.dumps(block.input, indent=2)})")

                    # Intercept produce_verdict — extract the JSON and stop the loop
                    if block.name == "produce_verdict":
                        verdict_json = block.input.get("verdict_json", "{}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"status": "verdict_received"})
                        })
                    else:
                        result = dispatch_tool(block.name, block.input)
                        if verbose:
                            print(f"  Result: {json.dumps(result)[:200]}...")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

            # If produce_verdict was called, parse and return immediately
            if verdict_json:
                try:
                    text = verdict_json.strip()
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    return {"error": "produce_verdict contained invalid JSON", "raw": verdict_json}

            messages.append({"role": "user", "content": tool_results})

        # Model finished reasoning — extract JSON output
        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    text = block.text.strip()
                    # Extract JSON from the response
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()
                    # Find JSON object
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        try:
                            return json.loads(text[start:end])
                        except json.JSONDecodeError:
                            return {"error": "Agent produced invalid JSON", "raw": text}
            return {"error": "No text response from agent"}

        else:
            return {"error": f"Unexpected stop reason: {response.stop_reason}"}

    return {"error": f"Agent exceeded {max_iterations} iterations without producing a verdict"}


# ── Mode 1: Coverage Audit ────────────────────────────────────────────

def run_coverage_audit(policy_id: str, policy_type: str,
                       industry: str = "any", client_id: str = None,
                       verbose: bool = False) -> dict:
    """
    Mode 1 — Proactive coverage audit of a SPECIFIC policy.
    Broker asks: "What are the vulnerabilities in THIS policy for this insured?"

    The policy_id is the subject. Risk patterns and playbooks are the lens.
    Every clause retrieval is filtered to this specific policy.

    Args:
        policy_id:   The indexed policy to audit (e.g. CA0001-2013)
        policy_type: Type of policy (commercial_auto, general_liability, etc.)
        industry:    The insured's industry (trucking, construction, etc.)
        verbose:     Print agent reasoning steps
    """
    system_prompt = open(
        os.path.join(os.path.dirname(__file__), "..", "prompts", "stress_test_system.txt")
    ).read()

    if client_id:
        client_id_hint = f"CLIENT ID: {client_id}"
        client_history_line = f'  - retrieve_client_history(client_id="{client_id}")'
    else:
        client_id_hint = "CLIENT ID: none — no client record is linked to this policy"
        client_history_line = (
            "  - (no client record is linked to this policy — skip retrieve_client_history "
            "and base personalization only on what the policy itself says)"
        )

    user_message = f"""MODE 1 — COVERAGE AUDIT

You are auditing a specific policy for a broker. Use ALL available intelligence sources.

SUBJECT POLICY ID: {policy_id}
POLICY TYPE: {policy_type}
INSURED INDUSTRY: {industry}
{client_id_hint}

STEP 1 — Load context (call in parallel where possible):
  - load_playbook(policy_type="{policy_type}")
  - retrieve_risk_patterns(scenario_type="{policy_type}", industry="{industry}")
{client_history_line}
  - retrieve_eo_claims(policy_type="{policy_type}", industry="{industry}")

STEP 2 — Get market intelligence. For each candidate coverage_area surfaced by the risk
patterns or the E&O claims you just read, call:
  - retrieve_industry_losses(industry="{industry}", policy_type="{policy_type}")
  - retrieve_carrier_decisions(policy_type="{policy_type}", coverage_area="<area>")

  These return RAW RECORDS plus live-computed outcome breakdowns (counts, not
  percentages) for everything matching your filter. Compute the rates yourself:
  e.g. if outcome_breakdown shows denied=340 out of total_matching_claims=1000,
  that's a 34% denial rate — say so explicitly, and show the arithmetic.

STEP 3 — Read the subject policy (policy_id="{policy_id}" on EVERY call):
  For each HIGH/CRITICAL risk identified, search THIS SPECIFIC POLICY for:
  - The coverage clause that should apply
  - The exclusion or condition that creates the risk
  Always pass policy_id="{policy_id}" — never search other policies.

STEP 4 — Synthesize and produce verdict:
  Each risk finding must integrate:
  - What THIS POLICY actually says (from policy clauses)
  - How often this causes denied claims (computed from eo-claims-raw outcome counts)
  - How bad the losses are (computed from industry-losses severity + paid amounts)
  - Whether this carrier type enforces it strictly (computed from carrier-decisions outcome counts)
  - Whether THIS CLIENT has prior history with this issue (from client history)

  A risk with a prior client denial + a carrier-decisions sample showing ~90%
  upheld_denial + E&O claims averaging $500K+ settlements is CRITICAL. A risk with
  no client history, a ~30% denial rate, and modest severity is MEDIUM.
  Always show your arithmetic (X of Y records = Z%) — never state a rate without
  the underlying counts you computed it from.

Call produce_verdict with your audit in MODE 1 format when done."""

    messages = [{"role": "user", "content": user_message}]

    iteration = 0
    max_iterations = 12

    while iteration < max_iterations:
        iteration += 1
        force_verdict = iteration == max_iterations

        if force_verdict:
            messages.append({
                "role": "user",
                "content": "You have reached the maximum number of research steps. "
                            "Call produce_verdict now with your best-available audit "
                            "based on everything retrieved so far. Note any missing "
                            "information in 'knowledge_gaps' and lower 'confidence' accordingly."
            })

        response = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            tool_choice={"type": "tool", "name": "produce_verdict"} if force_verdict else {"type": "auto"},
            messages=messages
        )

        if verbose:
            print(f"\n[Iteration {iteration}] stop_reason: {response.stop_reason}")

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            verdict_json = None

            for block in response.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"  Tool: {block.name}({json.dumps(block.input)[:120]}...)")

                    if block.name == "produce_verdict":
                        verdict_json = block.input.get("verdict_json", "{}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"status": "audit_received"})
                        })
                    else:
                        result = dispatch_tool(block.name, block.input)
                        if verbose:
                            print(f"  Result: {json.dumps(result)[:150]}...")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

            if verdict_json:
                try:
                    text = verdict_json.strip()
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    return {"error": "produce_verdict contained invalid JSON", "raw": verdict_json}

            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    text = block.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        try:
                            return json.loads(text[start:end])
                        except json.JSONDecodeError:
                            return {"error": "Invalid JSON in response", "raw": text}
            return {"error": "No text response from agent"}
        else:
            return {"error": f"Unexpected stop reason: {response.stop_reason}"}

    return {"error": f"Agent exceeded {max_iterations} iterations"}


# ── Quick test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Running stress test — Demo Scenario 2\n")
    print("Scenario: Scheduled vehicle stolen from unsecured lot in non-listed state\n")

    result = run_stress_test(
        scenario="A covered vehicle was stolen overnight from an unsecured parking lot in Nevada. The vehicle is garaged and registered in Texas, which is the only state listed in the policy declarations. The insured filed a police report the same day. The vehicle was on a one-off delivery run to Nevada.",
        client_id="DEMO-CLIENT-001",
        verbose=True
    )

    print("\n" + "=" * 60)
    print("VERDICT:", result.get("verdict"))
    print("CONFIDENCE:", result.get("confidence"))
    print("=" * 60)
    print(json.dumps(result, indent=2))
