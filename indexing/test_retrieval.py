"""
Validates the full retrieval layer end-to-end.
Tests both AI Search indices with realistic insurance scenarios.
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

policy_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_POLICY_INDEX"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

patterns_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_PATTERNS_INDEX"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

def embed(text):
    return openai_client.embeddings.create(
        input=text,
        model=os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
    ).data[0].embedding

# ── TEST 1: Policy clause retrieval (Demo Scenario 1) ─────────────────
print("=" * 60)
print("TEST 1: Policy clause retrieval")
print("Query: driver operating outside stated radius causes liability loss")
print("=" * 60)

query = "driver operating outside stated radius causes liability loss"
vector = embed(query)

results = list(policy_client.search(
    search_text=query,
    vector_queries=[VectorizedQuery(
        vector=vector,
        k_nearest_neighbors=3,
        fields="content_vector"
    )],
    top=3,
    select=["content", "section_type", "policy_id", "page_number"]
))

if results:
    for i, r in enumerate(results, 1):
        print(f"\n  Result {i} [{r['policy_id']} | {r['section_type']} | p.{r['page_number']}]")
        print(f"  {r['content'][:200]}...")
    print(f"\n  PASS - Retrieved {len(results)} policy clauses")
else:
    print("  FAIL - No results returned")

# ── TEST 2: Risk pattern retrieval (commercial auto) ──────────────────
print("\n" + "=" * 60)
print("TEST 2: Risk pattern retrieval")
print("Filter: scenario_type = commercial_auto, severity = HIGH")
print("=" * 60)

patterns = list(patterns_client.search(
    search_text="*",
    filter="scenario_type eq 'commercial_auto' and severity eq 'HIGH'",
    top=5,
    select=["risk_title", "severity", "recommended_check"]
))

if patterns:
    for p in patterns:
        print(f"\n  [{p['severity']}] {p['risk_title']}")
        print(f"  -> {p['recommended_check'][:120]}...")
    print(f"\n  PASS - Retrieved {len(patterns)} risk patterns")
else:
    print("  FAIL - No patterns returned")

# ── TEST 3: Policy clause retrieval (Demo Scenario 2) ─────────────────
print("\n" + "=" * 60)
print("TEST 3: Policy clause retrieval")
print("Query: pollution exclusion chemical spill property damage")
print("=" * 60)

query2 = "pollution exclusion chemical spill property damage"
vector2 = embed(query2)

results2 = list(policy_client.search(
    search_text=query2,
    vector_queries=[VectorizedQuery(
        vector=vector2,
        k_nearest_neighbors=3,
        fields="content_vector"
    )],
    top=3,
    select=["content", "section_type", "policy_id"]
))

if results2:
    for i, r in enumerate(results2, 1):
        print(f"\n  Result {i} [{r['policy_id']} | {r['section_type']}]")
        print(f"  {r['content'][:200]}...")
    print(f"\n  PASS - Retrieved {len(results2)} policy clauses")
else:
    print("  FAIL - No results returned")

print("\n" + "=" * 60)
print("Retrieval layer validation complete.")
print("=" * 60)
