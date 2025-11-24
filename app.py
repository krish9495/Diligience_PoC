import asyncio
from typing import List

import streamlit as st

from rbac_poc import build_demo_state, run_query, ensure_beta_share, POC_PROMPT


SCENARIOS = {
    "Alpha – only Alpha DDQ": {
        "user_key": "alpha_analyst",
        "dataset_names": ["ALPHA_DDQ"],
        "requires_share": False,
        "description": "Alice can only see Alpha's DDQ context.",
    },
    "Beta – only Beta DDQ": {
        "user_key": "beta_analyst",
        "dataset_names": ["BETA_DDQ"],
        "requires_share": False,
        "description": "Bob operates fully inside Beta tenant.",
    },
    "Alpha – force Beta (unauthorized)": {
        "user_key": "alpha_analyst",
        "dataset_names": ["BETA_DDQ"],
        "requires_share": False,
        "description": "Alice tries to access Beta-only dataset – this should raise PermissionDenied.",
    },
    "Alpha – Alpha + Beta (after share)": {
        "user_key": "alpha_analyst",
        "dataset_names": ["ALPHA_DDQ", "BETA_DDQ"],
        "requires_share": True,
        "description": "Alice reads Alpha plus shared Beta DDQ after cross-tenant sharing is configured.",
    },
    "Alpha compliance – shared scope": {
        "user_key": "alpha_compliance",
        "dataset_names": ["ALPHA_DDQ", "BETA_DDQ"],
        "requires_share": True,
        "description": "Charlie (compliance) mirrors Alice's shared scope for governance reviews.",
    },
}


def init_backend():
    if "demo_state" not in st.session_state:
        st.info("Initializing Cognee backend and demo state...")
        state = asyncio.run(build_demo_state(run_playbook=False))
        st.session_state.demo_state = state
        st.session_state.beta_shared = False


def get_dataset_ids(dataset_names: List[str]):
    state = st.session_state.demo_state
    registry = state["dataset_registry"]
    return [registry[name] for name in dataset_names if name in registry]


def share_beta_if_needed():
    if not st.session_state.beta_shared:
        state = st.session_state.demo_state
        asyncio.run(
            ensure_beta_share(
                state["users"],
                state["org_state"],
                state["dataset_registry"],
            )
        )
        st.session_state.beta_shared = True


def main():
    st.set_page_config(page_title="Cognee RBAC Demo", layout="wide")
    st.title(" Cognee RBAC Demo – Alpha & Beta Due Diligence")

    init_backend()
    state = st.session_state.demo_state

    left, right = st.columns([2, 3])

    with left:
        st.subheader("Scenario")

        scenario_label = st.selectbox("Choose a scenario:", list(SCENARIOS.keys()))
        scenario = SCENARIOS[scenario_label]

        st.caption(scenario["description"])

        user_key = scenario["user_key"]
        user_obj = state["users"][user_key]
        st.markdown(f"**Running as:** `{user_obj.email}`")

        question = st.text_area("Question", value=POC_PROMPT, height=120)

        if scenario["requires_share"]:
            st.warning("This scenario requires Beta to share its DDQ with Alpha.")
            if st.button(" Ensure Beta DDQ is shared with Alpha role"):
                share_beta_if_needed()
                st.success("Beta DDQ is now shared with Alpha role.")

        if st.button(" Run query"):
            dataset_ids = get_dataset_ids(scenario["dataset_names"])
            payload = asyncio.run(
                run_query(
                    user=user_obj,
                    label=scenario_label,
                    question=question,
                    dataset_ids=dataset_ids,
                )
            )
            st.session_state.last_payload = payload

    with right:
        st.subheader("Result")

        if "last_payload" not in st.session_state:
            st.info("Select a scenario on the left and click **Run query**.")
        else:
            payload = st.session_state.last_payload
            st.markdown(f"**Label:** {payload['label']}")
            st.markdown(f"**User:** `{payload['user']}`")
            st.markdown("**Dataset IDs used:**")
            st.code("\n".join(payload["dataset_ids"]) or "(none)")

            if payload["error"]:
                st.error(f"Permission error: {payload['error']}")
            else:
                st.success("Query executed successfully.")
                
                # Extract answer text safely
            if payload["results"]:
            # Cognee wraps the actual answer inside ["search_result"][0]
                answer = payload["results"][0].get("search_result", ["No answer"])[0]
                st.markdown("###  Answer")
                st.write(answer)

                # Optionally show the datasets involved
                st.markdown("### Source Datasets")
                st.code("\n".join(payload["dataset_ids"]))

            else:
                st.info("No answer returned.")



if __name__ == "__main__":
    main()
