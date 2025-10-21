# KDD RAG (Scrape → JSON → Dense Retrieval → FastAPI)

## Overview
End-to-end RAG system:
1) Scrape KDD products (2 categories) + careers
2) Store as JSON
3) Dense retrieval (e5-base-v2) + optional re-rank
4) Generate answers with FLAN-T5
5) Serve via FastAPI (/ask)

## Stack
- Scraping: requests + BeautifulSoup
- Storage: JSON (`kdd_data.json`)
- Embeddings: intfloat/e5-base-v2 (ungated)
- Vector DB: FAISS (inner product, normalized)
- Generator: google/flan-t5-base (ungated)
- API: FastAPI (+ Swagger UI at /docs)

## Run
pip install -r requirements.txt
python scraper.py   # or run Cell 1
uvicorn app:app --reload

## Example
GET /ask?query=List the KDD product names we scraped.

## Notes
- If the KDD structure changes, adjust CSS selectors in scraper.
