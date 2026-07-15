"""
Hybrid RAG: Wiki Graph (keyword) + ChromaDB proxy (text→vector→search).

Gateway calls chroma-proxy service which handles embedding internally.
No chromadb dependency needed in Gateway.
"""

import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from wiki_graph import get_wiki_graph, reload_wiki_graph

# ── Config ────────────────────────────────────────────────────────────────
CHROMA_PROXY_URL = os.environ.get("CHROMA_PROXY_URL", "http://chroma-proxy.default.svc.cluster.local:9000")


def _proxy_get(path: str) -> dict:
    """GET request to chroma-proxy."""
    url = f"{CHROMA_PROXY_URL}/{path}"
    try:
        resp = urlopen(Request(url), timeout=10)
        return json.loads(resp.read())
    except HTTPError as e:
        return {"error": str(e), "status": e.code}
    except Exception as e:
        return {"error": str(e), "status": 0}


def _proxy_post(path: str, body: dict) -> dict:
    """POST request to chroma-proxy."""
    url = f"{CHROMA_PROXY_URL}/{path}"
    data = json.dumps(body).encode()
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urlopen(req, timeout=30)
        return json.loads(resp.read())
    except HTTPError as e:
        return {"error": str(e), "status": e.code}
    except Exception as e:
        return {"error": str(e), "status": 0}


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
    """Get ChromaDB textbook collection status via proxy."""
    result = _proxy_get("status")
    if result.get("error"):
        return {
            "chroma_url": CHROMA_PROXY_URL,
            "collection": "textbook",
            "documents": 0,
            "embed_dim": 384,
            "error": result.get("error", "unknown"),
        }
    return {
        "chroma_url": CHROMA_PROXY_URL,
        "collection": result.get("collection", "textbook"),
        "documents": result.get("documents", 0),
        "embed_dim": result.get("embed_dim", 384),
    }


# ── Query ─────────────────────────────────────────────────────────────────

def hybrid_query(query: str, wiki_radius: int = 1, top_k: int = 5) -> dict:
    """
    Hybrid search: Wiki Graph keyword + ChromaDB via proxy.

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
            "slug": page.path,
            "relevance": 1.0,
            "source": "wiki",
            "preview": page.content[:300] if page.content else "",
        })

    # ── 2. ChromaDB (vector search via proxy) ──
    chroma_results = []
    try:
        result = _proxy_post("query", {"query": query, "top_k": top_k})
        if not result.get("error") and result.get("results"):
            for item in result["results"]:
                chroma_results.append({
                    "page_title": item.get("page_title", ""),
                    "slug": item.get("source", ""),
                    "relevance": item.get("relevance", 0),
                    "source": "chroma",
                    "preview": item.get("preview", ""),
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
