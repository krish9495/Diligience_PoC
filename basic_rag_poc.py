import os
import pathlib
from dotenv import load_dotenv
import sqlite3
import pandas as pd
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import google.generativeai as genai

# --- Configuration ---
load_dotenv() # Read the .env file

GEMINI_API_KEY = os.getenv("LLM_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR: LLM_API_KEY not found in your .env file.")
    exit()

genai.configure(api_key=GEMINI_API_KEY)

# 1. Define the base directory for the script
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()

# 2. Define the path to the data sub-folder
DATA_DIR = SCRIPT_DIR / "demo_files"

# 3. The PoC Question (SAME as before)
poc_question = "Following the Q2 Phishing Incident reported in Alpha Fund’s SOC 2 compliance summary, what remediation measures were taken, and who from the fund’s management team is responsible for data privacy oversight??"

# --- HELPER FUNCTIONS ---

def extract_text_from_pdfs(data_dir):
    """
    Finds all PDFs in the data directory and extracts their text.
    """
    print("   Extracting text from PDFs...")
    all_text = ""
    pdf_files = [data_dir / "demo_ddq.pdf", data_dir / "demo_soc2.pdf"]
    
    for pdf_path in pdf_files:
        if not pdf_path.exists():
            print(f"   WARNING: PDF file not found - {pdf_path}")
            continue
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                all_text += page.extract_text() or ""
            all_text += "\n\n" # Add a separator
        except Exception as e:
            print(f"   ERROR reading {pdf_path.name}: {e}")
    
    print("   PDF text extracted.")
    return all_text

def extract_text_from_sql(db_path, table_name):
    """
    Uses Pandas to read a SQL table and convert it to a simple text string.
    """
    print(f"   Extracting text from: {db_path.name}...")
    if not db_path.exists():
        print(f"   WARNING: Database file not found - {db_path}")
        return ""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        text = f"Database table {table_name}:\n{df.to_string()}"
        print("   SQL data extracted successfully.")
        return text
    except Exception as e:
        print(f"   ERROR extracting text from {db_path.name}: {e}")
        return ""

def simple_chunker(text, chunk_size=500, chunk_overlap=50):
    """
    Splits text into fixed-size chunks with overlap.
    """
    print("   Chunking text...")
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    print(f"   Created {len(chunks)} chunks.")
    return chunks

# --- Main Baseline RAG Function ---

def run_baseline_rag():
    print("--- Starting 'non-Cognee' (Baseline RAG) PoC ---")

    # --- 1. Extract All Text ---
    print("Step 1: Extracting text from all data sources...")
    pdf_text = extract_text_from_pdfs(DATA_DIR)
    sql_text = extract_text_from_sql(DATA_DIR / "alpha_fund_data.db", "fund_managers")
    
    corpus = pdf_text + "\n\n" + sql_text
    
    if not corpus.strip():
        print("ERROR: No text was extracted from data files. Exiting.")
        print("Please run 'setup_data.py' first.")
        return

    # --- 2. Chunk Text ---
    chunks = simple_chunker(corpus)
    
    # --- 3. Embed and Index (Create Vector Store) ---
    print("Step 2: Embedding chunks and creating FAISS index...")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2') # A good, fast embedding model
        embeddings = model.encode(chunks)
        
        # Create a FAISS index
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(np.array(embeddings).astype('float32'))
        print("   FAISS index created in memory.")
    except Exception as e:
        print(f"   ERROR during embedding or indexing: {e}")
        return

    # --- 4. Search (Retrieve) ---
    print(f"Step 3: Searching for relevant chunks for question: '{poc_question}'")
    query_vector = model.encode([poc_question])
    D, I = index.search(np.array(query_vector).astype('float32'), k=4) # Get top 4 chunks

    retrieved_chunks = [chunks[i] for i in I[0]]
    
    print("\n--- Raw Retrieved Chunks (The 'Before' Demo) ---")
    print("This is what the 'non-Cognee' system found (it's fragmented):")
    for i, chunk in enumerate(retrieved_chunks):
        print(f"\n[Chunk {i+1}]:\n{chunk.strip()}")
    
    # --- 5. Generate Response ---
    print("\n--- Baseline RAG Search Results ---")
    print("Step 4: Stuffing chunks into Gemini prompt...")
    
    context = "\n\n---\n\n".join(retrieved_chunks)
    prompt_template = f"""
    You are an analyst. Answer the user's question *only* using the context provided below.
    If the context does not contain the answer, say so.

    Context:
    {context}
    
    Question:
    {poc_question}
    
    Answer:
    """

    try:
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        response = gemini_model.generate_content(prompt_template)
        
        print(response.text)
    
    except Exception as e:
        print(f"   ERROR during Gemini generation: {e}")

    print("\n--- Baseline RAG PoC Finished ---")

# --- Run the PoC ---
if __name__ == "__main__":
    run_baseline_rag()