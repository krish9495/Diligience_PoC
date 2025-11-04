# Due Diligence RAG PoC

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
