
import os, json, pandas as pd, streamlit as st
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from agents.intake_agent import build_intake_agent
from agents.triage_agent import build_triage_agent
from agents.sql_agent import build_sql_agent
from tools.sql_tool import run_parameterized
from tools.retrieval_tool import retrieve_similar_notes
import asyncio,json,re
load_dotenv()


def extract_json_content(res):
    """
    Extract clean JSON string from Semantic Kernel FunctionResult or
    raw OpenAI ChatCompletion.
    """
    text = None

    # Case 1: Semantic Kernel FunctionResult
    if hasattr(res, "get_inner_content"):
        raw = res.get_inner_content()
        # If it's a ChatMessageContent, grab .content
        if hasattr(raw, "content"):
            text = raw.content
            print(text)
        else:
            text = str(raw)

    # Case 2: Raw ChatCompletion
    elif hasattr(res, "choices"):
        text = res.choices[0].message.content
        print(text)

    # Fallback: just stringify
    else:
        text = str(res)

    return _clean_json_str(text)


def _clean_json_str(text: str) -> str:
    """Remove ```json fences if present."""
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r"^```(?:json)?\n?", "", text).strip()
    text = text.strip("`").strip()
    return text
def extract_json(raw_text: str):
    import re, json
    # remove triple backticks and optional `json`
    clean = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE)
    return json.loads(clean)
def build_kernel():
    k = Kernel()
    k.add_service(
        AzureChatCompletion(
            service_id="azure",
            deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION","2024-08-01-preview"),
        )
    )
    return k

st.set_page_config(page_title="SK + DiskANN Claims", page_icon="🧩", layout="wide")
st.title("🧩 SK + DiskANN Insurance Claims Demo")

tab1, tab2, tab3 = st.tabs(["📨 Triage a Claim", "🔍 Semantic Retrieval", "🔎 Ask the Database"])

k = build_kernel()
intake = build_intake_agent(k)
triage = build_triage_agent(k)
sql_agent = build_sql_agent(k)

with tab1:
    st.subheader("Paste a claim note")
    note = st.text_area("Claim description", height=140,
                        placeholder="Rear-end collision at low speed on I-35 in Austin...")
    colA, colB = st.columns(2)
    with colA:
        policy_id = st.number_input("Policy ID", min_value=1, value=1)
    with colB:
        amount_claimed = st.number_input("Amount Claimed (USD)", min_value=0.0, value=1500.0, step=100.0)

    if st.button("Run Triage", type="primary"):
        if not note.strip():
            st.warning("Please enter a note.")
        else:
            intake_res = asyncio.run(k.invoke(intake, input=note))
            intake_json_str = extract_json_content(intake_res)
            print(extract_json(intake_res.get_inner_content().choices[0].message.content))
            try:
                intake_data = extract_json(intake_res.get_inner_content().choices[0].message.content)
            except Exception:
                st.error("Could not parse IntakeAgent output")
                st.code(intake_json_str)
                
                st.stop()

            ctx_rows = run_parameterized(
                "SELECT count(*) AS prior_count, coalesce(sum(amount_claimed),0) AS prior_total "
                "FROM claims WHERE policy_id = %s",
                (policy_id,)
            )
            ctx = ctx_rows[0] if ctx_rows else {"prior_count":0,"prior_total":0}

            sim = retrieve_similar_notes(note, k=3)
            sim_lines = "\n".join([f"Note {r['note_id']} (claim {r['claim_id']}): {r['note_text']}" for r in sim])

            triage_res = asyncio.run(k.invoke(
            triage,
            summary=intake_data.get("concise_summary", ""),
            context=(
                f"policy_id={policy_id}, prior_claims={ctx['prior_count']}, "
                f"prior_total={ctx['prior_total']}\nSimilar past notes:\n{sim_lines}"
               )
            ))
            triage_json = extract_json(triage_res.get_inner_content().choices[0].message.content)
            print(triage_json)
            try:
                tri = triage_json
            except Exception:
                st.error("Could not parse TriageAgent output.")
                st.code(triage_json)
                st.stop()

            new_claim = run_parameterized(
                "INSERT INTO claims (policy_id, date_of_loss, description, amount_claimed, status) "
                "VALUES (%s, CURRENT_DATE, %s, %s, 'OPEN') RETURNING claim_id;",
                (policy_id, note, amount_claimed)
            )
            claim_id = new_claim[0]["claim_id"]

            run_parameterized(
                "INSERT INTO triage_decisions (claim_id, severity, fraud_risk, route_to, rationale) "
                "VALUES (%s, %s, %s, %s, %s);",
                (claim_id, tri["severity"], float(tri["fraud_risk"]), tri["route_to"], tri["rationale"])
            )

            st.success(f"Triage complete for claim #{claim_id}")
            st.json({"intake": intake_data, "triage": tri})

            recent = run_parameterized(
                "SELECT t.decision_id, t.created_at, t.severity, t.fraud_risk, t.route_to, c.description "
                "FROM triage_decisions t "
                "JOIN claims c ON c.claim_id = t.claim_id "
                "ORDER BY t.decision_id DESC LIMIT 10"
            )
            if recent:
                st.subheader("Recent Triage Decisions")
                st.dataframe(pd.DataFrame(recent))

with tab2:
    st.subheader("Find similar past cases (DiskANN)")
    desc = st.text_area("Enter a short description", height=120)
    kval = st.slider("Top K", 1, 10, 5)
    if st.button("Find similar", key="sim"):
        if not desc.strip():
            st.warning("Please enter a description.")
        else:
            results = retrieve_similar_notes(desc, k=kval)
            st.dataframe(pd.DataFrame(results))

with tab3:
    st.subheader("Ask in natural language (NL→SQL)")
    q = st.text_input("e.g., Top 5 HIGH severity claims this quarter with amounts")
    if st.button("Ask", key="ask"):
        if not q.strip():
            st.warning("Enter a question.")
        else:
            sql_res = asyncio.run(k.invoke(sql_agent, input=q))
            out = extract_json_content(sql_res)
            print(sql_res)
            print(extract_json(sql_res.get_inner_content().choices[0].message.content)["sql"])
            try:
                parsed = extract_json(sql_res.get_inner_content().choices[0].message.content)
            except Exception:
                st.error("Could not parse SqlAgent output.")
                st.code(out)
                st.stop()
            st.caption("Proposed SQL")
            st.code(parsed.get("sql",""))
            try:
                rows = run_parameterized(parsed["sql"])
                st.dataframe(pd.DataFrame(rows))
            except Exception as e:
                st.error(f"SQL error: {e}")
            st.caption("Explanation")
            st.write(parsed.get("explanation",""))
