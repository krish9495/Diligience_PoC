import asyncio
import os
import pathlib
from dotenv import load_dotenv
import cognee
from cognee import SearchType

# --- Imports from Cognee internals ---
from cognee.infrastructure.databases.graph import get_graph_engine
from cognee.infrastructure.databases.relational import get_migration_relational_engine
from cognee.tasks.ingestion import migrate_relational_database
from cognee.infrastructure.databases.relational import (
    create_db_and_tables as create_relational_db_and_tables,
)

# --- Configuration ---
load_dotenv()  # Read the .env file

if not os.getenv("LLM_API_KEY"):
    print("ERROR: LLM_API_KEY not found in your .env file.")
    exit()

# --- Paths ---
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "demo_files"

# --- PoC Query ---
poc_question = (
    "Following the Q2 Phishing Incident reported in Alpha Fund’s SOC 2 compliance summary, what remediation measures were taken, and who from the fund’s management team is responsible for data privacy oversight?"
)


async def run_cognee_poc():
    print("--- Starting Cognee PoC (Gemini | PDF + SQL) ---")

    # --- Cleanup ---
    print("1. Pruning existing data (if any)...")
    try:
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
        print("   Cleanup complete.")
    except Exception as e:
        print(f"   Cleanup failed or not needed: {e}")

    # --- Setup internal DBs ---
    print("2. Setting up Cognee's internal relational tables...")
    await create_relational_db_and_tables()
    print("   Relational DB setup complete.")

    # --- Step 1A: Add PDF data sources ---
    print("3. Adding File data sources (PDFs)...")
    pdf_files = [
        DATA_DIR / "demo_ddq.pdf",
        DATA_DIR / "demo_soc2.pdf",
    ]
    for file_path in pdf_files:
        if file_path.exists():
            await cognee.add(str(file_path))
            print(f"   Added file: {file_path.name}")
        else:
            print(f"   WARNING: File not found - {file_path}")

    # --- Step 1B: Migrate SQL Database ---
    print("4. Migrating SQL Database (alpha_fund_data.db)...")
    db_path = DATA_DIR / "alpha_fund_data.db"

    if not db_path.exists():
        print(f"   WARNING: Database file not found - {db_path}")
        return

    try:
        os.environ["MIGRATION_DB_PROVIDER"] = "sqlite"
        os.environ["MIGRATION_DB_PATH"] = str(DATA_DIR.resolve())
        os.environ["MIGRATION_DB_NAME"] = "alpha_fund_data.db"

        engine = get_migration_relational_engine()
        schema = await engine.extract_schema()
        graph = await get_graph_engine()

        await migrate_relational_database(graph, schema=schema)
        print("   SQL database migration complete.")
    except Exception as e:
        print(f"   ERROR during SQL migration: {e}")
        return

    # --- Step 2: Cognify PDFs ---
    print("5. Running Cognify to process PDFs...")
    try:
        await cognee.cognify()
        print("   Cognify complete.")
    except Exception as e:
        print(f"   ERROR during Cognify: {e}")
        return

    # --- Step 3: Search unified knowledge graph ---
    print(f"6. Searching the unified graph with question:\n   {poc_question}")
    try:
        results = await cognee.search(
            query_text=poc_question,
            query_type=SearchType.GRAPH_COMPLETION,
            top_k=50
        )

        print("\n--- Cognee Search Results ---")
        if results:
            for result in results:
                if isinstance(result, str):
                    print(result)
                elif hasattr(result, "text"):
                    print(result.text)
                else:
                    print(result)
        else:
            print("   No results found by Cognee.")
    except Exception as e:
        print(f"   ERROR during Search: {e}")

    print("\n--- Cognee PoC Finished ---")





# --- Run the PoC ---
if __name__ == "__main__":
    asyncio.run(run_cognee_poc())


