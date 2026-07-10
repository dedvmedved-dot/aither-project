"""
Hybrid RAG: Wiki Graph (keyword) + ChromaDB (vector via REST API).

No external dependencies — uses urllib for ChromaDB REST calls.
"""

import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from wiki_graph import get_wiki_graph, reload_wiki_graph

# ── Config ────────────────────────────────────────────────────────────────
CHROMA_URL = os.environ.get("CHROMA_URL", "http://chromadb:8000")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "textbook")


def _chroma_req(method: str, path: str, body: dict = None) -> dict:
    """Call ChromaDB REST API. Returns parsed JSON."""
    url = f"{CHROMA_URL}/api/v1/{path}"
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        resp = urlopen(req, timeout=10)
        return json.loads(resp.read())
    except HTTPError as e:
        return {"error": str(e), "status": e.code}


def _get_or_create_collection() -> dict:
    """Ensure textbook collection exists."""
    # Try to get the collection
    result = _chroma_req("GET", f"collections/{CHROMA_COLLECTION}")
    if result.get("error"):
        # Create it
        result = _chroma_req("POST", "collections", {
            "name": CHROMA_COLLECTION,
            "metadata": {"description": "Учебник Aither"}
        })
    return result


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
    try:
        result = _chroma_req("GET", f"collections/{CHROMA_COLLECTION}")
        count = 0
        if not result.get("error") and isinstance(result, dict):
            count = result.get("metadata", {}).get("count", 0) if isinstance(result.get("metadata"), dict) else 0
        return {
            "chroma_url": CHROMA_URL,
            "collection": CHROMA_COLLECTION,
            "documents": count,
            "embed_dim": 384,
        }
    except Exception as e:
        return {
            "chroma_url": CHROMA_URL,
            "collection": CHROMA_COLLECTION,
            "documents": 0,
            "embed_dim": 384,
            "error": str(e)[:100],
        }


# ── Query ─────────────────────────────────────────────────────────────────

def hybrid_query(query: str, wiki_radius: int = 1, top_k: int = 5) -> dict:
    """
    Hybrid search: Wiki Graph keyword + ChromaDB vector (via REST API).

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
            "relevance": 1.0,
            "source": "wiki",
            "preview": page.content[:300] if page.content else "",
        })

    # ── 2. ChromaDB (vector search via REST API) ──
    chroma_results = []
    try:
        coll_info = _chroma_req("GET", f"collections/{CHROMA_COLLECTION}")
        if not coll_info.get("error"):
            result = _chroma_req("POST", f"collections/{CHROMA_COLLECTION}/query", {
                "query_texts": [query],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            })
            if not result.get("error") and result.get("ids") and result["ids"]:
                for i, doc_id in enumerate(result["ids"][0]):
                    meta = result["metadatas"][0][i] if result.get("metadatas") else {}
                    dist = result["distances"][0][i] if result.get("distances") else 1.0
                    doc = result["documents"][0][i] if result.get("documents") else ""

                    chroma_results.append({
                        "page_title": f"{meta.get('chapter', '')} › {meta.get('section', '')}",
                        "slug": meta.get("source", ""),
                        "relevance": round(1.0 - min(dist, 1.0), 3),
                        "source": "chroma",
                        "preview": doc[:300],
                    })
    except Exception as e:
        chroma_results.append({
            "page_title": "ChromaDB error",
            "relevance": 0,
            "source": "chroma",
            "preview": str(e)[:200],
        })

    # ── 3. Combine ──
    seen = set()
    combined = []
    for r in wiki_results + chroma_results:
        key = r["page_title"][:80]
        if key not in seen:
            seen.add(key)
            combined.append(r)

    combined.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "query": query,
        "wiki_results": wiki_results,
        "chroma_results": chroma_results,
        "combined": combined[:top_k],
        "wiki_count": len(wiki_results),
        "chroma_count": len(chroma_results),
    }
