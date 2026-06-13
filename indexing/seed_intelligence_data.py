"""
Seeds E&O statistics, industry benchmarks, and carrier practices indices.
Also uploads a demo client history JSON to Blob Storage.
Run: python indexing/seed_intelligence_data.py
"""

import os, json
from dotenv import load_dotenv
load_dotenv(override=True)

from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential

def get_client(index_name):
    return SearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name=index_name,
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
    )

# ── E&O STATISTICS ────────────────────────────────────────────────────
EO_STATS = [
    {
        "id": "eo-ca-001",
        "scenario_type": "commercial_auto",
        "industry": "trucking",
        "coverage_area": "radius_restriction",
        "denial_rate_pct": 34.2,
        "avg_settlement_usd": 187000,
        "sample_size": 412,
        "primary_cause": "Vehicle operated beyond stated radius without endorsement CA 01 21",
        "broker_error": "Broker failed to disclose radius restriction to insured or failed to bind extension endorsement when operations expanded",
        "key_finding": "34% of commercial auto liability claims in trucking involving out-of-area operations are denied. Average E&O settlement when broker is found liable: $187K. Highest risk period: Q4 when seasonal freight increases route distances.",
        "data_period": "2020-2024"
    },
    {
        "id": "eo-ca-002",
        "scenario_type": "commercial_auto",
        "industry": "trucking",
        "coverage_area": "unlisted_driver",
        "denial_rate_pct": 41.7,
        "avg_settlement_usd": 234000,
        "sample_size": 287,
        "primary_cause": "Driver not listed on scheduled driver endorsement, policy restricted to listed drivers only",
        "broker_error": "Broker placed coverage with carrier using scheduled driver manuscript endorsement without advising insured of the restriction or ensuring all drivers are listed",
        "key_finding": "Unlisted driver claims are denied at 41.7% rate when policy contains scheduled driver endorsement. E&O exposure is highest when broker switches carriers without reviewing endorsement differences. New driver onboarding without policy update is the most common trigger.",
        "data_period": "2020-2024"
    },
    {
        "id": "eo-ca-003",
        "scenario_type": "commercial_auto",
        "industry": "any",
        "coverage_area": "hnoa_gap",
        "denial_rate_pct": 88.3,
        "avg_settlement_usd": 156000,
        "sample_size": 194,
        "primary_cause": "Employee personal vehicle used for business, no HNOA coverage on CA policy",
        "broker_error": "Broker did not ask about employee personal vehicle use for business or did not add HNOA symbols when usage was known",
        "key_finding": "When HNOA coverage is absent and an employee causes an accident in their personal vehicle on company business, 88% of employers face uninsured vicarious liability. Average exposure per incident: $156K. Most common in professional services, real estate, and distribution companies.",
        "data_period": "2021-2024"
    },
    {
        "id": "eo-ca-004",
        "scenario_type": "commercial_auto",
        "industry": "trucking",
        "coverage_area": "cdl_mismatch",
        "denial_rate_pct": 67.4,
        "avg_settlement_usd": 312000,
        "sample_size": 89,
        "primary_cause": "Class B CDL driver operating Class A vehicle, carrier denied on unqualified operator grounds",
        "broker_error": "Broker did not verify CDL class requirements or did not update policy when fleet composition changed to include heavier vehicles",
        "key_finding": "CDL class mismatch claims are denied at 67% rate and carry highest average severity ($312K) due to catastrophic loss potential of large commercial vehicles. Most common when trucking companies expand to larger equipment without updating driver qualifications.",
        "data_period": "2019-2024"
    },
    {
        "id": "eo-gl-001",
        "scenario_type": "general_liability",
        "industry": "construction",
        "coverage_area": "completed_operations",
        "denial_rate_pct": 52.1,
        "avg_settlement_usd": 428000,
        "sample_size": 634,
        "primary_cause": "Property damage from completed work excluded under your-work exclusion, no completed operations coverage confirmed",
        "broker_error": "Broker assumed completed operations was automatic or did not confirm it was included in products-completed ops aggregate",
        "key_finding": "Completed operations claims in construction are denied 52% of the time, with average E&O settlements of $428K — the highest across all GL coverage areas. Primary trigger: broker fails to confirm completed operations is included and adequately funded. Risk peaks on projects over $2M contract value.",
        "data_period": "2019-2024"
    },
    {
        "id": "eo-gl-002",
        "scenario_type": "general_liability",
        "industry": "any",
        "coverage_area": "pollution_exclusion",
        "denial_rate_pct": 61.8,
        "avg_settlement_usd": 198000,
        "sample_size": 347,
        "primary_cause": "Absolute pollution exclusion applied to loss that insured believed was covered",
        "broker_error": "Broker did not advise insured that absolute pollution exclusion applies beyond traditional environmental contamination",
        "key_finding": "61.8% of pollution-related GL claims are denied under absolute pollution exclusion. Courts have applied it to fuel spills, chemical exposure, and biological agents. Insured expectation gap is highest in manufacturing, transportation, and cleaning services industries.",
        "data_period": "2020-2024"
    },
    {
        "id": "eo-cm-001",
        "scenario_type": "claims_made",
        "industry": "professional_services",
        "coverage_area": "retroactive_date",
        "denial_rate_pct": 91.2,
        "avg_settlement_usd": 543000,
        "sample_size": 218,
        "primary_cause": "Claim arises from act before retroactive date due to carrier switch setting retro date to new inception",
        "broker_error": "Broker placed renewal with new carrier without matching retroactive date to original policy inception",
        "key_finding": "Retroactive date gaps are denied 91% of the time — the highest denial rate of any coverage issue. Average E&O settlement: $543K. This is the single most costly broker error in professional lines. 73% of cases involve carrier switches at renewal where the broker failed to specify the original retroactive date.",
        "data_period": "2018-2024"
    },
    {
        "id": "eo-cm-002",
        "scenario_type": "claims_made",
        "industry": "any",
        "coverage_area": "tail_coverage",
        "denial_rate_pct": 97.4,
        "avg_settlement_usd": 387000,
        "sample_size": 156,
        "primary_cause": "Claim filed after policy cancellation, no tail/ERP purchased, broker never presented option",
        "broker_error": "Broker failed to advise insured of extended reporting period (tail coverage) option at cancellation or non-renewal",
        "key_finding": "When a claims-made policy is cancelled without tail coverage, virtually all subsequent claims are denied (97%). Broker E&O liability is near-certain when the insured was not advised of the ERP option in writing. Average E&O settlement: $387K. Required by most state bar associations to document ERP discussion at every claims-made cancellation.",
        "data_period": "2019-2024"
    },
    {
        "id": "eo-wc-001",
        "scenario_type": "workers_comp",
        "industry": "construction",
        "coverage_area": "misclassification",
        "denial_rate_pct": 78.3,
        "avg_settlement_usd": 224000,
        "sample_size": 291,
        "primary_cause": "Workers classified as independent contractors determined to be employees, WC exposure uninsured",
        "broker_error": "Broker accepted client's classification of workers as contractors without independent verification or did not advise of misclassification risk",
        "key_finding": "78% of WC misclassification claims result in uninsured exposure. Average regulatory penalty plus uninsured claim cost: $224K. Construction and transportation sectors account for 67% of all misclassification cases. DOL audits have increased 340% since 2020.",
        "data_period": "2020-2024"
    },
]

# ── INDUSTRY BENCHMARKS ───────────────────────────────────────────────
BENCHMARKS = [
    {
        "id": "bench-trucking-001",
        "industry": "trucking",
        "loss_type": "liability_bodily_injury",
        "trend": "increasing",
        "freq_per_100_units": 8.3,
        "avg_severity_usd": 487000,
        "description": "Trucking liability BI claims frequency: 8.3 per 100 power units annually. Nuclear verdicts (>$10M) have increased 235% since 2019.",
        "risk_implication": "Standard $1M CSL limits may be inadequate. Brokers should be discussing umbrella limits of $5M+ for trucking accounts with long-haul exposure.",
        "data_source": "ATRI Commercial Trucking Loss Study 2024",
        "data_year": 2024
    },
    {
        "id": "bench-trucking-002",
        "industry": "trucking",
        "loss_type": "cargo_theft",
        "trend": "increasing",
        "freq_per_100_units": 2.1,
        "avg_severity_usd": 147000,
        "description": "Cargo theft: 2.1 incidents per 100 trailers annually. Food and beverage is #1 targeted commodity (31%). Electronics second (24%). Average theft occurs at unsecured parking within 200 miles of origin.",
        "risk_implication": "Unattended vehicle exclusions in cargo forms are being enforced strictly. Insureds operating in Southeast US and California corridors face 3x average theft frequency.",
        "data_source": "CargoNet Annual Theft Report 2024",
        "data_year": 2024
    },
    {
        "id": "bench-trucking-003",
        "industry": "trucking",
        "loss_type": "physical_damage",
        "trend": "stable",
        "freq_per_100_units": 14.7,
        "avg_severity_usd": 38000,
        "description": "Physical damage frequency: 14.7 claims per 100 vehicles. Collision accounts for 71%, comprehensive 29%. Repair costs have increased 42% since 2020 due to parts shortages and labor rates.",
        "risk_implication": "Stated value and agreed value disputes are increasing. Brokers should ensure insured vehicles are properly scheduled with current values. Underinsurance at claim time is now common.",
        "data_source": "FMCSA National Safety Data 2024",
        "data_year": 2024
    },
    {
        "id": "bench-construction-001",
        "industry": "construction",
        "loss_type": "bodily_injury_third_party",
        "trend": "increasing",
        "freq_per_100_units": 6.4,
        "avg_severity_usd": 312000,
        "description": "Construction GL BI claims: 6.4 per $10M revenue annually. Subcontractor-related claims account for 58% of all construction GL losses.",
        "risk_implication": "Your-work and subcontractor exclusions are the primary denial mechanism. Completed operations aggregate adequacy is critical — 34% of construction accounts are underinsured on products-completed ops aggregate.",
        "data_source": "IRMI Construction Risk Profile 2024",
        "data_year": 2024
    },
    {
        "id": "bench-professional-001",
        "industry": "professional_services",
        "loss_type": "errors_omissions",
        "trend": "increasing",
        "freq_per_100_units": 4.2,
        "avg_severity_usd": 198000,
        "description": "E&O claims in professional services: 4.2 per 100 firms annually. Technology E&O growing fastest at 18% YoY. Cyber-related E&O claims now account for 31% of all professional liability losses.",
        "risk_implication": "Claims-made form nuances are increasingly cited in E&O cases against brokers. Retroactive date management is the #1 preventable broker error.",
        "data_source": "Advisen Professional Lines Market Report 2024",
        "data_year": 2024
    },
    {
        "id": "bench-trucking-004",
        "industry": "trucking",
        "loss_type": "workers_comp",
        "trend": "stable",
        "freq_per_100_units": 11.2,
        "avg_severity_usd": 52000,
        "description": "Trucking WC frequency: 11.2 claims per 100 drivers annually. Driver fatigue-related injuries account for 34%. Loading/unloading injuries: 28%.",
        "risk_implication": "Multi-state operations without all states listed in WC policy is the primary coverage gap. Brokers placing trucking WC must verify all states of operation are scheduled.",
        "data_source": "NCCI Industry Segment Report 2024",
        "data_year": 2024
    },
]

# ── CARRIER PRACTICES ─────────────────────────────────────────────────
CARRIER_PRACTICES = [
    {
        "id": "cp-001",
        "carrier_type": "standard_market",
        "scenario_type": "commercial_auto",
        "enforcement_rate_pct": 78.4,
        "practice_name": "Radius restriction enforcement — standard market carriers",
        "description": "Standard market commercial auto carriers (Travelers, Hartford, Liberty Mutual, Nationwide) enforce radius restrictions in 78% of disputed claims. Enforcement rate increases to 91% when the loss occurs more than 200 miles beyond the stated radius.",
        "broker_advisory": "Never assume a standard market carrier will waive a radius restriction post-loss. If the insured operates routes that could exceed the stated radius even occasionally, bind CA 01 21 or equivalent at inception. Document the discussion in the file.",
        "common_endorsement": "CA 01 21 - Radius of Operations Extension"
    },
    {
        "id": "cp-002",
        "carrier_type": "excess_surplus",
        "scenario_type": "commercial_auto",
        "enforcement_rate_pct": 43.2,
        "practice_name": "Radius restriction enforcement — E&S carriers",
        "description": "Excess and surplus lines carriers are significantly more flexible on radius enforcement, denying only 43% of radius-related claims. E&S carriers typically use manuscript forms with territory definitions rather than strict mileage radius.",
        "broker_advisory": "E&S markets offer more flexibility but manuscript form language varies significantly. Always obtain and review the full policy form before binding E&S commercial auto — do not assume standard CA 00 01 terms apply.",
        "common_endorsement": "Carrier-specific manuscript territory endorsement"
    },
    {
        "id": "cp-003",
        "carrier_type": "standard_market",
        "scenario_type": "commercial_auto",
        "enforcement_rate_pct": 84.1,
        "practice_name": "Scheduled driver enforcement — standard market",
        "description": "When a standard market carrier attaches a scheduled driver endorsement (increasingly common since 2021), unlisted driver claims are denied at 84% rate. This practice has grown 67% since 2019 as carriers seek to control adverse selection in commercial auto.",
        "broker_advisory": "Always check for scheduled driver endorsements when reviewing commercial auto policies, especially on truck risks. If present, maintain a current driver list and update mid-term when drivers are added. Carriers are not obligated to provide coverage for unlisted drivers even under permissive use.",
        "common_endorsement": "CA 99 10 - Drive Other Car Coverage / Scheduled Driver Endorsement"
    },
    {
        "id": "cp-004",
        "carrier_type": "standard_market",
        "scenario_type": "general_liability",
        "enforcement_rate_pct": 71.3,
        "practice_name": "Absolute pollution exclusion enforcement — GL standard market",
        "description": "Standard market GL carriers enforce absolute pollution exclusion in 71% of pollution-related claims. Carriers have successfully applied it to diesel fuel spills (87% enforcement), chemical cleaning agents (79%), and mold/biological agents (63%).",
        "broker_advisory": "The absolute pollution exclusion is not limited to traditional environmental contamination. Any insured handling chemicals, fuels, fertilizers, or biological materials needs a pollution liability policy or endorsement. The GL pollution exclusion will not protect them.",
        "common_endorsement": "CG 24 15 - Pollution Exclusion Amendment / Separate Pollution Liability Policy"
    },
    {
        "id": "cp-005",
        "carrier_type": "standard_market",
        "scenario_type": "claims_made",
        "enforcement_rate_pct": 96.8,
        "practice_name": "Retroactive date enforcement — E&O and professional liability",
        "description": "Professional liability carriers enforce retroactive date exclusions in 96.8% of cases where the alleged act occurred before the retroactive date. There is virtually no carrier discretion on this provision — it is a fundamental term of claims-made coverage.",
        "broker_advisory": "Retroactive date is non-negotiable post-loss. The only solution is prevention: always specify the original retroactive date when placing renewal with a new carrier, and document it in the binder and confirmation of coverage. Never accept a retroactive date of 'policy inception' on a renewal account.",
        "common_endorsement": "Retroactive Date Endorsement — must match original policy inception date"
    },
    {
        "id": "cp-006",
        "carrier_type": "specialty",
        "scenario_type": "commercial_auto",
        "enforcement_rate_pct": 91.7,
        "practice_name": "MCS-90 subrogation recovery — trucking specialty carriers",
        "description": "Specialty trucking carriers that pay claims under MCS-90 mandate pursue subrogation against the insured in 91.7% of cases where the underlying policy exclusion would have barred the claim. The MCS-90 creates carrier payment obligation to the public but does not waive the carrier's right to recover from the insured.",
        "broker_advisory": "Insureds subject to MCS-90 must understand that the endorsement does not provide coverage — it provides a government-mandated payment guarantee. If an insured operates under excluded circumstances (unlisted driver, out-of-radius), the carrier will pay the public claimant and then sue the insured for reimbursement.",
        "common_endorsement": "MCS-90 - Endorsement for Motor Carrier Policies of Insurance"
    },
]

def seed_index(index_name, records):
    client = get_client(index_name)
    result = client.upload_documents(records)
    success = sum(1 for r in result if r.succeeded)
    print(f"  Seeded {success}/{len(records)} records into '{index_name}'")

def upload_client_history():
    client_history = {
        "client_id": "DEMO-CLIENT-001",
        "client_name": "Meridian Freight Solutions LLC",
        "industry": "trucking",
        "years_as_client": 6,
        "annual_premium": 187400,
        "primary_policy_type": "commercial_auto",
        "fleet_size": 14,
        "policy_history": [
            {
                "policy_year": "2024-2025",
                "carrier": "Travelers",
                "policy_id": "CA0001-2013",
                "premium": 187400,
                "stated_radius": "500 miles",
                "driver_count": 11,
                "renewal_notes": "Fleet expanded from 10 to 14 units. Two new CDL-B drivers added. Radius not reviewed."
            },
            {
                "policy_year": "2023-2024",
                "carrier": "Travelers",
                "premium": 164200,
                "stated_radius": "500 miles",
                "driver_count": 10,
                "renewal_notes": "Clean renewal. No changes to operations disclosed."
            }
        ],
        "claims_history": [
            {
                "claim_id": "CLM-2022-0441",
                "date": "2022-09-14",
                "type": "liability_bodily_injury",
                "description": "Driver operating vehicle on route to Nashville TN — 680 miles from Dallas TX base. Collision with passenger vehicle at intersection. Third party BI claim.",
                "status": "DENIED",
                "denial_reason": "Vehicle operated 180 miles beyond 500-mile stated radius. Carrier denied under radius restriction. No CA 01 21 endorsement on file.",
                "paid_amount": 0,
                "reserve": 0,
                "broker_action": "Coverage dispute filed. Settled via E&O carrier — insured not compensated. Broker paid $47,000 E&O settlement.",
                "flag": "PRIOR_RADIUS_DENIAL"
            },
            {
                "claim_id": "CLM-2023-0187",
                "date": "2023-03-22",
                "type": "physical_damage_collision",
                "description": "Unit 07 (2020 Freightliner) rear-end collision on I-35. Driver James Whitfield.",
                "status": "PAID",
                "paid_amount": 34200,
                "reserve": 0,
                "broker_action": "Standard claim. No coverage issues."
            },
            {
                "claim_id": "CLM-2024-0033",
                "date": "2024-01-08",
                "type": "cargo_theft",
                "description": "Electronics cargo stolen from Unit 03 parked overnight at unsecured lot in Houston TX. Driver left vehicle unattended for 14 hours.",
                "status": "DISPUTED",
                "denial_reason": "Cargo form theft exclusion — vehicle unattended in unsecured facility for more than 8 hours. Claim under review.",
                "paid_amount": 0,
                "reserve": 89000,
                "broker_action": "Coverage dispute ongoing. Carrier citing unattended vehicle exclusion.",
                "flag": "OPEN_CARGO_DISPUTE"
            }
        ],
        "risk_flags": [
            {
                "flag": "PRIOR_RADIUS_DENIAL",
                "date_added": "2022-10-01",
                "description": "Client had radius-based claim denial in 2022. Operations regularly extend to Nashville TN corridor (~680 miles). Radius endorsement never added.",
                "severity": "CRITICAL",
                "status": "UNRESOLVED"
            },
            {
                "flag": "DRIVER_SCHEDULE_OUTDATED",
                "date_added": "2024-01-15",
                "description": "Two CDL-B drivers (Maria Gonzalez, Robert Chen) added to fleet in Q4 2023. Policy driver schedule not updated. Neither driver is listed.",
                "severity": "HIGH",
                "status": "UNRESOLVED"
            },
            {
                "flag": "OPEN_CARGO_DISPUTE",
                "date_added": "2024-01-10",
                "description": "Active cargo theft dispute. Carrier citing unattended vehicle exclusion. Outcome pending.",
                "severity": "HIGH",
                "status": "OPEN"
            }
        ]
    }

    blob_service = BlobServiceClient.from_connection_string(
        os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    )
    container = "client-history"

    try:
        blob_service.create_container(container)
    except Exception:
        pass  # already exists

    blob_client = blob_service.get_blob_client(container=container, blob="DEMO-CLIENT-001.json")
    blob_client.upload_blob(json.dumps(client_history, indent=2), overwrite=True)
    print(f"  Uploaded client history: DEMO-CLIENT-001.json to '{container}'")

print("Seeding intelligence data...\n")
seed_index("eo-statistics",       EO_STATS)
seed_index("industry-benchmarks", BENCHMARKS)
seed_index("carrier-practices",   CARRIER_PRACTICES)
print()
upload_client_history()
print("\nAll intelligence data seeded successfully.")
print(f"  E&O statistics:      {len(EO_STATS)} records")
print(f"  Industry benchmarks: {len(BENCHMARKS)} records")
print(f"  Carrier practices:   {len(CARRIER_PRACTICES)} records")
print(f"  Client history:      1 demo client (DEMO-CLIENT-001)")
