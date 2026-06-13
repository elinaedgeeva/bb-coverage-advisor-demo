"""
Creates raw intelligence indices — no pre-computed statistics.
Each record is a primary source data point that the agent reasons over directly.

Indices:
  eo-claims-raw      : Individual E&O claim records filed against brokers
  carrier-decisions  : Individual carrier coverage decision records
  industry-losses    : Individual commercial loss event records
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType
)
from azure.core.credentials import AzureKeyCredential

client = SearchIndexClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

# ── E&O CLAIMS RAW ────────────────────────────────────────────────────
# Individual E&O claim records. Each row = one actual E&O claim event.
# Outcome, amounts, and denial reasons are what happened — not summaries.
eo_index = SearchIndex(
    name="eo-claims-raw",
    fields=[
        SimpleField(name="id",               type=SearchFieldDataType.String, key=True),
        SimpleField(name="claim_year",        type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SimpleField(name="policy_type",       type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="industry",          type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="coverage_area",     type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="state",             type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="carrier_type",      type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="claim_outcome",     type=SearchFieldDataType.String, filterable=True, facetable=True),
        # outcome: denied | paid | litigated | settled | withdrawn
        SimpleField(name="eo_settlement_usd", type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SimpleField(name="insured_loss_usd",  type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SimpleField(name="broker_error_type", type=SearchFieldDataType.String, filterable=True),
        # broker_error_type: failed_to_advise | wrong_coverage | missed_endorsement |
        #                    failed_to_update | misrepresentation | inadequate_limits
        SearchableField(name="denial_reason", type=SearchFieldDataType.String),
        SearchableField(name="case_narrative",type=SearchFieldDataType.String),
        # case_narrative: free-text description of what happened — what the agent reads
    ]
)

# ── CARRIER DECISIONS ─────────────────────────────────────────────────
# Individual coverage decisions by carriers on disputed claims.
# Each row = one carrier's decision on a specific coverage dispute.
carrier_index = SearchIndex(
    name="carrier-decisions",
    fields=[
        SimpleField(name="id",               type=SearchFieldDataType.String, key=True),
        SimpleField(name="decision_year",     type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SimpleField(name="carrier_type",      type=SearchFieldDataType.String, filterable=True),
        # carrier_type: standard_market | excess_surplus | specialty | admitted | non_admitted
        SimpleField(name="policy_type",       type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="industry",          type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="coverage_area",     type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="decision",          type=SearchFieldDataType.String, filterable=True, facetable=True),
        # decision: upheld_denial | reversed_denial | partial_coverage | settled | paid_in_full
        SimpleField(name="endorsement_issue", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="state",             type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="claim_amount_usd",  type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SimpleField(name="paid_amount_usd",   type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SearchableField(name="denial_basis",  type=SearchFieldDataType.String),
        SearchableField(name="decision_narrative", type=SearchFieldDataType.String),
        # decision_narrative: what the carrier said and why — what the agent reads
    ]
)

# ── INDUSTRY LOSS RECORDS ─────────────────────────────────────────────
# Individual commercial loss events across industries.
# Each row = one claim event from a policyholder (not broker E&O — actual insured loss).
loss_index = SearchIndex(
    name="industry-losses",
    fields=[
        SimpleField(name="id",                type=SearchFieldDataType.String, key=True),
        SimpleField(name="loss_year",          type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SimpleField(name="industry",           type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="naics_code",         type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="policy_type",        type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="loss_type",          type=SearchFieldDataType.String, filterable=True),
        # loss_type: bodily_injury | property_damage | cargo_theft | physical_damage |
        #            workers_comp | professional_liability | pollution
        SimpleField(name="state",              type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="carrier_type",       type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="coverage_responded", type=SearchFieldDataType.String, filterable=True, facetable=True),
        # coverage_responded: yes | no | partial
        SimpleField(name="loss_severity_usd",  type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SimpleField(name="paid_usd",           type=SearchFieldDataType.Int32,  filterable=True, sortable=True),
        SimpleField(name="denial_reason",      type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="loss_narrative", type=SearchFieldDataType.String),
        # loss_narrative: what happened — what the agent reads to find patterns
    ]
)

for index in [eo_index, carrier_index, loss_index]:
    client.create_or_update_index(index)
    print(f"  Created index: {index.name}")

print("Done. All 3 raw intelligence indices created.")
