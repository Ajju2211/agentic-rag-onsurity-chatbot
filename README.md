# Agentic RAG Onsurity Chatbot

This repository contains the Agentic RAG Insurance Chatbot:
- Multi-channel ingestion (local folder + sitemap)
- Local sentence-transformers embeddings
- FAISS persistent indexes
- Background worker with Redis for sitemap diff & lazy indexing
- Agentic RAG: tool-calling agent selects retrievers/tools
- Simple human-readable LLM answers (no JSON exposed to users)

## Quickstart

1. Copy `.env.example` to `.env` and set values (OPTIONAL OpenAI key for final LLM).
2. Put insurance PDF/TXT files in `data/insurance_docs/`.
3. Start with Docker Compose:

   ```bash
   docker-compose up --build
   ```

4. Visit http://localhost:8501

## Project layout

See the repository files for details.
