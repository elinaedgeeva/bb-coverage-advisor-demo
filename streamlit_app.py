"""
B&B Coverage Advisor — Demo UI
-------------------------------
Thin reference client for the coverage stress-test agent. Calls the same
Python engine that's deployed as an Azure Function (function_app.py).

In production this becomes a Copilot Studio agent in Teams — same backend,
same JSON contract (see copilot_studio/stress_test_connector.swagger.json),
zero changes to the engine. This UI exists to demo the human-in-the-loop
experience without depending on Copilot Studio provisioning.

Run with:
    .venv\\Scripts\\Activate.ps1
    streamlit run streamlit_app.py
"""

import os

import streamlit as st

# On Streamlit Community Cloud, secrets are configured via the dashboard
# (st.secrets) rather than a .env file. Mirror them into os.environ so the
# existing dotenv-based clients (agents/stress_tester.py, services/llm_client.py)
# work unchanged both locally and when deployed.
for _k, _v in st.secrets.items():
    os.environ.setdefault(_k, str(_v))

from agents.stress_tester import run_stress_test, run_coverage_audit, retrieve_client_history
from run_test import SCENARIOS

st.set_page_config(page_title="B&B Coverage Advisor", page_icon="🛡️", layout="centered")

st.title("🛡️ B&B Coverage Advisor")
st.caption(
    "AI-powered coverage stress testing — every finding is grounded in retrieved policy "
    "language, this client's actual history, and institutional risk patterns."
)

VERDICT_ICON = {"COVERED": "🟢", "CONDITIONAL": "🟡", "LIKELY_DENIED": "🔴"}
SEVERITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢",
                 "critical": "🔴", "CRITICAL": "🔴", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

CLIENT_ID = "DEMO-CLIENT-001"


@st.cache_data(ttl=300)
def get_client():
    return retrieve_client_history(CLIENT_ID)["client"]


client = get_client()
policy = client["policy_history"][0]

# ── Active client context (always visible) ─────────────────────────────
with st.container(border=True):
    st.markdown(f"### 📁 {client['client_name']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Policy", policy["policy_id"])
    c2.metric("Carrier", policy["carrier"])
    c3.metric("Industry", client["industry"].replace("_", " ").title())
    c4.metric("Annual Premium", f"${client['annual_premium']:,}")

mode = st.sidebar.radio("Mode", ["Scenario Stress Test", "Coverage Audit"])
st.sidebar.divider()
st.sidebar.markdown(
    "**Architecture note**\n\n"
    "This UI is a thin client over the same Azure Function deployed at "
    "`bb-coverage-stress-tester.azurewebsites.net`. The Copilot Studio "
    "connector and Adaptive Card are built and ready to import — same "
    "API contract, different front door."
)

# ── Scenario Stress Test ──────────────────────────────────────────────
if mode == "Scenario Stress Test":
    st.subheader("Scenario Stress Test")
    st.write(
        f"Describe a claim scenario — the agent checks it against **{client['client_name']}'s** "
        f"actual policy ({policy['policy_id']}) and claims history, and surfaces coverage gaps, "
        f"exclusions, and ambiguities."
    )

    preset = st.selectbox(
        "Demo scenario",
        ["Custom"] + [f"{k}. {v['label']}" for k, v in SCENARIOS.items()],
    )

    if preset == "Custom":
        scenario = st.text_area("Scenario description", height=120)
    else:
        key = preset.split(".")[0]
        s = SCENARIOS[key]
        scenario = st.text_area("Scenario description", value=s["scenario"], height=120)

    run = st.button("Run Stress Test", type="primary")

    if run:
        with st.spinner(
            f"Agent is checking {client['client_name']}'s history, policy language, "
            "and risk patterns..."
        ):
            result = run_stress_test(scenario=scenario, client_id=CLIENT_ID, verbose=False)
        st.session_state["result"] = result
        st.session_state["result_type"] = "scenario"

# ── Coverage Audit ─────────────────────────────────────────────────────
else:
    st.subheader("Coverage Audit")
    st.write(
        f"Proactively review **{client['client_name']}'s** policy ({policy['policy_id']}) "
        "for gaps before binding or renewal — grounded in their claims history, "
        "E&O loss data, and carrier enforcement patterns."
    )

    run = st.button(f"Run Audit — {policy['policy_id']}", type="primary")

    if run:
        with st.spinner(f"Agent is auditing {policy['policy_id']}..."):
            result = run_coverage_audit(
                policy_id=policy["policy_id"],
                policy_type=client["primary_policy_type"],
                industry=client["industry"],
                client_id=CLIENT_ID,
                verbose=False,
            )
        st.session_state["result"] = result
        st.session_state["result_type"] = "audit"

# ── Results ──────────────────────────────────────────────────────────
if "result" in st.session_state:
    result = st.session_state["result"]
    st.divider()

    if result.get("error"):
        st.error(result["error"])

    elif st.session_state["result_type"] == "scenario":
        verdict = result.get("verdict", "UNKNOWN")
        confidence = result.get("confidence", 0)

        st.markdown(f"### {VERDICT_ICON.get(verdict, '⚪')} Verdict: **{verdict}**")
        st.progress(min(max(confidence, 0.0), 1.0), text=f"Confidence: {int(confidence * 100)}%")

        if result.get("scenario_summary"):
            st.write(result["scenario_summary"])

        findings = result.get("findings", [])
        if findings:
            st.markdown("#### Findings")
            for f in findings:
                sev = (f.get("severity") or "").lower()
                label = f"{SEVERITY_ICON.get(sev, '⚪')} [{f.get('severity', '').upper()}] {f.get('clause_reference', '')}"
                with st.expander(label):
                    if f.get("policy_language"):
                        st.markdown(f"**Policy language:** {f['policy_language']}")
                    st.markdown(f"**Implication:** {f.get('implication', '')}")

        if result.get("recommended_action"):
            st.markdown("#### Recommended Action")
            st.info(result["recommended_action"])

        if result.get("human_review_required"):
            st.markdown("#### ⚠️ Human Review Required")
            st.warning(result.get("human_review_reason", ""))

        if result.get("knowledge_gaps"):
            with st.expander("Knowledge gaps"):
                st.write(result["knowledge_gaps"])

        # ── Human-in-the-loop decision ──────────────────────────────
        st.divider()
        st.markdown("#### Broker Decision")
        c1, c2, c3 = st.columns(3)
        decision = None
        if c1.button("✅ Accept", use_container_width=True):
            decision = "accept"
        if c2.button("🚩 Flag for Review", use_container_width=True):
            decision = "flag_for_review"
        if c3.button("⚖️ Escalate to Attorney", use_container_width=True):
            decision = "escalate_attorney"

        if decision:
            st.session_state.setdefault("decision_log", []).append(
                {
                    "scenario": (result.get("scenario_summary") or "")[:80],
                    "verdict": verdict,
                    "decision": decision,
                }
            )
            st.success(f"Decision logged: **{decision}**")

    else:  # audit
        st.markdown("### Coverage Audit Report")
        st.write(result.get("summary", ""))

        risks = result.get("risks", [])
        for r in risks:
            sev = (r.get("severity") or "").lower()
            label = f"{SEVERITY_ICON.get(sev, '⚪')} #{r.get('rank')} [{r.get('severity')}] {r.get('risk_title')}"
            with st.expander(label):
                st.markdown(f"**E&O Frequency:** {r.get('eo_frequency', 'unknown')}")
                st.markdown(f"**What could go wrong:** {r.get('what_could_go_wrong', '')}")
                st.markdown(f"**Fix:** {r.get('fix', '')}")

        actions = result.get("immediate_actions", [])
        if actions:
            st.markdown("#### Immediate Actions")
            for a in actions:
                st.write(f"- {a}")

    with st.expander("Raw JSON response"):
        st.json(result)

# ── Decision log ─────────────────────────────────────────────────────
if st.session_state.get("decision_log"):
    st.divider()
    st.markdown("#### Decision Log (this session)")
    st.table(st.session_state["decision_log"])
