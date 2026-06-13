"""
Coverage stress test runner — two modes:

MODE 1 — Coverage Audit (proactive, policy-specific)
  python run_test.py audit CA0001-2013 trucking     (audit specific policy)
  python run_test.py audit CG0001-2007 construction
  python run_test.py policies                        (list available policy IDs)

MODE 2 — Scenario Test (reactive, evaluated against DEMO-CLIENT-001's policy)
  python run_test.py 1        (radius violation)
  python run_test.py 2        (vehicle theft)
  python run_test.py custom   (type your own scenario)

Interactive menu:
  python run_test.py
"""

import sys, json
from agents.stress_tester import run_stress_test, run_coverage_audit, list_indexed_policies

SCENARIOS = {
    "1": {
        "label": "Radius violation — driver 400 miles outside stated territory",
        "scenario": "A driver listed on the policy operates a covered vehicle 400 miles beyond the stated radius of operations at 11pm and causes a collision resulting in third-party bodily injury. The policy has a 500-mile radius stated in the declarations.",
    },
    "2": {
        "label": "Vehicle theft — stolen in non-listed state",
        "scenario": "A covered vehicle was stolen overnight from an unsecured parking lot in Nevada. The vehicle is garaged and registered in Texas, which is the only state listed in the policy declarations. The insured filed a police report the same day. The vehicle was on a one-off delivery run to Nevada.",
    },
}

def print_result(result: dict):
    print("\n" + "=" * 60)
    verdict = result.get("verdict", "ERROR")
    confidence = result.get("confidence", 0)
    color_map = {"COVERED": "GREEN", "CONDITIONAL": "YELLOW", "LIKELY_DENIED": "RED"}
    print(f"VERDICT:    {verdict}  ({color_map.get(verdict, '?')})")
    print(f"CONFIDENCE: {int(confidence * 100)}%")
    print(f"HUMAN REVIEW REQUIRED: {result.get('human_review_required', '?')}")
    print("=" * 60)

    findings = result.get("findings", [])
    if findings:
        print(f"\nFINDINGS ({len(findings)}):")
        for i, f in enumerate(findings, 1):
            print(f"\n  [{i}] {f.get('type', '').upper()} — {f.get('severity', '')} severity")
            print(f"      Clause: {f.get('clause_reference', 'N/A')}")
            print(f"      Impact: {f.get('implication', '')[:200]}")

    if result.get("recommended_action"):
        print(f"\nRECOMMENDED ACTION:\n  {result['recommended_action'][:300]}")

    if result.get("human_review_reason"):
        print(f"\nWHY HUMAN REVIEW:\n  {result['human_review_reason'][:200]}")

    if result.get("knowledge_gaps"):
        print(f"\nKNOWLEDGE GAPS:\n  {result['knowledge_gaps'][:200]}")

    print("\n[Full JSON saved to last_result.json]")
    with open("last_result.json", "w") as f:
        json.dump(result, f, indent=2)


POLICY_TYPE_MAP = {"ca": "commercial_auto", "gl": "general_liability",
                   "cm": "claims_made", "wc": "workers_comp"}

POLICY_ID_TO_TYPE = {
    "CA0001-2010":    "commercial_auto",
    "CA0001-2013":    "commercial_auto",
    "CG0001-2007":    "general_liability",
    "CG0001-2013":    "general_liability",
    "WC000000C":      "workers_comp",
    "WC-STATEFUND":   "workers_comp",
    "UMBRELLA-WBASNY":"umbrella",
}

def show_policies():
    print("\nAvailable policies in AI Search:\n")
    result = list_indexed_policies()
    for p in result["policies"]:
        policy_type = POLICY_ID_TO_TYPE.get(p["policy_id"], "unknown")
        print(f"  {p['policy_id']:<20} {p['form_number']:<20} {policy_type}")
    print()

def print_audit(result: dict):
    print("\n" + "=" * 60)
    print("COVERAGE AUDIT REPORT")
    print("=" * 60)
    print(f"\nSUMMARY:\n  {result.get('summary', 'N/A')}")

    risks = result.get("risks", [])
    print(f"\nRISKS IDENTIFIED ({len(risks)}):")
    for r in risks:
        print(f"\n  #{r.get('rank')} [{r.get('severity')}] {r.get('risk_title')}")
        print(f"  E&O Frequency: {r.get('eo_frequency', 'unknown')}")
        print(f"  What could go wrong: {r.get('what_could_go_wrong', '')[:200]}")
        print(f"  Fix: {r.get('fix', '')[:150]}")

    actions = result.get("immediate_actions", [])
    if actions:
        print(f"\nIMMEDIATE ACTIONS:")
        for a in actions:
            print(f"  - {a}")

    print("\n[Full JSON saved to last_result.json]")
    with open("last_result.json", "w") as f:
        json.dump(result, f, indent=2)


def main():
    args = sys.argv[1:]
    choice = args[0] if args else None

    # List policies
    if choice == "policies":
        show_policies()
        return

    # MODE 1 — Coverage Audit (policy-specific)
    if choice == "audit":
        if len(args) < 2:
            print("\nUsage: python run_test.py audit <POLICY_ID> [industry]")
            print("       python run_test.py policies   (to see available IDs)\n")
            show_policies()
            return

        policy_id = args[1].upper()
        industry  = args[2] if len(args) > 2 else "any"
        policy_type = POLICY_ID_TO_TYPE.get(policy_id)

        if not policy_type:
            print(f"\nUnknown policy ID: {policy_id}")
            show_policies()
            return

        print(f"\nMODE 1 — Coverage Audit")
        print(f"Subject policy : {policy_id}")
        print(f"Policy type    : {policy_type}")
        print(f"Industry       : {industry}\n")
        print("Agent is reasoning...\n")
        result = run_coverage_audit(
            policy_id=policy_id,
            policy_type=policy_type,
            industry=industry,
            verbose=True
        )
        print_audit(result)
        return

    # Interactive menu
    if not choice:
        print("\n--- MODE 1: Coverage Audit (policy-specific) ---")
        show_policies()
        print("  audit <POLICY_ID> <industry>   e.g. audit CA0001-2013 trucking")
        print("\n--- MODE 2: Scenario Test ---")
        for k, v in SCENARIOS.items():
            print(f"  {k}. {v['label']}")
        print("  custom. Enter your own scenario")
        choice = input("\nPick (audit <ID> <industry> / 1-2 / custom): ").strip()

        if choice.lower().startswith("audit"):
            parts = choice.split()
            if len(parts) < 2:
                print("Please provide a policy ID. Run 'python run_test.py policies' to see options.")
                return
            policy_id   = parts[1].upper()
            industry    = parts[2] if len(parts) > 2 else "any"
            policy_type = POLICY_ID_TO_TYPE.get(policy_id, "commercial_auto")
            result = run_coverage_audit(
                policy_id=policy_id,
                policy_type=policy_type,
                industry=industry,
                verbose=True
            )
            print_audit(result)
            return

    # MODE 2 — Scenario Test (always evaluated against DEMO-CLIENT-001's policy)
    if choice == "custom":
        scenario = input("Describe the claim scenario: ").strip()
    elif choice in SCENARIOS:
        s = SCENARIOS[choice]
        print(f"\nMODE 2 — Scenario Test")
        print(f"Client: DEMO-CLIENT-001 (Meridian Freight Solutions LLC)")
        print(f"Running: {s['label']}")
        print(f"Scenario: {s['scenario']}\n")
        scenario = s["scenario"]
    else:
        print(f"Unknown choice: {choice}")
        return

    print("Agent is reasoning... (verbose mode on)\n")
    result = run_stress_test(
        scenario=scenario,
        client_id="DEMO-CLIENT-001",
        verbose=True
    )
    print_result(result)


if __name__ == "__main__":
    main()
