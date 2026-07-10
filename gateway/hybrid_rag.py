"""
Hybrid RAG: Wiki Graph (keyword) + ChromaDB (vector).

Usage:
    from hybrid_rag import hybrid_query, wiki_ingest, wiki_status, chroma_status
"""

import os
from wiki_graph import get_wiki_graph, reload_wiki_graph, WikiGraph

# ── Config ────────────────────────────────────────────────────────────────
CHROMA_URL = os.environ.get("CHROMA_URL", "http://chromadb:8000")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "textbook")
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Lazy-loaded singletons
_chroma_client = None
_embed_model = None
_collection = None


def _get_chroma():
    """Lazy-init ChromaDB client. Must match server version."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        # ChromaDB 0.6.x settings
        _chroma_client = chromadb.HttpClient(
            host=CHROMA_URL.split("://")[1].split(":")[0],
            port=int(CHROMA_URL.split(":")[-1]),
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=False,
            ),
        )
    return _chroma_client


def _get_collection():
    """Lazy-init textbook collection."""
    global _collection
    if _collection is None:
        chroma = _get_chroma()
        try:
            _collection = chroma.get_collection(CHROMA_COLLECTION)
        except Exception:
            return None
    return _collection


def _get_embed_model():
    """Lazy-init sentence-transformers model (CPU, ~118MB, 50ms/inference)."""
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


# ── Ingestion ─────────────────────────────────────────────────────────────

def wiki_ingest() -> dict:
    """Re-index wiki — reloads graph from disk."""
    graph = reload_wiki_graph()
    pages = graph.list_all()
    return {
        "ingested": len(pages),
        "pages": [f"wiki/{p.path}" for p in pages],
        "message": f"wiki graph reloaded: {len(pages)} pages indexed",
    }


# ── Status ────────────────────────────────────────────────────────────────

def wiki_status() -> dict:
    """Get wiki graph status."""
    graph = get_wiki_graph()
    return {
        "wiki_pages": graph.page_count,
        "mode": "graph (Karpathy-style keyword search)",
    }


def chroma_status() -> dict:
    """Get ChromaDB textbook collection status."""
    coll = _get_collection()
    count = coll.count() if coll else 0
    return {
        "chroma_url": CHROMA_URL,
        "collection": CHROMA_COLLECTION,
        "documents": count,
        "model": EMBED_MODEL_NAME,
        "embed_dim": 384,
    }


# ── Query ─────────────────────────────────────────────────────────────────

def hybrid_query(query: str, wiki_radius: int = 1, top_k: int = 5) -> dict:
    """
    Hybrid search: Wiki Graph keyword + ChromaDB vector.

    Returns: {
        "query": str,
        "wiki_results": [...],
        "chroma_results": [...],
        "combined": [...],
    }
    """
    # ── 1. Wiki Graph (keyword search) ──
    graph = get_wiki_graph()
    wiki_pages = graph.search(query)[:top_k]

    wiki_results = []
    for page in wiki_pages:
        wiki_results.append({
            "page_title": page.title,
            "slug": page.slug,
            "relevance": 1.0,  # keyword match
            "source": "wiki",
            "preview": page.content[:300] if page.content else "",
        })

    # ── 2. ChromaDB (vector search) ──
    chroma_results = []
    coll = _get_collection()
    if coll and coll.count() > 0:
        try:
            model = _get_embed_model()
            query_embedding = model.encode([query]).tolist()

            results = coll.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            if results and results.get("ids") and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    dist = results["distances"][0][i] if results.get("distances") else 1.0
                    doc = results["documents"][0][i] if results.get("documents") else ""

                    chroma_results.append({
                        "page_title": f"{meta.get('chapter', '')} › {meta.get('section', '')}",
                        "slug": meta.get("source", ""),
                        "relevance": round(1.0 - min(dist, 1.0), 3),
                        "source": "chroma",
                        "preview": doc[:300],
                        "metadata": meta,
                    })
        except Exception as e:
            chroma_results.append({
                "page_title": "ChromaDB error",
                "slug": "",
                "relevance": 0,
                "source": "chroma",
                "preview": str(e)[:200],
            })

    # ── 3. Combine (deduplicate by title) ──
    seen = set()
    combined = []
    for r in wiki_results + chroma_results:
        key = r["page_title"][:80]
        if key not in seen:
            seen.add(key)
            combined.append(r)

    # Sort by relevance
    combined.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "query": query,
        "wiki_results": wiki_results,
        "chroma_results": chroma_results,
        "combined": combined[:top_k],
        "wiki_count": len(wiki_results),
        "chroma_count": len(chroma_results),
    }
