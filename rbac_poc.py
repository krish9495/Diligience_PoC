"""
Cognee RBAC demo: Alpha & Beta due diligence datasets

- Two orgs (Alpha, Beta)
- Three users (Alpha analyst, Alpha compliance, Beta analyst)
- Two datasets (ALPHA_DDQ, BETA_DDQ)
- Dataset-level RBAC, tenant isolation, and cross-tenant sharing
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from dotenv import load_dotenv
from PyPDF2 import PdfReader

import cognee
from cognee import SearchType
from cognee.infrastructure.databases.exceptions import EntityAlreadyExistsError
from cognee.modules.engine.operations.setup import setup
from cognee.modules.users.exceptions import PermissionDeniedError
from cognee.modules.users.methods import create_user, get_user_by_email
from cognee.modules.users.permissions.methods import (
    authorized_give_permission_on_datasets,
    get_principal,
    give_permission_on_dataset,
)
from cognee.modules.users.roles.methods import add_user_to_role, create_role
from cognee.modules.users.tenants.methods import add_user_to_tenant, create_tenant
from fastapi_users.exceptions import UserAlreadyExists


POC_PROMPT = (
    "Following the Q2 Phishing Incident reported in Alpha Fund's SOC 2 compliance summary, "
    "what remediation measures were taken, and who from the fund's management team is "
    "responsible for data privacy oversight?"
)


# ---------------------------------------------------------------------------
# Environment & Initialization
# ---------------------------------------------------------------------------

def configure_environment() -> None:
    load_dotenv()
    if not os.getenv("LLM_API_KEY"):
        raise RuntimeError("LLM_API_KEY is required in the environment or .env file.")
    # Enable RBAC in Cognee
    os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "True")


async def initialize_cognee() -> None:
    print("Resetting Cognee storage and user tables...")
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    await setup()


# ---------------------------------------------------------------------------
# Users, Tenants, Roles
# ---------------------------------------------------------------------------

DEMO_USER_CONFIGS = {
    "alpha_analyst": {
        "email": "alice.analyst@alphafund.demo",
        "password": "alpha-pass",
        "display": "Alice (Alpha Analyst)",
    },
    "alpha_compliance": {
        "email": "charlie.compliance@alphafund.demo",
        "password": "alpha-pass",
        "display": "Charlie (Alpha Compliance)",
    },
    "beta_analyst": {
        "email": "bob.analyst@betapartners.demo",
        "password": "beta-pass",
        "display": "Bob (Beta Analyst)",
    },
}


async def create_or_get_user(email: str, password: str):
    try:
        return await create_user(
            email=email,
            password=password,
            is_verified=True,
            is_active=True,
        )
    except UserAlreadyExists:
        user = await get_user_by_email(email)
        if user is None:
            raise
        return user


async def bootstrap_users() -> Dict[str, object]:
    users: Dict[str, object] = {}
    for key, cfg in DEMO_USER_CONFIGS.items():
        user = await create_or_get_user(cfg["email"], cfg["password"])
        users[key] = user
        print(f"User ready: {cfg['display']} ({cfg['email']})")
    return users


async def setup_tenants_and_roles(users: Dict[str, object]):
    """
    Creates:
    - Tenant AlphaCapital with role AlphaDueDiligence
    - Tenant BetaPartners with role BetaDueDiligence
    and assigns users accordingly.
    """

    org_state: Dict[str, Dict[str, object]] = {}

    # Alpha org
    alpha_owner = users["alpha_analyst"]
    alpha_tenant_id = await create_tenant("AlphaCapital", alpha_owner.id)
    alpha_role_id = await create_role(role_name="AlphaDueDiligence", owner_id=alpha_owner.id)

    for member_key in ["alpha_analyst", "alpha_compliance"]:
        member = users[member_key]
        try:
            await add_user_to_tenant(user_id=member.id, tenant_id=alpha_tenant_id, owner_id=alpha_owner.id)
        except EntityAlreadyExistsError:
            pass
        try:
            await add_user_to_role(user_id=member.id, role_id=alpha_role_id, owner_id=alpha_owner.id)
        except EntityAlreadyExistsError:
            pass

    org_state["alpha"] = {"tenant_id": alpha_tenant_id, "role_id": alpha_role_id}

    # Beta org
    beta_owner = users["beta_analyst"]
    beta_tenant_id = await create_tenant("BetaPartners", beta_owner.id)
    beta_role_id = await create_role(role_name="BetaDueDiligence", owner_id=beta_owner.id)

    for member_key in ["beta_analyst"]:
        member = users[member_key]
        try:
            await add_user_to_tenant(user_id=member.id, tenant_id=beta_tenant_id, owner_id=beta_owner.id)
        except EntityAlreadyExistsError:
            pass
        try:
            await add_user_to_role(user_id=member.id, role_id=beta_role_id, owner_id=beta_owner.id)
        except EntityAlreadyExistsError:
            pass

    org_state["beta"] = {"tenant_id": beta_tenant_id, "role_id": beta_role_id}

    print("Tenants and roles configured.")
    return org_state


# ---------------------------------------------------------------------------
# Datasets & Ingestion
# ---------------------------------------------------------------------------

DATA_ROOT = Path(__file__).parent / "demo_files"
DATASET_FILES = {
    "ALPHA_DDQ": DATA_ROOT / "alpha" / "alpha_ddq.pdf",
    "BETA_DDQ": DATA_ROOT / "beta" / "BetaFund_DDQ.pdf",
}


def load_dataset_text(dataset_name: str) -> str:
    pdf_path = DATASET_FILES[dataset_name]
    if not pdf_path.exists():
        raise FileNotFoundError(f"Dataset source not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError(f"No text extracted from {pdf_path}")
    return text


def extract_first_dataset_id(cognify_result) -> Optional[UUID]:
    """
    Cognee cognify() can return either a dict keyed by dataset_id
    or a list of dicts containing dataset_id/datasetId.
    We just grab the first one.
    """
    if isinstance(cognify_result, dict) and cognify_result:
        raw = next(iter(cognify_result.keys()))
        return raw if isinstance(raw, UUID) else UUID(str(raw))

    if isinstance(cognify_result, list) and cognify_result:
        first = cognify_result[0]
        if isinstance(first, dict):
            raw = first.get("dataset_id") or first.get("datasetId")
            if raw:
                return raw if isinstance(raw, UUID) else UUID(str(raw))

    return None


async def ensure_share_permission_on_dataset(owner, dataset_id: UUID):
    principal = await get_principal(owner.id)
    await give_permission_on_dataset(principal, dataset_id, "share")


async def ingest_datasets(users: Dict[str, object]) -> Dict[str, UUID]:
    dataset_registry: Dict[str, UUID] = {}

    # Alpha DDQ
    alpha_owner = users["alpha_analyst"]
    alpha_body = load_dataset_text("ALPHA_DDQ")
    await cognee.add([alpha_body], dataset_name="ALPHA_DDQ", user=alpha_owner)
    alpha_cognify = await cognee.cognify(["ALPHA_DDQ"], user=alpha_owner)
    alpha_id = extract_first_dataset_id(alpha_cognify)
    if not alpha_id:
        raise RuntimeError("Failed to extract dataset id for ALPHA_DDQ")
    await ensure_share_permission_on_dataset(alpha_owner, alpha_id)
    dataset_registry["ALPHA_DDQ"] = alpha_id
    print(f"Ingested ALPHA_DDQ (id={alpha_id}).")

    # Beta DDQ
    beta_owner = users["beta_analyst"]
    beta_body = load_dataset_text("BETA_DDQ")
    await cognee.add([beta_body], dataset_name="BETA_DDQ", user=beta_owner)
    beta_cognify = await cognee.cognify(["BETA_DDQ"], user=beta_owner)
    beta_id = extract_first_dataset_id(beta_cognify)
    if not beta_id:
        raise RuntimeError("Failed to extract dataset id for BETA_DDQ")
    await ensure_share_permission_on_dataset(beta_owner, beta_id)
    dataset_registry["BETA_DDQ"] = beta_id
    print(f"Ingested BETA_DDQ (id={beta_id}).")

    return dataset_registry


async def assign_org_permissions(
    users: Dict[str, object],
    org_state: Dict[str, Dict[str, object]],
    dataset_registry: Dict[str, UUID],
):
    """
    Each org role gets read access to its own dataset:
    - AlphaDueDiligence -> ALPHA_DDQ
    - BetaDueDiligence -> BETA_DDQ
    """
    # Alpha
    alpha_owner = users["alpha_analyst"]
    alpha_role_id = org_state["alpha"]["role_id"]
    alpha_dataset_id = dataset_registry["ALPHA_DDQ"]
    try:
        await authorized_give_permission_on_datasets(
            principal_id=alpha_role_id,
            dataset_ids=[alpha_dataset_id],
            permission_name="read",
            owner_id=alpha_owner.id,
        )
    except EntityAlreadyExistsError:
        pass

    # Beta
    beta_owner = users["beta_analyst"]
    beta_role_id = org_state["beta"]["role_id"]
    beta_dataset_id = dataset_registry["BETA_DDQ"]
    try:
        await authorized_give_permission_on_datasets(
            principal_id=beta_role_id,
            dataset_ids=[beta_dataset_id],
            permission_name="read",
            owner_id=beta_owner.id,
        )
    except EntityAlreadyExistsError:
        pass

    print("Org-level read permissions assigned.")


async def ensure_beta_share(users, org_state, dataset_registry):
    """
    Beta owner grants Alpha role read access on BETA_DDQ.
    This simulates cross-tenant sharing.
    """
    beta_owner = users["beta_analyst"]
    alpha_role_id = org_state["alpha"]["role_id"]
    beta_dataset_id = dataset_registry["BETA_DDQ"]
    try:
        await authorized_give_permission_on_datasets(
            principal_id=alpha_role_id,
            dataset_ids=[beta_dataset_id],
            permission_name="read",
            owner_id=beta_owner.id,
        )
        print("Beta DDQ shared with Alpha role.")
    except EntityAlreadyExistsError:
        print("Sharing already configured; skipping.")


# ---------------------------------------------------------------------------
# Query Execution
# ---------------------------------------------------------------------------

async def run_query(
    user,
    label: str,
    question: str,
    dataset_ids: Optional[List[UUID]] = None,
):
    print(f"\n[{label}] -> querying as {user.email}")
    payload = {
        "label": label,
        "user": user.email,
        "question": question,
        "dataset_ids": [str(d) for d in (dataset_ids or [])],
        "results": [],
        "error": None,
    }
    try:
        search_kwargs = {
            "query_type": SearchType.GRAPH_COMPLETION,
            "query_text": question,
            "user": user,
        }
        if dataset_ids:
            search_kwargs["dataset_ids"] = dataset_ids

        results = await cognee.search(**search_kwargs)
        payload["results"] = results or []
        if not results:
            print("No context returned.")
        else:
            for idx, result in enumerate(results, start=1):
                print(f"Result {idx}: {result}")
        return payload
    except PermissionDeniedError as exc:
        print(f"Permission denied: {exc}")
        payload["error"] = str(exc)
        return payload


async def demonstrate_rbac(users, org_state, dataset_registry):
    alpha_scope = [dataset_registry["ALPHA_DDQ"]]
    beta_scope = [dataset_registry["BETA_DDQ"]]

    demo_runs = []

    # 1. Alpha isolated
    demo_runs.append(
        await run_query(users["alpha_analyst"], "Alpha analyst (isolated)", POC_PROMPT, alpha_scope)
    )

    # 2. Beta isolated
    demo_runs.append(
        await run_query(users["beta_analyst"], "Beta analyst (isolated)", POC_PROMPT, beta_scope)
    )

    # 3. Alpha forcing Beta (should fail)
    print("\nAttempting to force Beta dataset as Alpha analyst (should fail)...")
    demo_runs.append(
        await run_query(
            users["alpha_analyst"],
            "Alpha analyst unauthorized",
            POC_PROMPT,
            beta_scope,
        )
    )

    # 4. Grant Beta DDQ to Alpha role
    print("\nGranting Beta DDQ read access to Alpha role (cross-org sharing)...")
    await ensure_beta_share(users, org_state, dataset_registry)

    merged_scope = alpha_scope + beta_scope

    # 5. Alpha with shared Beta graph
    demo_runs.append(
        await run_query(
            users["alpha_analyst"],
            "Alpha analyst with shared Beta graph",
            POC_PROMPT,
            merged_scope,
        )
    )

    # 6. Alpha compliance teammate querying shared scope
    demo_runs.append(
        await run_query(
            users["alpha_compliance"],
            "Alpha compliance",
            POC_PROMPT,
            merged_scope,
        )
    )

    return demo_runs


# ---------------------------------------------------------------------------
# State Builder (used by both CLI & Streamlit)
# ---------------------------------------------------------------------------

async def build_demo_state(run_playbook: bool = False):
    configure_environment()
    await initialize_cognee()
    users = await bootstrap_users()
    org_state = await setup_tenants_and_roles(users)
    dataset_registry = await ingest_datasets(users)
    await assign_org_permissions(users, org_state, dataset_registry)

    state = {
        "users": users,
        "org_state": org_state,
        "dataset_registry": dataset_registry,
    }
    if run_playbook:
        state["query_runs"] = await demonstrate_rbac(users, org_state, dataset_registry)
    return state


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

async def main():
    await build_demo_state(run_playbook=True)


if __name__ == "__main__":
    asyncio.run(main())
