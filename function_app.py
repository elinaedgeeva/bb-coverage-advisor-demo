"""
Azure Functions HTTP wrapper around the coverage stress test agent.
Callable from Copilot Studio via the HTTP connector.

Endpoints:
  POST /api/stress_test   -> stress_test_function   (Use Case 1: Coverage Stress Tester)
  GET  /api/policies      -> list_policies_function (lookup helper for the audit form)
  POST /api/parse_schedule -> parse_schedule_function (Use Case 2: stub, not yet built)

stress_test_function request body:
  Audit mode (proactive, policy-specific):
    {"mode": "audit", "policy_id": "CA0001-2013", "policy_type": "commercial_auto", "industry": "trucking"}

  Scenario mode (reactive, "what if" question, evaluated against a specific client's policy):
    {"mode": "scenario", "scenario": "...", "client_id": "DEMO-CLIENT-001"}
    (client_id defaults to "DEMO-CLIENT-001" if omitted)
"""

import json
import logging

import azure.functions as func

from agents.stress_tester import run_stress_test, run_coverage_audit, list_indexed_policies

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def _json_response(payload: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload),
        status_code=status_code,
        mimetype="application/json"
    )


@app.route(route="stress_test", methods=["POST"])
def stress_test_function(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "Request body must be valid JSON"}, 400)

    mode = body.get("mode", "scenario")

    try:
        if mode == "audit":
            policy_id = body.get("policy_id")
            policy_type = body.get("policy_type")
            industry = body.get("industry", "any")

            if not policy_id or not policy_type:
                return _json_response(
                    {"error": "audit mode requires 'policy_id' and 'policy_type'"}, 400
                )

            result = run_coverage_audit(
                policy_id=policy_id,
                policy_type=policy_type,
                industry=industry,
                verbose=False
            )

        elif mode == "scenario":
            scenario = body.get("scenario")
            client_id = body.get("client_id", "DEMO-CLIENT-001")

            if not scenario:
                return _json_response(
                    {"error": "scenario mode requires 'scenario'"}, 400
                )

            result = run_stress_test(
                scenario=scenario,
                client_id=client_id,
                verbose=False
            )

        else:
            return _json_response(
                {"error": f"Unknown mode '{mode}'. Use 'audit' or 'scenario'."}, 400
            )

        return _json_response(result, 200)

    except Exception as e:
        logging.exception("stress_test_function failed")
        return _json_response({"error": str(e)}, 500)


@app.route(route="policies", methods=["GET"])
def list_policies_function(req: func.HttpRequest) -> func.HttpResponse:
    try:
        result = list_indexed_policies()
        return _json_response(result, 200)
    except Exception as e:
        logging.exception("list_policies_function failed")
        return _json_response({"error": str(e)}, 500)


@app.route(route="parse_schedule", methods=["POST"])
def parse_schedule_function(req: func.HttpRequest) -> func.HttpResponse:
    # Use Case 2 (PDF Schedule Parser) agent has not been built yet — see PLAN.md Day 3.
    return _json_response(
        {"error": "parse_schedule is not yet implemented — Use Case 2 is pending."}, 501
    )
