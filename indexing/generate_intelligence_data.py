"""
Generates and uploads 10,000+ raw records for each intelligence index.
Pure Python generation — no API calls, no pre-computed statistics.
The agent reads these records and discovers patterns itself.

Run: python indexing/generate_intelligence_data.py
Est. time: 5-10 minutes for 30,000 uploads
"""

import os, random, uuid, json
from datetime import date, timedelta
from dotenv import load_dotenv
load_dotenv(override=True)

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

random.seed(42)  # reproducible data

# ── Configuration ─────────────────────────────────────────────────────
N = 10000
BATCH = 500

POLICY_TYPES    = ["commercial_auto", "general_liability", "claims_made",
                   "workers_comp", "commercial_property", "umbrella"]
INDUSTRIES      = ["trucking", "construction", "professional_services",
                   "manufacturing", "retail", "healthcare", "real_estate",
                   "hospitality", "agriculture", "warehousing"]
STATES          = ["TX","CA","FL","NY","OH","IL","PA","GA","NC","MI",
                   "AZ","WA","CO","TN","MO","IN","MD","WI","MN","AL"]
CARRIER_TYPES   = ["standard_market", "excess_surplus", "specialty",
                   "admitted", "non_admitted"]
NAICS = {
    "trucking":              "484110",
    "construction":          "236220",
    "professional_services": "541611",
    "manufacturing":         "332999",
    "retail":                "441110",
    "healthcare":            "621111",
    "real_estate":           "531110",
    "hospitality":           "722511",
    "agriculture":           "111110",
    "warehousing":           "493110",
}

# Coverage areas with realistic outcome distributions (denial probability)
COVERAGE_AREAS = {
    "commercial_auto": [
        ("radius_restriction",       0.34),
        ("unlisted_driver",          0.42),
        ("hnoa_gap",                 0.88),
        ("cdl_class_mismatch",       0.67),
        ("vehicle_use_classification",0.29),
        ("cargo_theft_exclusion",    0.51),
        ("pollution_discharge",      0.63),
        ("territory_violation",      0.38),
    ],
    "general_liability": [
        ("completed_operations",     0.52),
        ("pollution_exclusion",      0.62),
        ("your_work_exclusion",      0.48),
        ("professional_services",    0.71),
        ("contractual_liability",    0.33),
        ("subcontractor_work",       0.44),
        ("employee_injury",          0.81),
    ],
    "claims_made": [
        ("retroactive_date_gap",     0.91),
        ("tail_coverage_absence",    0.97),
        ("late_notice",              0.74),
        ("known_circumstance",       0.68),
        ("prior_pending_exclusion",  0.55),
    ],
    "workers_comp": [
        ("independent_contractor",   0.78),
        ("multi_state_gap",          0.61),
        ("employer_liability",       0.44),
        ("subrogation_waiver",       0.29),
    ],
    "commercial_property": [
        ("coinsurance_penalty",      0.41),
        ("vacancy_exclusion",        0.67),
        ("flood_exclusion",          0.89),
        ("earth_movement",           0.94),
        ("equipment_breakdown",      0.33),
    ],
    "umbrella": [
        ("retained_limit_gap",       0.58),
        ("underlying_exhaustion",    0.42),
        ("pollution_exclusion",      0.71),
        ("professional_services",    0.63),
    ]
}

BROKER_ERRORS = [
    "failed_to_advise",
    "wrong_coverage",
    "missed_endorsement",
    "failed_to_update",
    "misrepresentation",
    "inadequate_limits",
    "wrong_policy_type",
    "failed_to_document",
]

# ── Narrative templates ───────────────────────────────────────────────

def rand_date(start_year=2015, end_year=2024):
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def rand_amount(lo, hi, skew="normal"):
    if skew == "high":
        return int(random.lognormvariate(0, 1) * (hi - lo) / 3 + lo)
    return random.randint(lo, hi)

# ── E&O claim narratives ──────────────────────────────────────────────
EO_NARRATIVES = {
    "radius_restriction": [
        "Insured trucking company rated for {radius}-mile radius. Driver dispatched {actual}-mile route to {city}. At-fault collision occurred. Carrier denied citing radius restriction. Broker had not bound CA 01 21 endorsement. Insured sued broker. {resolution}",
        "Policy declarations showed {radius}-mile operating radius. Insured expanded operations to {city} ({actual} miles) without notifying broker. Loss occurred during out-of-radius trip. Carrier enforced restriction. Broker E&O claim filed — broker failed to review radius at renewal. {resolution}",
        "Renewal processed without radius review. Insured's actual operations extended to {actual} miles but policy stated {radius}. Claim denied. Broker argued coverage territory definition but carrier prevailed. {resolution}",
    ],
    "unlisted_driver": [
        "New employee hired {months} months before loss. Broker not notified. Driver operated covered vehicle, caused {loss_type}. Policy contained scheduled driver endorsement — unlisted drivers excluded. Carrier denied. Broker E&O claimed for failure to advise insured to update driver schedule. {resolution}",
        "Insured added seasonal drivers without contacting broker. Carrier using manuscript scheduled driver form — permissive use language removed. Claim for {loss_type} denied. Broker had not explained the restriction at placement. {resolution}",
        "Driver roster changed but renewal processed without updated schedule. Unlisted driver caused at-fault accident. Standard market carrier enforced exclusion. E&O claim — broker failed to implement driver update process. {resolution}",
    ],
    "retroactive_date_gap": [
        "Insured switched E&O carriers at renewal. New carrier set retroactive date to policy inception rather than original date {years} years prior. Claim arose from work performed {months} months before new inception. Denied — prior acts not covered. Broker E&O settled for {eo_amt}. {resolution}",
        "Broker placed renewal without specifying retroactive date to new carrier. New retro date set to today. Client had undisclosed prior work that generated a claim {months} months later. Full prior acts exclusion applied. {resolution}",
        "Mid-term carrier change required — original carrier exited market. Replacement policy inception set as retroactive date by default. Claim from prior period denied. Broker had not flagged retro date issue to client in writing. {resolution}",
    ],
    "tail_coverage_absence": [
        "Claims-made policy cancelled at insured's request. Broker failed to present ERP/tail coverage options in writing. Claim filed {months} months post-cancellation for work performed during policy period. Denied — no coverage, no tail. Broker E&O for failure to advise. {resolution}",
        "Non-renewal issued by carrier. Broker sent non-renewal notice but did not discuss tail options. Insured did not purchase ERP. Subsequent claim denied. State bar association rules require documented tail discussion. {resolution}",
        "Insured sold business, cancelled professional liability. No tail purchased. Buyer's counsel filed claim against prior owner {months} months later. E&O carrier denied — no tail in force. Broker paid {eo_amt} E&O settlement. {resolution}",
    ],
    "completed_operations": [
        "General contractor completed {project_type} project. {months} months later, property damage discovered in completed work. GL carrier denied under your-work exclusion. Broker had not confirmed completed operations was included. Products-completed ops aggregate was zero. {resolution}",
        "Subcontractor work incorporated into completed project caused subsequent property damage. No subcontractor exception to your-work exclusion. Carrier denied. Broker E&O — completed operations adequacy not reviewed at renewal. {resolution}",
        "Insured's project completed {months} months before loss. Completed operations aggregate exhausted by prior claims — broker had not recommended increasing it at renewal. Claim paid from own pocket by insured. {resolution}",
    ],
    "pollution_exclusion": [
        "Cleaning service contractor used chemical solution that caused {damage_type}. GL carrier denied under absolute pollution exclusion. Insured expected coverage — broker had not explained exclusion applies to cleaning agents. {resolution}",
        "Fuel spill during truck servicing contaminated neighboring property. Absolute pollution exclusion applied — carrier denied. Broker had not recommended pollution liability endorsement despite knowing insured handled fuel. {resolution}",
        "HVAC contractor released refrigerant — third party injury claim. GL carrier denied — refrigerant classified as pollutant under absolute exclusion. Broker E&O claim for failure to advise on scope of exclusion. {resolution}",
    ],
    "cdl_class_mismatch": [
        "CDL-B driver assigned to Class A tractor-trailer (GVW {weight} lbs). Loss occurred during operation. Carrier denied — unqualified operator. Fleet had expanded to include Class A equipment but driver qualifications not reviewed. {resolution}",
        "Driver license upgrade overdue. CDL expired {months} months prior to loss. Carrier denied on unqualified/unlicensed operator grounds. Broker had not implemented CDL verification process at renewal. {resolution}",
        "New vehicle purchased mid-term — Class A requirement. Existing CDL-B drivers assigned by insured without notifying broker. At-fault accident. Carrier denied. Broker E&O for failure to review driver quals on mid-term vehicle addition. {resolution}",
    ],
    "hnoa_gap": [
        "Employee used personal vehicle for business delivery. At-fault accident. Employer vicariously liable. No HNOA on CA policy. Broker had not asked about personal vehicle use at application. Defense costs and judgment paid out of pocket. {resolution}",
        "Sales representative caused accident in personal vehicle while visiting client. Company sued. No HNOA — Symbol 9 absent from declarations. Broker placed policy without confirming whether employees used personal vehicles. {resolution}",
        "Real estate agent used personal vehicle for property showings. Accident — serious BI. Employer exposed. No HNOA. Broker E&O for failing to identify and place HNOA coverage for known personal vehicle use. {resolution}",
    ],
    "coinsurance_penalty": [
        "Commercial building insured for {insured_val}. Replacement cost at time of loss was {actual_val}. Coinsurance clause {pct}% — insured value below requirement. Partial loss of {loss_amt} settled at {settled_amt} after coinsurance penalty. Broker had not recommended revaluation in {years} years. {resolution}",
        "Contents undervalued at renewal. Broker processed renewal without contents revaluation — construction costs had increased 38% since last appraisal. Fire loss subject to coinsurance penalty. Insured recovered only 67% of loss. {resolution}",
        "Agreed value endorsement absent. Insured believed property was fully covered. Partial loss resulted in $280K coinsurance penalty. Broker had not offered agreed value option. {resolution}",
    ],
    "multi_state_gap": [
        "Employer expanded to {state2} without notifying broker. Employee injured in {state2}. WC policy listed only {state1}. {state2} statutory benefits applied — uninsured gap. State penalty assessed. Broker E&O claim. {resolution}",
        "Seasonal workers deployed to {state2} project. WC policy covered {state1} only. Workers injured — {state2} WC board found coverage gap. Employer paid benefits directly. Broker not notified of expansion. {resolution}",
        "Remote workers hired in {state2} during post-COVID expansion. WC policy not updated. Injury claim arose — {state2} benefit requirements differ significantly from {state1}. Gap in coverage. {resolution}",
    ],
}

DEFAULT_NARRATIVES = [
    "Coverage dispute arose from {policy_type} policy covering {industry} insured in {state}. Carrier denied claim based on policy language. Dispute resolved via {resolution}.",
    "{industry} insured filed claim under {policy_type} policy. Carrier issued denial based on policy exclusion. Broker E&O claim followed alleging failure to place adequate coverage. {resolution}",
]

RESOLUTIONS = [
    "E&O claim settled for {eo_amt}.",
    "Litigation filed. Case settled during discovery for {eo_amt}.",
    "E&O carrier defended. Verdict for defendant broker.",
    "E&O carrier paid {eo_amt} to resolve claim.",
    "Mediation resulted in {eo_amt} settlement.",
    "Claim withdrawn after coverage analysis showed broker not negligent.",
    "Arbitration awarded {eo_amt} to insured.",
]

CITIES = ["Nashville TN","Phoenix AZ","Atlanta GA","Denver CO","Seattle WA",
          "Chicago IL","Miami FL","Dallas TX","Portland OR","Boston MA",
          "Charlotte NC","Las Vegas NV","Minneapolis MN","Detroit MI","Houston TX"]

PROJECT_TYPES = ["commercial office building","retail strip center","apartment complex",
                 "warehouse distribution center","restaurant buildout","hotel renovation",
                 "industrial facility","school expansion","hospital wing","data center"]

DAMAGE_TYPES = ["property damage to adjacent units","employee respiratory illness",
                "environmental remediation costs","third party injury",
                "structural damage to neighboring property"]

def fill_narrative(template, industry, state, policy_type, outcome):
    eo_amt = f"${random.randint(15, 650) * 1000:,}"
    months = random.randint(2, 36)
    years = random.randint(1, 8)
    weight = random.choice(["26,001","33,000","50,000","80,000"])
    radius = random.choice([50, 100, 200, 300, 500])
    actual = radius + random.randint(50, 400)
    insured_val = random.randint(500, 3000) * 1000
    actual_val  = int(insured_val * random.uniform(1.2, 2.1))
    loss_amt    = random.randint(50, 500) * 1000
    settled_amt = int(loss_amt * random.uniform(0.4, 0.85))
    pct = random.choice([80, 90])
    state2 = random.choice([s for s in STATES if s != state])

    resolution = random.choice(RESOLUTIONS).format(eo_amt=eo_amt)

    try:
        return template.format(
            eo_amt=eo_amt, months=months, years=years, weight=weight,
            radius=radius, actual=actual, city=random.choice(CITIES),
            loss_type=random.choice(["bodily injury","property damage","cargo loss"]),
            project_type=random.choice(PROJECT_TYPES),
            damage_type=random.choice(DAMAGE_TYPES),
            insured_val=f"${insured_val:,}", actual_val=f"${actual_val:,}",
            loss_amt=f"${loss_amt:,}", settled_amt=f"${settled_amt:,}", pct=pct,
            state=state, state1=state, state2=state2,
            industry=industry, policy_type=policy_type, resolution=resolution
        )
    except KeyError:
        return f"{industry} insured in {state}. {policy_type} coverage dispute. {resolution}"

# ── CARRIER DECISION NARRATIVES ───────────────────────────────────────
CARRIER_NARRATIVES = {
    "radius_restriction": [
        "Insurer reviewed loss location vs. stated radius. Vehicle was {miles} miles beyond the {radius}-mile declaration. Carrier invoked radius restriction. Broker presented coverage territory argument — denied. Endorsement CA 01 21 was not in file.",
        "Claim submitted for loss at location {miles} miles beyond stated radius. Standard market carrier applied strict geographic interpretation. Upheld denial. No radius extension endorsement found in policy file.",
        "E&S carrier reviewed claim. Loss occurred outside stated radius by {miles} miles. Carrier exercised discretion — agreed to partial payment acknowledging ambiguity in territory definition. Settled at {pct}% of claimed amount.",
    ],
    "unlisted_driver": [
        "Carrier confirmed scheduled driver endorsement was in effect. Driver not listed. Denied. Permissive use language was superseded by manuscript endorsement CA 99 10.",
        "Claim submitted for loss caused by driver not on schedule. Standard carrier upheld denial citing manuscript scheduled driver endorsement. No exceptions for permissive use under this form.",
        "E&S carrier reviewed unlisted driver claim. Policy contained open driver class — standard permissive use applied. Claim paid in full. No scheduled driver restriction in this manuscript form.",
    ],
    "retroactive_date_gap": [
        "Professional liability carrier confirmed retroactive date on current policy. Act alleged to have occurred prior to retro date. Coverage not triggered. Denial upheld on retroactive date grounds — non-negotiable provision.",
        "Claims-made carrier issued denial letter citing retroactive date exclusion. Broker argued equitable tolling — rejected. Prior acts exclusion is unambiguous. Denial stands.",
        "New carrier retro date was set to policy inception. Prior carrier confirmed coverage lapsed. Gap in coverage confirmed. Neither carrier accepted the claim. Insured uninsured for the period.",
    ],
    "pollution_exclusion": [
        "GL carrier applied absolute pollution exclusion. Substance determined to be a pollutant as defined. Denial upheld — no exception for sudden and accidental release in this form version (post-1986 absolute form).",
        "Standard market carrier denied pollution claim. Insured argued sudden and accidental exception — not available under absolute exclusion form CG 00 01. Denial confirmed.",
        "E&S carrier using older sudden and accidental pollution form. Covered the release as it met the definition of sudden, accidental, and neither expected nor intended. Claim paid.",
    ],
    "completed_operations": [
        "GL carrier confirmed completed operations aggregate was zero — not selected. Your-work exclusion applied to property damage from completed project. Claim denied. No completed operations coverage.",
        "Carrier reviewed your-work exclusion. Damage was to insured's own completed work — squarely within exclusion. No subcontractor exception endorsement attached. Denial upheld.",
        "Products-completed ops aggregate confirmed in declarations. Claim submitted within policy period. Coverage responded. Paid {pct}% of claimed amount after deductible.",
    ],
}

DEFAULT_CARRIER_NARRATIVES = [
    "Carrier reviewed {policy_type} claim from {industry} insured. Decision: {decision}. Basis: policy language applied to facts presented. Amount at issue: ${amt:,}.",
    "{carrier_type} carrier issued {decision} on {policy_type} coverage dispute. {industry} insured. Coverage area: {coverage_area}. Decision based on policy exclusion.",
]

CARRIER_DECISIONS_MAP = {
    "upheld_denial": 0.60,
    "reversed_denial": 0.12,
    "partial_coverage": 0.15,
    "settled": 0.08,
    "paid_in_full": 0.05,
}

def pick_carrier_decision(denial_prob):
    if random.random() < denial_prob:
        return random.choices(
            ["upheld_denial", "partial_coverage", "settled"],
            weights=[0.75, 0.15, 0.10]
        )[0]
    else:
        return random.choices(
            ["reversed_denial", "paid_in_full", "partial_coverage"],
            weights=[0.40, 0.45, 0.15]
        )[0]

def fill_carrier_narrative(template, industry, state, policy_type, coverage_area, decision, carrier_type):
    miles = random.randint(50, 500)
    radius = random.choice([50, 100, 200, 500])
    pct = random.randint(40, 90)
    amt = random.randint(25, 850) * 1000
    try:
        return template.format(
            miles=miles, radius=radius, pct=pct, amt=amt,
            industry=industry, state=state, policy_type=policy_type,
            coverage_area=coverage_area, decision=decision, carrier_type=carrier_type
        )
    except KeyError:
        return f"{carrier_type} carrier decision on {policy_type} for {industry} insured: {decision}."

# ── LOSS RECORD NARRATIVES ────────────────────────────────────────────
LOSS_NARRATIVES = {
    "bodily_injury": [
        "{industry} operation. Third party bodily injury claim. Claimant alleged negligence during {operation}. Severity: ${amt:,}. Coverage {responded}.",
        "Slip and fall at {industry} premises. Medical expenses plus lost wages. Liability disputed. Settled ${amt:,}. GL {responded}.",
        "Vehicle operator caused collision injuring third party. BI claim ${amt:,}. Carrier {responded} under commercial auto.",
    ],
    "cargo_theft": [
        "Cargo theft from {industry} vehicle. {commodity} stolen. Vehicle was {condition} when theft occurred. Loss: ${amt:,}. Cargo coverage {responded}.",
        "Trailer contents stolen from {location}. Insured filed within {days} days. Cargo form {responded} — {condition} exclusion {applied}.",
        "Electronics cargo targeted at {location}. ${amt:,} loss. Unattended vehicle for {hours} hours. Carrier {responded}.",
    ],
    "property_damage": [
        "{industry} operation caused property damage to adjacent {property_type}. ${amt:,} repair cost. GL {responded}.",
        "Equipment malfunction caused ${amt:,} property damage. {industry} insured. Coverage {responded} under {policy_type}.",
        "Fire originating from {industry} premises spread to neighboring property. ${amt:,} total damage. Coverage {responded}.",
    ],
    "workers_comp": [
        "{injury_type} injury to employee of {industry} firm. Medical: ${med:,}. Lost wages: ${wage:,}. WC {responded}.",
        "Loading/unloading injury at {industry} facility. Employee required surgery. Total incurred: ${amt:,}. WC coverage {responded}.",
        "Driver fatigue-related injury. {industry} sector. Claim filed {days} days after incident. WC {responded}.",
    ],
    "pollution": [
        "Fuel spill during {industry} operations. Environmental remediation: ${amt:,}. GL pollution exclusion {applied}.",
        "Chemical release at {industry} site. Third party injury. ${amt:,} claim. Absolute pollution exclusion {applied} — {responded}.",
        "HVAC refrigerant discharge — {industry} contractor. BI and property claim. GL carrier {applied} absolute pollution exclusion.",
    ],
}

OPERATIONS = ["loading/unloading","delivery operations","parking lot","job site entry",
              "equipment operation","customer premises visit","routine maintenance"]
COMMODITIES = ["electronics","food/beverage","pharmaceuticals","automotive parts",
               "clothing/apparel","industrial equipment","consumer goods"]
LOCATIONS = ["truck stop","shipper dock","unsecured parking lot","warehouse yard",
             "customer facility","rest area","highway rest stop"]
PROPERTY_TYPES = ["commercial building","residential property","vehicle","equipment","inventory"]
INJURY_TYPES = ["back/spine","shoulder/rotator cuff","knee","hand/wrist","head/neck","fall-related"]

def fill_loss_narrative(template, industry, policy_type, coverage_responded):
    amt  = random.randint(10, 2000) * 1000
    med  = random.randint(5, 300) * 1000
    wage = random.randint(2, 100) * 1000
    days = random.randint(1, 90)
    hours= random.randint(1, 24)
    responded = "responded" if coverage_responded == "yes" else ("partially responded" if coverage_responded == "partial" else "did not respond — denied")
    applied = "applied" if coverage_responded == "no" else "did not apply"
    condition = random.choice(["locked","unlocked","alarmed","unattended"])
    try:
        return template.format(
            industry=industry, policy_type=policy_type, amt=amt,
            med=med, wage=wage, days=days, hours=hours,
            responded=responded, applied=applied, condition=condition,
            operation=random.choice(OPERATIONS),
            commodity=random.choice(COMMODITIES),
            location=random.choice(LOCATIONS),
            property_type=random.choice(PROPERTY_TYPES),
            injury_type=random.choice(INJURY_TYPES),
        )
    except KeyError:
        return f"{industry} insured. {policy_type} loss. Coverage {responded}. Amount: ${amt:,}."

# ── Upload helper ─────────────────────────────────────────────────────

def upload_batch(search_client, records, index_name):
    for i in range(0, len(records), BATCH):
        batch = records[i:i+BATCH]
        search_client.upload_documents(batch)
        pct = min(100, int((i + BATCH) / len(records) * 100))
        print(f"  {index_name}: {pct}% ({min(i+BATCH, len(records))}/{len(records)})", end="\r")
    print(f"  {index_name}: 100% ({len(records)}/{len(records)}) done.          ")

def get_client(index_name):
    return SearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name=index_name,
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
    )

# ── Generate E&O Claims ───────────────────────────────────────────────
def generate_eo_claims(n):
    records = []
    for i in range(n):
        policy_type = random.choice(POLICY_TYPES)
        industry    = random.choice(INDUSTRIES)
        state       = random.choice(STATES)
        carrier_type= random.choice(CARRIER_TYPES)
        broker_error= random.choice(BROKER_ERRORS)
        d           = rand_date()

        areas = COVERAGE_AREAS.get(policy_type, [("general_coverage", 0.35)])
        coverage_area, denial_prob = random.choice(areas)

        denied = random.random() < denial_prob
        outcome = random.choice(["denied","litigated","settled"]) if denied else random.choice(["paid","withdrawn","settled"])

        eo_settlement = 0
        if outcome in ["settled","litigated"] and denied:
            eo_settlement = random.randint(10, 800) * 1000
        insured_loss = random.randint(5, 500) * 1000 if not denied else 0

        templates = EO_NARRATIVES.get(coverage_area, DEFAULT_NARRATIVES)
        narrative  = fill_narrative(random.choice(templates), industry, state, policy_type, outcome)

        records.append({
            "id":               f"eo-{i:06d}",
            "claim_year":       d.year,
            "policy_type":      policy_type,
            "industry":         industry,
            "coverage_area":    coverage_area,
            "state":            state,
            "carrier_type":     carrier_type,
            "claim_outcome":    outcome,
            "eo_settlement_usd":eo_settlement,
            "insured_loss_usd": insured_loss,
            "broker_error_type":broker_error,
            "denial_reason":    coverage_area.replace("_", " ").title(),
            "case_narrative":   narrative,
        })
    return records

# ── Generate Carrier Decisions ────────────────────────────────────────
def generate_carrier_decisions(n):
    records = []
    for i in range(n):
        policy_type   = random.choice(POLICY_TYPES)
        industry      = random.choice(INDUSTRIES)
        state         = random.choice(STATES)
        carrier_type  = random.choice(CARRIER_TYPES)
        d             = rand_date()

        areas = COVERAGE_AREAS.get(policy_type, [("general_coverage", 0.45)])
        coverage_area, denial_prob = random.choice(areas)
        decision = pick_carrier_decision(denial_prob)

        claim_amount = random.randint(15, 2000) * 1000
        paid_amount  = 0 if "denial" in decision else int(claim_amount * random.uniform(0.3, 1.0))

        templates  = CARRIER_NARRATIVES.get(coverage_area, DEFAULT_CARRIER_NARRATIVES)
        narrative  = fill_carrier_narrative(
            random.choice(templates), industry, state, policy_type,
            coverage_area, decision, carrier_type
        )

        records.append({
            "id":                  f"cd-{i:06d}",
            "decision_year":       d.year,
            "carrier_type":        carrier_type,
            "policy_type":         policy_type,
            "industry":            industry,
            "coverage_area":       coverage_area,
            "decision":            decision,
            "endorsement_issue":   coverage_area,
            "state":               state,
            "claim_amount_usd":    claim_amount,
            "paid_amount_usd":     paid_amount,
            "denial_basis":        coverage_area.replace("_", " ").title(),
            "decision_narrative":  narrative,
        })
    return records

# ── Generate Industry Losses ──────────────────────────────────────────
LOSS_TYPES = ["bodily_injury","property_damage","cargo_theft","physical_damage",
              "workers_comp","professional_liability","pollution"]

COVERAGE_RESPOND_PROBS = {
    "bodily_injury":           ("yes", 0.71),
    "property_damage":         ("yes", 0.65),
    "cargo_theft":             ("partial", 0.49),
    "physical_damage":         ("yes", 0.78),
    "workers_comp":            ("yes", 0.82),
    "professional_liability":  ("partial", 0.61),
    "pollution":               ("no", 0.62),
}

def generate_industry_losses(n):
    records = []
    for i in range(n):
        industry      = random.choice(INDUSTRIES)
        policy_type   = random.choice(POLICY_TYPES)
        state         = random.choice(STATES)
        carrier_type  = random.choice(CARRIER_TYPES)
        loss_type     = random.choice(LOSS_TYPES)
        d             = rand_date()

        likely_response, response_prob = COVERAGE_RESPOND_PROBS.get(loss_type, ("partial", 0.5))
        r = random.random()
        if r < response_prob * 0.8:
            coverage_responded = likely_response
        elif r < response_prob:
            coverage_responded = "partial"
        else:
            coverage_responded = "no"

        severity = random.randint(5, 3000) * 1000
        paid     = 0 if coverage_responded == "no" else int(severity * random.uniform(0.4, 0.95))
        denial_reason = "" if coverage_responded == "yes" else \
            random.choice(["exclusion_applied","condition_violated",
                           "late_notice","misrepresentation","out_of_territory"])

        templates  = LOSS_NARRATIVES.get(loss_type, DEFAULT_NARRATIVES)
        narrative  = fill_loss_narrative(random.choice(templates), industry, policy_type, coverage_responded)

        records.append({
            "id":                 f"il-{i:06d}",
            "loss_year":          d.year,
            "industry":           industry,
            "naics_code":         NAICS.get(industry, "999999"),
            "policy_type":        policy_type,
            "loss_type":          loss_type,
            "state":              state,
            "carrier_type":       carrier_type,
            "coverage_responded": coverage_responded,
            "loss_severity_usd":  severity,
            "paid_usd":           paid,
            "denial_reason":      denial_reason,
            "loss_narrative":     narrative,
        })
    return records

# ── Main ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Generating {N:,} records per index ({N*3:,} total)...\n")

    print(f"[1/3] E&O Claims...")
    eo_records = generate_eo_claims(N)
    upload_batch(get_client("eo-claims-raw"), eo_records, "eo-claims-raw")

    print(f"[2/3] Carrier Decisions...")
    cd_records = generate_carrier_decisions(N)
    upload_batch(get_client("carrier-decisions"), cd_records, "carrier-decisions")

    print(f"[3/3] Industry Losses...")
    il_records = generate_industry_losses(N)
    upload_batch(get_client("industry-losses"), il_records, "industry-losses")

    print(f"\nDone. {N*3:,} raw records uploaded across 3 indices.")
    print(f"  eo-claims-raw:    {N:,} E&O claim records")
    print(f"  carrier-decisions:{N:,} carrier coverage decision records")
    print(f"  industry-losses:  {N:,} commercial loss event records")
    print(f"\nThe agent now discovers patterns from data — no pre-computed statistics.")
