"""
Creates both AI Search indices:
  - policy-docs   : chunked policy text with hybrid retrieval (BM25 + vector)
  - risk-patterns : structured institutional knowledge, filterable
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchFieldDataType,
)
from azure.core.credentials import AzureKeyCredential

client = SearchIndexClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
    profiles=[VectorSearchProfile(name="vec-profile", algorithm_configuration_name="hnsw")]
)

# ── INDEX 1: policy-docs ──────────────────────────────────────────────
policy_index = SearchIndex(
    name="policy-docs",
    fields=[
        SimpleField(name="id",           type=SearchFieldDataType.String, key=True),
        SearchableField(name="content",  type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SimpleField(name="policy_id",    type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="section_type", type=SearchFieldDataType.String, filterable=True),
        # section_type: declarations | insuring_agreement | exclusions |
        #               conditions | definitions | endorsement | body
        SimpleField(name="form_number",  type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="page_number",  type=SearchFieldDataType.Int32,  sortable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="vec-profile"
        )
    ],
    vector_search=vector_search
)

# ── INDEX 2: risk-patterns ────────────────────────────────────────────
patterns_index = SearchIndex(
    name="risk-patterns",
    fields=[
        SimpleField(name="id",            type=SearchFieldDataType.String, key=True),
        SimpleField(name="scenario_type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="industry",      type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="carrier_type",  type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="severity",      type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="eo_frequency",  type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="risk_title",        type=SearchFieldDataType.String),
        SearchableField(name="description",       type=SearchFieldDataType.String),
        SearchableField(name="recommended_check", type=SearchFieldDataType.String),
        SimpleField(name="exclusion_reference",   type=SearchFieldDataType.String),
    ]
)

print("Creating index: policy-docs ...")
client.create_or_update_index(policy_index)
print("  Done.")

print("Creating index: risk-patterns ...")
client.create_or_update_index(patterns_index)
print("  Done.")

# ── INDEX 3: eo-statistics ────────────────────────────────────────────
eo_index = SearchIndex(
    name="eo-statistics",
    fields=[
        SimpleField(name="id",                 type=SearchFieldDataType.String, key=True),
        SimpleField(name="scenario_type",      type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="industry",           type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="coverage_area",      type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="denial_rate_pct",    type=SearchFieldDataType.Double, sortable=True),
        SimpleField(name="avg_settlement_usd", type=SearchFieldDataType.Int32,  sortable=True),
        SimpleField(name="sample_size",        type=SearchFieldDataType.Int32),
        SearchableField(name="primary_cause",  type=SearchFieldDataType.String),
        SearchableField(name="broker_error",   type=SearchFieldDataType.String),
        SearchableField(name="key_finding",    type=SearchFieldDataType.String),
        SimpleField(name="data_period",        type=SearchFieldDataType.String),
    ]
)

# ── INDEX 4: industry-benchmarks ─────────────────────────────────────
benchmarks_index = SearchIndex(
    name="industry-benchmarks",
    fields=[
        SimpleField(name="id",                  type=SearchFieldDataType.String, key=True),
        SimpleField(name="industry",            type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="loss_type",           type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="trend",               type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="freq_per_100_units",  type=SearchFieldDataType.Double, sortable=True),
        SimpleField(name="avg_severity_usd",    type=SearchFieldDataType.Int32,  sortable=True),
        SearchableField(name="description",     type=SearchFieldDataType.String),
        SearchableField(name="risk_implication",type=SearchFieldDataType.String),
        SimpleField(name="data_source",         type=SearchFieldDataType.String),
        SimpleField(name="data_year",           type=SearchFieldDataType.Int32,  sortable=True),
    ]
)

# ── INDEX 5: carrier-practices ────────────────────────────────────────
carrier_index = SearchIndex(
    name="carrier-practices",
    fields=[
        SimpleField(name="id",                   type=SearchFieldDataType.String, key=True),
        SimpleField(name="carrier_type",         type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="scenario_type",        type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="enforcement_rate_pct", type=SearchFieldDataType.Double, sortable=True),
        SearchableField(name="practice_name",    type=SearchFieldDataType.String),
        SearchableField(name="description",      type=SearchFieldDataType.String),
        SearchableField(name="broker_advisory",  type=SearchFieldDataType.String),
        SimpleField(name="common_endorsement",   type=SearchFieldDataType.String),
    ]
)

print("Creating index: eo-statistics ...")
client.create_or_update_index(eo_index)
print("  Done.")

print("Creating index: industry-benchmarks ...")
client.create_or_update_index(benchmarks_index)
print("  Done.")

print("Creating index: carrier-practices ...")
client.create_or_update_index(carrier_index)
print("  Done.")

print("\nAll 5 indices created successfully.")
