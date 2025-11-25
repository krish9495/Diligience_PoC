#  Cognee RBAC Demo – Multi-Tenant Due Diligence Access Control (Current Assignment)

This repository now includes a new *Role-Based Access Control (RBAC)* Proof-of-Concept built using *Cognee’s knowledge graph engine*.  
This section explains *the work done as part of the current assignment*, including the architecture, functionality, and implementation details.

---

#  Work Done as Part of This Assignment (LATEST)

This assignment implements a *multi-tenant RBAC system* with dataset-level permissions over due-diligence documents.  
It showcases secure access, isolation, and cross-tenant sharing using Cognee.

The following major components were implemented:

---

##  1. *User Bootstrapping*
Created 3 demo users programmatically:
- *Alice* – Alpha Analyst  
- *Charlie* – Alpha Compliance  
- *Bob* – Beta Analyst  

Each user is created idempotently (created once, reused if exists).

---

##  2. *Tenant & Role Setup*
Implemented automatic creation of:
- Tenant: *AlphaCapital* → Role: *AlphaDueDiligence*
- Tenant: *BetaPartners* → Role: *BetaDueDiligence*

Then:
- Users are added to respective tenants  
- Users are added to respective roles  

This establishes strict organizational boundaries.

---

##  3. *Dataset Ingestion Using Cognee*
Two DDQ PDFs are processed:
- alpha/alpha_ddq.pdf
- beta/BetaFund_DDQ.pdf

Steps:
1. PDFs are converted to text (via PyPDF2)  
2. Cognee ingests text into the system (cognee.add)  
3. Cognee builds knowledge graph embeddings (cognee.cognify)  
4. Dataset IDs are extracted and stored

Dataset ownership is automatically associated with the user performing ingestion.

---

##  4. *RBAC Permission Assignment*
Roles receive *read access* to their own datasets:

- AlphaDueDiligence → ALPHA_DDQ  
- BetaDueDiligence → BETA_DDQ  

Additionally:
- Dataset *owners* are explicitly given *share* permission  
  (so they can share with other roles)

---

##  5. *Cross-Tenant Sharing*
Beta’s dataset can be shared with Alpha:

- Bob (Beta owner) grants read access on BETA_DDQ
- Granted to *Alpha’s role*, not a specific user

This enables safe multi-organization collaboration.

---

##  6. *Query Execution with RBAC Enforcement*
Built a generic query runner:

- Accepts user, question, and optional dataset IDs  
- If dataset IDs aren't supplied → query uses all datasets user is allowed to read  
- Cognee enforces permissions  
- Unauthorized access returns a permission error  

---

##  7. **Streamlit Side Application (app.py)**
Created an interactive dashboard:

### Features:
- Choose scenario (Alpha only, Beta only, unauthorized, after sharing, etc.)
- Run query as any user
- Test cross-tenant sharing (Beta → Alpha)
- Show dataset IDs
- Show permission errors
- Show LLM answer

### Scenarios included:
1. Alpha → Only Alpha dataset  
2. Beta → Only Beta dataset  
3. Alpha → Forcing access to Beta dataset (*should fail*)  
4. Alpha → Access Alpha + Beta (after Beta shares)  
5. Alpha Compliance → Same shared access  

The UI provides complete demonstration of RBAC enforcement.

---

#  Project Structure (Updated)
```
Diligence_PoC/
├── rbac_poc.py             # NEW — Full RBAC backend implementation
├── app.py                  # NEW — Streamlit UI for RBAC demo
│
├── basic_rag_poc.py        # Previous assignment (Traditional RAG)
├── cognee_poc.py           # Previous assignment (Cognee RAG)
│
└── demo_files/
├── alpha/alpha_ddq.pdf
├── beta/BetaFund_DDQ.pdf




```

---

# 🚀 Running the RBAC Demo

### 1️ Install dependencies
```
pip install -r requirements.txt
```
### 2️ Add API key in .env
```
LLM_API_KEY=your_gemini_api_key
ENABLE_BACKEND_ACCESS_CONTROL="True"
```
### 3️ Run the Streamlit UI
```
streamlit run app.py
```

This repository now supports *two separate PoCs*:

### 🟦 Previous Work → RAG PoC  
### 🟩 Current Work → RBAC PoC (this assignment)




# Due Diligence RAG PoC (Previous POC)

This project demonstrates the improvement in LLM responses using Cognee's knowledge graph approach compared to traditional RAG (Retrieval-Augmented Generation) implementation for due diligence processes.

## Overview

The PoC implements two approaches to showcase the enhancement in LLM responses:

1. Traditional RAG implementation (basic_rag_poc.py)
2. Cognee's knowledge graph-based approach (cognee_poc.py)

## Features

### Data Processing Capabilities

- PDF document processing (DDQ and SOC2 reports)
- SQL database integration (fund manager information)
- Knowledge graph construction (Cognee implementation)
- Vector-based search (Traditional RAG)

### Components

- **Traditional RAG Implementation**:
  - PyPDF2 for PDF text extraction
  - Sentence-transformers for embeddings
  - FAISS for vector search
  - Simple text chunking
- **Cognee Implementation**:
  - Knowledge graph-based document understanding
  - SQL database migration to graph structure
  - Unified query processing
  - Enhanced context awareness

## Setup

### Prerequisites

- Python 3.8+
- Google Gemini API Key

### Environment Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/krish9495/Diligience_PoC.git
   ```

2. Create and configure .env file:

   ```
   LLM_API_KEY=your_gemini_api_key_here
   ```

3. Install required packages:
   ```bash
   pip install sentence-transformers faiss-cpu google-generativeai PyPDF2 pandas python-dotenv cognee
   ```

### Data Files

Place the following files in the `demo_files` directory:

- `demo_ddq.pdf`
- `demo_soc2.pdf`
- `alpha_fund_data.db`

## Running the Demo

1. Run the traditional RAG implementation:

   ```bash
   python basic_rag_poc.py
   ```

2. Run the Cognee-enhanced version:
   ```bash
   python cognee_poc.py
   ```

## Current Limitations

- Audio files (.mp3) processing not currently supported with Gemini
- Image files (.png) processing not currently supported with Gemini
- Limited to PDF and SQL data sources in current implementation

## Implementation Details

### Traditional RAG (basic_rag_poc.py)

- Uses simple text chunking with fixed size
- Vector-based similarity search
- Direct concatenation of relevant chunks for context

### Cognee Enhancement (cognee_poc.py)

- Knowledge graph construction from documents
- Relationship-aware data processing
- Graph-based context retrieval
- Unified querying across different data sources

## Sample Query

The PoC demonstrates improved responses for queries like:

```
"Following the Q2 Phishing Incident reported in Alpha Fund's SOC 2 compliance summary,
what remediation measures were taken, and who from the fund's management team is
responsible for data privacy oversight?"
```

## Project Structure

```
Diligence_Poc/
├── basic_rag_poc.py        # Traditional RAG implementation
├── cognee_poc.py           # Cognee-enhanced implementation
├── demo_files/             # Data directory
│   ├── demo_ddq.pdf
│   ├── demo_soc2.pdf
│   └── alpha_fund_data.db
└── .env                    # Environment configuration
```

## Future Enhancements

- Integration of audio file processing when supported
- Image analysis capabilities when available
- Extended document format support
- Enhanced error handling and logging
- Test suite implementation
