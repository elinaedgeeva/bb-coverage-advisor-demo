"""
Seeds the risk-patterns AI Search index with structured institutional knowledge.
These are known risk patterns brokers should check — organized by scenario type,
industry, and severity. This is the "Layer 2" knowledge store.

Run once: python indexing/seed_risk_patterns.py
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_PATTERNS_INDEX"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

PATTERNS = [
    # ── COMMERCIAL AUTO ───────────────────────────────────────────────
    {
        "id": "ca-001",
        "scenario_type": "commercial_auto",
        "industry": "trucking",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "very_common",
        "risk_title": "Radius restriction — operation outside stated territory",
        "description": "CA 00 01 policies include territory-based radius restrictions. A vehicle operating beyond the stated radius may void physical damage and liability coverage unless a radius endorsement (CA 01 21 or equivalent) is attached.",
        "exclusion_reference": "CA 00 01 Part IV, Business Auto Conditions",
        "recommended_check": "Confirm CA 01 21 radius endorsement is attached. Verify stated radius matches actual operations including seasonal routes."
    },
    {
        "id": "ca-002",
        "scenario_type": "commercial_auto",
        "industry": "any",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "very_common",
        "risk_title": "Unlisted driver — scheduled driver requirement",
        "description": "Some CA forms limit coverage to scheduled drivers only via manuscript endorsement, overriding the standard permissive use language in CA 00 01. An unlisted driver causing a loss may result in a full denial.",
        "exclusion_reference": "CA 00 01 driver schedule endorsement — carrier manuscript form",
        "recommended_check": "Check whether policy uses open driver class or requires scheduled drivers. If scheduled, verify all drivers are listed including part-time and seasonal operators."
    },
    {
        "id": "ca-003",
        "scenario_type": "commercial_auto",
        "industry": "any",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "common",
        "risk_title": "CDL class mismatch — unqualified operator",
        "description": "A driver operating a vehicle that requires a higher CDL class than they hold is considered an unqualified operator. Most CA forms exclude losses caused by unqualified drivers.",
        "exclusion_reference": "CA 00 01 Conditions — driver qualification",
        "recommended_check": "Verify CDL class for each listed driver matches the class required for their assigned vehicle. Class B cannot operate Class A vehicles."
    },
    {
        "id": "ca-004",
        "scenario_type": "commercial_auto",
        "industry": "any",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "common",
        "risk_title": "Hired and non-owned auto — employee personal vehicle gap",
        "description": "If an employee uses their personal vehicle for company business and causes an accident, the employer may be vicariously liable. Without HNOA coverage on the CA policy, this exposure is uninsured.",
        "exclusion_reference": "CA 00 01 — covered autos symbols; HNOA endorsement absence",
        "recommended_check": "Confirm HNOA (symbols 8 and 9) is included on the policy. Especially critical for businesses where employees use personal vehicles for deliveries or client visits."
    },
    {
        "id": "ca-005",
        "scenario_type": "commercial_auto",
        "industry": "trucking",
        "carrier_type": "standard",
        "severity": "MEDIUM",
        "eo_frequency": "common",
        "risk_title": "Cargo coverage — theft from unattended vehicle exclusion",
        "description": "Many motor truck cargo forms exclude theft from unattended vehicles or require specific security conditions (locked vehicle, alarm, enclosed facility). Overnight parking at an unsecured lot is a common denial scenario.",
        "exclusion_reference": "Motor Truck Cargo form — theft exclusion conditions",
        "recommended_check": "Review cargo form theft conditions. Advise insured of parking and security requirements to maintain coverage."
    },

    # ── GENERAL LIABILITY ─────────────────────────────────────────────
    {
        "id": "gl-001",
        "scenario_type": "general_liability",
        "industry": "any",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "very_common",
        "risk_title": "Absolute pollution exclusion — broader than expected",
        "description": "The standard CG 00 01 absolute pollution exclusion has been applied by courts to fuels, chemicals, dust, and biological agents well beyond traditional environmental contamination. Many insureds are unaware of its scope.",
        "exclusion_reference": "CG 00 01 Section I, Coverage A, Exclusion f",
        "recommended_check": "Identify operations involving any chemical, fuel, biological, or particulate exposure. Confirm whether a pollution liability endorsement or separate PL policy is in force."
    },
    {
        "id": "gl-002",
        "scenario_type": "general_liability",
        "industry": "construction",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "very_common",
        "risk_title": "Your work exclusion — completed operations gap",
        "description": "CG 00 01 excludes property damage to the insured's own work arising out of it. Completed operations coverage must be explicitly confirmed and funded in the products-completed operations aggregate.",
        "exclusion_reference": "CG 00 01 Section I, Coverage A, Exclusions j and l",
        "recommended_check": "Verify completed operations is scheduled in declarations. Confirm products-completed ops aggregate is adequately funded relative to contract values."
    },
    {
        "id": "gl-003",
        "scenario_type": "general_liability",
        "industry": "construction",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "common",
        "risk_title": "Subcontractor work — faulty workmanship gap",
        "description": "Without a subcontractor exception endorsement, damage caused by a subcontractor's faulty work incorporated into the insured's project may be excluded under the your-work exclusion.",
        "exclusion_reference": "CG 00 01 Exclusion l — your work; subcontractor exception",
        "recommended_check": "Check whether the policy includes a subcontractor exception to the your-work exclusion. If not, damage from sub's work is excluded."
    },
    {
        "id": "gl-004",
        "scenario_type": "general_liability",
        "industry": "professional_services",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "common",
        "risk_title": "Professional services exclusion — advice and consulting",
        "description": "Standard CG 00 01 excludes bodily injury or property damage arising out of the rendering or failure to render professional services. Businesses providing any advisory, design, or consulting service need separate E&O coverage.",
        "exclusion_reference": "CG 00 01 — professional services exclusion endorsement",
        "recommended_check": "Identify whether insured provides any advice, design, consulting, or professional service. If yes, confirm E&O or professional liability policy is in force."
    },

    # ── CLAIMS-MADE ───────────────────────────────────────────────────
    {
        "id": "cm-001",
        "scenario_type": "claims_made",
        "industry": "any",
        "carrier_type": "any",
        "severity": "CRITICAL",
        "eo_frequency": "very_common",
        "risk_title": "Retroactive date gap — prior acts uninsured",
        "description": "Claims-made policies only cover claims arising from acts on or after the retroactive date. If a broker moves an insured to a new carrier with a retroactive date that does not match the prior policy inception, prior acts are completely uninsured.",
        "exclusion_reference": "Claims-made insuring agreement — retroactive date",
        "recommended_check": "ALWAYS confirm the retroactive date on a new or renewal claims-made policy matches the original policy inception date. Never accept a retroactive date set to today for an ongoing risk."
    },
    {
        "id": "cm-002",
        "scenario_type": "claims_made",
        "industry": "any",
        "carrier_type": "any",
        "severity": "CRITICAL",
        "eo_frequency": "very_common",
        "risk_title": "Tail coverage not purchased on cancellation",
        "description": "When a claims-made policy is cancelled or non-renewed, the insured has a limited window to purchase extended reporting period (ERP/tail) coverage. Failure to advise the insured of this option is a leading cause of E&O claims against brokers.",
        "exclusion_reference": "Claims-made ERP provision",
        "recommended_check": "On any claims-made cancellation or non-renewal, document in writing that ERP options were presented, explained, and either accepted or declined by the insured."
    },

    # ── WORKERS COMPENSATION ──────────────────────────────────────────
    {
        "id": "wc-001",
        "scenario_type": "workers_comp",
        "industry": "any",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "common",
        "risk_title": "Employee vs. independent contractor misclassification",
        "description": "Workers compensation only covers employees. If workers classified as independent contractors are later determined to be employees by a court or regulatory body, the employer has uninsured WC exposure for that period.",
        "exclusion_reference": "WC policy — employee definition; statutory coverage",
        "recommended_check": "Review insured's contractor classification practices. Flag any workforce heavily reliant on 1099 workers in industries where misclassification is common (construction, gig economy, transportation)."
    },
    {
        "id": "wc-002",
        "scenario_type": "workers_comp",
        "industry": "construction",
        "carrier_type": "standard",
        "severity": "HIGH",
        "eo_frequency": "common",
        "risk_title": "Multi-state operations — state act coverage gap",
        "description": "WC policies cover employees under the laws of states listed in the declarations. Employees working in unlisted states may not be covered under that state's statutory requirements.",
        "exclusion_reference": "WC policy — Part One, Workers Compensation Insurance; state schedule",
        "recommended_check": "Verify all states where employees work are listed in the WC policy declarations, including states where employees travel regularly for work."
    },
]

result = client.upload_documents(PATTERNS)
success = sum(1 for r in result if r.succeeded)
print(f"Seeded {success}/{len(PATTERNS)} risk patterns into '{os.getenv('AZURE_SEARCH_PATTERNS_INDEX')}'")
