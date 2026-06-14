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
import tempfile

import streamlit as st

# On Streamlit Community Cloud, secrets are configured via the dashboard
# (st.secrets) rather than a .env file. Mirror them into os.environ so the
# existing dotenv-based clients (agents/stress_tester.py, services/llm_client.py)
# work unchanged both locally and when deployed.
try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:
    # No secrets.toml — running locally with a .env file instead, which
    # the dotenv-based clients load on their own.
    pass

from agents.stress_tester import (
    run_stress_test,
    run_coverage_audit,
    retrieve_client_history,
    list_client_histories,
    list_indexed_policies,
    get_policy_chunks,
    retrieve_risk_patterns,
    retrieve_eo_claims,
    retrieve_industry_losses,
    retrieve_carrier_decisions,
)
from run_test import SCENARIOS, POLICY_ID_TO_TYPE, POLICY_ID_TO_INDUSTRY, POLICY_TYPES
from indexing.index_policy import index_policy

st.set_page_config(page_title="B&B Coverage Advisor", page_icon="🛡️", layout="centered")

# Lightweight shared-password gate — this app is public and makes live calls
# to paid Claude / Azure services, so we don't want it wide open to anyone
# who stumbles on the URL. Set APP_PASSWORD in the Streamlit Cloud secrets
# to override the default.
try:
    _app_password = st.secrets.get("APP_PASSWORD", "sunflower")
except Exception:
    _app_password = "sunflower"

if not st.session_state.get("authenticated"):
    st.title("🛡️ B&B Coverage Advisor")
    with st.form("login_form"):
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter", type="primary")
    if submitted:
        if pw == _app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

st.title("🛡️ B&B Coverage Advisor")
st.caption(
    "AI-powered coverage stress testing — every finding is grounded in retrieved policy "
    "language, this client's actual history, and institutional risk patterns."
)

VERDICT_ICON = {"COVERED": "🟢", "CONDITIONAL": "🟡", "LIKELY_DENIED": "🔴"}
SEVERITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢",
                 "critical": "🔴", "CRITICAL": "🔴", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

INDUSTRIES = ["any", "trucking", "construction", "professional_services", "manufacturing",
              "retail", "agriculture", "real_estate", "hospitality", "healthcare", "warehousing"]

UPLOAD_LABEL = "➕ Upload new policy..."


@st.cache_data(ttl=300)
def get_clients():
    return list_client_histories()["clients"]


@st.cache_data(ttl=300)
def get_policies():
    return list_indexed_policies()["policies"]


@st.cache_data(ttl=300)
def get_client_record(client_id):
    return retrieve_client_history(client_id)["client"]


def policy_and_client_picker(key_prefix: str):
    """Shared client + policy picker used by both Coverage Risk Audit and
    Scenario Stress Test. The policy list is pre-filtered to default to the
    selected client's policy, but any indexed policy can be chosen, and a
    brand new policy can be uploaded + indexed inline.

    Returns (client_record_or_None, policy_id_or_None).
    """
    clients = get_clients()
    policies = get_policies()

    client_choices = ["— No client (generic policy) —"] + [
        f"{c['client_name']} — {c['policy_id']} ({c['client_id']})" for c in clients
    ]
    client_choice = st.selectbox("Client", client_choices, key=f"{key_prefix}_client")

    client = None
    if client_choice != client_choices[0]:
        client = get_client_record(clients[client_choices.index(client_choice) - 1]["client_id"])

    policy_labels = {f"{p['policy_id']} ({p['form_number']})": p["policy_id"] for p in policies}
    policy_label_by_id = {v: k for k, v in policy_labels.items()}

    # When the client changes, snap the policy picker to that client's policy
    # by writing directly into session_state before the widget is created —
    # this is the reliable way to programmatically change a selectbox's value.
    prev_client_key = f"{key_prefix}_prev_client"
    if st.session_state.get(prev_client_key) != client_choice:
        st.session_state[prev_client_key] = client_choice
        if client:
            subj_id = client["policy_history"][0]["policy_id"]
            if subj_id in policy_label_by_id:
                st.session_state[f"{key_prefix}_policy"] = policy_label_by_id[subj_id]

    policy_choices = list(policy_labels.keys()) + [UPLOAD_LABEL]
    policy_choice = st.selectbox("Policy", policy_choices, key=f"{key_prefix}_policy")

    if policy_choice == UPLOAD_LABEL:
        st.markdown("##### Upload a new policy")
        st.caption(
            "Runs the same Document Intelligence + embedding pipeline used for the "
            "existing policies. Once indexed, it's immediately available here."
        )
        uploaded = st.file_uploader("Policy PDF", type=["pdf"], key=f"{key_prefix}_upload")
        c1, c2 = st.columns(2)
        new_policy_id = c1.text_input("Policy ID", placeholder="e.g. CA0001-2019", key=f"{key_prefix}_new_id")
        new_form_number = c2.text_input("Form number", placeholder="e.g. CA-00-01-09-19", key=f"{key_prefix}_new_form")

        if st.button("Index Policy", key=f"{key_prefix}_index_btn", disabled=not uploaded):
            if not new_policy_id:
                st.error("Policy ID is required.")
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = tmp.name
                try:
                    with st.spinner(
                        "Extracting text with Document Intelligence, embedding, and uploading "
                        "to AI Search — this can take a minute..."
                    ):
                        chunk_count = index_policy(
                            pdf_path=tmp_path,
                            policy_id=new_policy_id,
                            form_number=new_form_number or "UNKNOWN",
                        )
                    get_policies.clear()
                    st.session_state[f"{key_prefix}_policy"] = (
                        f"{new_policy_id} ({new_form_number or 'UNKNOWN'})"
                    )
                    st.success(f"Indexed {new_policy_id} — {chunk_count} chunks added to AI Search.")
                    st.rerun()
                finally:
                    os.unlink(tmp_path)
        return client, None

    return client, policy_labels[policy_choice]


def render_audit_result(result: dict):
    st.divider()
    if result.get("error"):
        st.error(result["error"])
        return

    st.markdown("### Coverage Audit Report")
    st.write(result.get("summary", ""))

    for r in result.get("risks", []):
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


def render_scenario_result(result: dict):
    st.divider()
    if result.get("error"):
        st.error(result["error"])
        return

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
    if c1.button("✅ Accept", use_container_width=True, key="scenario_accept"):
        decision = "accept"
    if c2.button("🚩 Flag for Review", use_container_width=True, key="scenario_flag"):
        decision = "flag_for_review"
    if c3.button("⚖️ Escalate to Attorney", use_container_width=True, key="scenario_escalate"):
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

    with st.expander("Raw JSON response"):
        st.json(result)

    if st.session_state.get("decision_log"):
        st.divider()
        st.markdown("#### Decision Log (this session)")
        st.table(st.session_state["decision_log"])


top_tabs = st.tabs(["Stress Test Policy", "Data Explorer"])

# ── Stress Test Policy ──────────────────────────────────────────────────
with top_tabs[0]:
    sub_tabs = st.tabs(["Coverage Risk Audit", "Scenario Stress Test"])

    # ── Coverage Risk Audit ──
    with sub_tabs[0]:
        st.subheader("Coverage Risk Audit")
        st.write(
            "Proactively review a policy for gaps before binding or renewal — grounded "
            "in claims history, E&O loss data, and carrier enforcement patterns."
        )

        client, policy_id = policy_and_client_picker("audit")

        if policy_id:
            default_type = (
                client["primary_policy_type"] if client
                else POLICY_ID_TO_TYPE.get(policy_id, "general_liability")
            )
            default_industry = (
                client["industry"] if client
                else POLICY_ID_TO_INDUSTRY.get(policy_id, "any")
            )

            # When the selected policy changes, snap policy type / industry to
            # that policy's (or client's) defaults.
            if st.session_state.get("audit_prev_policy") != policy_id:
                st.session_state["audit_prev_policy"] = policy_id
                st.session_state["audit_policy_type"] = (
                    default_type if default_type in POLICY_TYPES else "general_liability"
                )
                st.session_state["audit_industry"] = default_industry

            if client:
                st.caption(
                    f"📁 Linked client: **{client['client_name']}** "
                    f"({client['client_id']}) — audit will also use their claims/risk history"
                )
            else:
                st.caption(
                    "No client selected — audit will rely on policy language, playbook, "
                    "and market intelligence only."
                )

            c1, c2 = st.columns(2)
            policy_type = c1.selectbox("Policy type", POLICY_TYPES, key="audit_policy_type")
            industry = c2.text_input("Industry", key="audit_industry")

            if st.button(f"Run Audit — {policy_id}", type="primary", key="audit_run"):
                with st.spinner(f"Agent is auditing {policy_id}..."):
                    result = run_coverage_audit(
                        policy_id=policy_id,
                        policy_type=policy_type,
                        industry=industry,
                        client_id=client["client_id"] if client else None,
                        verbose=False,
                    )
                st.session_state["audit_result"] = result

        if "audit_result" in st.session_state:
            render_audit_result(st.session_state["audit_result"])

    # ── Scenario Stress Test ──
    with sub_tabs[1]:
        st.subheader("Scenario Stress Test")
        st.write(
            "Describe a claim scenario — the agent checks it against the selected "
            "client's actual policy and claims history, and surfaces coverage gaps, "
            "exclusions, and ambiguities."
        )

        client, policy_id = policy_and_client_picker("scenario")

        if client is None:
            st.warning(
                "Select a client to run a scenario stress test — the agent evaluates "
                "scenarios against a specific client's policy and claims history."
            )
        else:
            policy = client["policy_history"][0]
            subj_policy_id = policy["policy_id"]

            if policy_id and policy_id != subj_policy_id:
                st.caption(
                    f"Note: the scenario is evaluated against **{client['client_name']}'s** "
                    f"policy on file ({subj_policy_id}), regardless of the policy selected above."
                )

            with st.container(border=True):
                st.markdown(f"### 📁 {client['client_name']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Policy", policy["policy_id"])
                c2.metric("Carrier", policy["carrier"])
                c3.metric("Industry", client["industry"].replace("_", " ").title())
                c4.metric("Annual Premium", f"${client['annual_premium']:,}")

            client_id = client["client_id"]
            if client_id == "DEMO-CLIENT-001":
                preset_options = ["Custom"] + [f"{k}. {v['label']}" for k, v in SCENARIOS.items()]
            else:
                preset_options = ["Custom"]
                st.caption(
                    "The preset demo scenarios were written for Meridian Freight (DEMO-CLIENT-001). "
                    "For this client, describe a custom scenario relevant to their policy/industry."
                )

            preset = st.selectbox("Demo scenario", preset_options, key="scenario_preset")

            if preset == "Custom":
                scenario = st.text_area(
                    "Scenario description", height=120, key="scenario_text",
                    placeholder="e.g. A subcontractor's crew damages a client's existing structure "
                                "while working on an addition — does coverage respond?",
                )
            else:
                key = preset.split(".")[0]
                s = SCENARIOS[key]
                scenario = st.text_area("Scenario description", value=s["scenario"], height=120, key="scenario_text_preset")

            if st.button("Run Stress Test", type="primary", key="scenario_run"):
                with st.spinner(
                    f"Agent is checking {client['client_name']}'s history, policy language, "
                    "and risk patterns..."
                ):
                    result = run_stress_test(scenario=scenario, client_id=client_id, verbose=False)
                st.session_state["scenario_result"] = result

        if "scenario_result" in st.session_state:
            render_scenario_result(st.session_state["scenario_result"])

# ── Data Explorer ────────────────────────────────────────────────────
with top_tabs[1]:
    st.subheader("Data Explorer — what the agent actually sees")
    st.write(
        "Raw records from the knowledge layer the agent grounds its reasoning in. "
        "Nothing here is pre-aggregated — the agent computes any rates or patterns "
        "itself, live, from records like these."
    )

    tabs = st.tabs([
        "Client Profile", "Policy Clauses", "Risk Patterns",
        "E&O Claims", "Industry Losses", "Carrier Decisions",
    ])

    # ── Client Profile ──
    with tabs[0]:
        clients = get_clients()
        options = {f"{c['client_name']} ({c['client_id']})": c["client_id"] for c in clients}
        label = st.selectbox("Client", list(options.keys()), key="explorer_client")
        client = get_client_record(options[label])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Industry", client["industry"].replace("_", " ").title())
        c2.metric("Years as client", client["years_as_client"])
        c3.metric("Annual Premium", f"${client['annual_premium']:,}")
        c4.metric("Policy Type", client["primary_policy_type"].replace("_", " ").title())

        st.markdown("#### Policy History")
        st.dataframe(client["policy_history"], use_container_width=True)

        st.markdown("#### Claims History")
        st.dataframe(client["claims_history"], use_container_width=True)

        st.markdown("#### Risk Flags")
        st.dataframe(client["risk_flags"], use_container_width=True)

    # ── Policy Clauses ──
    with tabs[1]:
        policies = get_policies()
        options = {f"{p['policy_id']} ({p['form_number']})": p["policy_id"] for p in policies}
        label = st.selectbox("Policy", list(options.keys()), key="explorer_policy")
        policy_id = options[label]

        chunks_result = get_policy_chunks(policy_id)
        st.caption(f"{chunks_result['count']} indexed chunks for {policy_id} — every chunk "
                   "the agent's retrieve_policy_clauses tool can search over.")

        section_types = sorted(set(c["section_type"] for c in chunks_result["chunks"]))
        section_filter = st.multiselect(
            "Filter by section type", section_types, default=section_types
        )

        for c in chunks_result["chunks"]:
            if c["section_type"] not in section_filter:
                continue
            with st.expander(f"p.{c.get('page_number', '?')} — {c['section_type']}"):
                st.write(c["content"])

    # ── Risk Patterns ──
    with tabs[2]:
        st.caption("Pre-encoded institutional risk patterns — the agent's lens for what "
                   "to look for before reading policy language.")
        c1, c2 = st.columns(2)
        scenario_type = c1.selectbox("Scenario type", POLICY_TYPES, key="explorer_scenario_type")
        industry = c2.selectbox("Industry", INDUSTRIES, key="explorer_rp_industry")

        result = retrieve_risk_patterns(
            scenario_type=scenario_type,
            industry=None if industry == "any" else industry,
        )
        if result.get("found"):
            st.caption(f"{result['count']} pattern(s)")
            st.dataframe(result["patterns"], use_container_width=True)
        else:
            st.info(result.get("message"))

    # ── E&O Claims ──
    with tabs[3]:
        st.caption("Raw sample from the 10,000-record E&O claims dataset. The outcome "
                   "breakdown below is raw counts — the agent computes the denial rate itself.")
        c1, c2, c3 = st.columns(3)
        policy_type = c1.selectbox("Policy type", POLICY_TYPES, key="explorer_eo_type")
        industry = c2.selectbox("Industry", INDUSTRIES, key="explorer_eo_industry")
        coverage_area = c3.text_input("Coverage area (optional)", value="", key="explorer_eo_area")

        result = retrieve_eo_claims(
            policy_type=policy_type,
            industry=None if industry == "any" else industry,
            coverage_area=coverage_area or None,
            top_k=25,
        )
        if result.get("found"):
            st.metric("Total matching claims", result["total_matching_claims"])
            st.markdown("**Outcome breakdown (raw counts — agent computes the rates)**")
            st.dataframe(result["outcome_breakdown"], use_container_width=True)
            st.markdown("**Sample claim records**")
            st.dataframe(result["sample_claims"], use_container_width=True)
        else:
            st.info(result.get("message"))

    # ── Industry Losses ──
    with tabs[4]:
        st.caption("Raw sample from the 10,000-record commercial loss event dataset.")
        c1, c2, c3 = st.columns(3)
        industry = c1.selectbox("Industry", [i for i in INDUSTRIES if i != "any"],
                                 key="explorer_il_industry")
        policy_type = c2.selectbox("Policy type", ["any"] + POLICY_TYPES, key="explorer_il_type")
        loss_type = c3.text_input("Loss type (optional)", value="", key="explorer_il_loss")

        result = retrieve_industry_losses(
            industry=industry,
            policy_type=None if policy_type == "any" else policy_type,
            loss_type=loss_type or None,
            top_k=25,
        )
        if result.get("found"):
            st.metric("Total matching losses", result["total_matching_losses"])
            st.markdown("**Coverage response breakdown (raw counts)**")
            st.dataframe(result["coverage_response_breakdown"], use_container_width=True)
            st.markdown("**Denial reason breakdown (raw counts)**")
            st.dataframe(result["denial_reason_breakdown"], use_container_width=True)
            st.markdown("**Sample loss records**")
            st.dataframe(result["sample_losses"], use_container_width=True)
        else:
            st.info(result.get("message"))

    # ── Carrier Decisions ──
    with tabs[5]:
        st.caption("Raw sample from the 10,000-record carrier coverage decision dataset.")
        c1, c2, c3 = st.columns(3)
        policy_type = c1.selectbox("Policy type", POLICY_TYPES, key="explorer_cd_type")
        coverage_area = c2.text_input("Coverage area (optional)", value="", key="explorer_cd_area")
        carrier_type = c3.text_input("Carrier type (optional)", value="", key="explorer_cd_carrier")

        result = retrieve_carrier_decisions(
            policy_type=policy_type,
            coverage_area=coverage_area or None,
            carrier_type=carrier_type or None,
            top_k=25,
        )
        if result.get("found"):
            st.metric("Total matching decisions", result["total_matching_decisions"])
            st.markdown("**Decision breakdown (raw counts)**")
            st.dataframe(result["decision_breakdown"], use_container_width=True)
            st.markdown("**Sample decision records**")
            st.dataframe(result["sample_decisions"], use_container_width=True)
        else:
            st.info(result.get("message"))
