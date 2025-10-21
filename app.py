
# app.py
import json, numpy as np
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer, CrossEncoder
import faiss
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# Load data
with open("kdd_data.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

docs = []
for p in raw.get("products", []):
    docs.append({"id": f"prod::{p.get('name','').strip()}", "type": "product", "payload": p, "text": json.dumps(p, ensure_ascii=False)})
for j in raw.get("careers", []):
    docs.append({"id": f"job::{j.get('title','').strip()}", "type": "career", "payload": j, "text": json.dumps(j, ensure_ascii=False)})

# Embeddings + index
embedder = SentenceTransformer("intfloat/e5-base-v2")
def embed_texts(texts): return embedder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
doc_vecs = embed_texts([f"passage: {d['text']}" for d in docs])
index = faiss.IndexFlatIP(doc_vecs.shape[1])
index.add(doc_vecs)

# Re-ranker (optional)
try:
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    USE_RERANK = True
except Exception:
    reranker = None
    USE_RERANK = False

# Generator
tok = AutoTokenizer.from_pretrained("google/flan-t5-base")
gen = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")

SYSTEM_INSTR = ("You are a helpful assistant that answers ONLY using the provided context. "
                "If the answer is not present, say: 'I don't know based on the scraped data.'")

def retrieve(query: str, k=10, k_final=5):
    qv = embed_texts([f"query: {query}"])
    D, I = index.search(qv, k)
    cands = [docs[i] for i in I[0]]
    if USE_RERANK and reranker is not None:
        pairs = [(query, c["text"]) for c in cands]
        scores = reranker.predict(pairs)
        order = np.argsort(scores)[::-1][:k_final]
        return [cands[i] for i in order]
    return cands[:k_final]

def generate_answer(query: str, contexts, max_new_tokens=256):
    context_block = "\n\n".join([c["text"] for c in contexts]) if contexts else "No context."
    prompt = f"{SYSTEM_INSTR}\n\nContext:\n{context_block}\n\nQuestion: {query}\nAnswer:"
    inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=2048)
    with torch.no_grad():
        out = gen.generate(**inputs, max_new_tokens=max_new_tokens)
    return tok.decode(out[0], skip_special_tokens=True)

class AskResponse(BaseModel):
    answer: str
    context_ids: List[str]
    context_snippets: List[str]

app = FastAPI(title="KDD RAG API", version="1.0")

@app.get("/health")
def health():
    return {"status": "ok", "docs": len(docs)}

@app.get("/ask", response_model=AskResponse)
def ask(query: str = Query(..., description="NL question about KDD products or careers")):
    ctx = retrieve(query)
    answer = generate_answer(query, ctx)
    return AskResponse(
        answer=answer,
        context_ids=[c["id"] for c in ctx],
        context_snippets=[c["text"][:240] for c in ctx]
    )
