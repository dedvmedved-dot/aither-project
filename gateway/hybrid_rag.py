"""
Hybrid RAG Engine — LLM-Wiki graph search (Karpathy-style).

Architecture:
  1. Keyword search across wiki titles/tags/summaries/content
  2. Wiki graph traversal (1-hop neighbors from matched pages)
  3. Merge + deduplicate
  4. Re-rank: keyword relevance × 0.7 + wiki connectivity × 0.3
  5. Return top_k results with context snippets

Pure wiki-graph RAG — no external vector DB dependency.
Compile-once, query-many pattern.
"""
import os
import hashlib
from typing import Optional

from wiki_graph import WikiGraph, WikiPage, get_wiki_graph, reload_wiki_graph, WIKI_ROOT


# ── Content hashing for dedup ────────────────────────────────────────────

def _content_hash(text: str) -> str:
    return hashlib.md5(text.strip().encode()).hexdigest()[:12]


# ── Wiki page matching ───────────────────────────────────────────────────

def _match_wiki_pages(
    keyword_hits: list[tuple[float, WikiPage]],
    graph: WikiGraph,
    max_matches: int = 5,
) -> list[tuple[float, WikiPage]]:
    """Deduplicate and rank keyword search results."""
    seen: dict[str, tuple[float, WikiPage]] = {}
    for score, page in keyword_hits:
        slug = graph._slug(page.path)
        if slug not in seen or score > seen[slug][0]:
            seen[slug] = (score, page)
    result = sorted(seen.values(), key=lambda x: x[0], reverse=True)
    return result[:max_matches]


# ── Hybrid query ─────────────────────────────────────────────────────────

def hybrid_query(
    query: str,
    top_k: int = 5,
    wiki_radius: int = 1,
    vector_weight: float = 0.7,  # Now: keyword_weight
) -> list[dict]:
    """Hybrid RAG: keyword search + Wiki graph traversal."""
    graph = get_wiki_graph()

    # Phase 1: Keyword search
    hits = graph.search(query, limit=top_k * 3)
    if not hits:
        return []

    # Assign positional scores (first = 1.0, descending)
    n = len(hits)
    keyword_hits = [((n - i) / n, page) for i, page in enumerate(hits)]

    # Score normalization
    max_score = max(s for s, _ in keyword_hits) if keyword_hits else 1
    normalized = [(s / max_score, p) for s, p in keyword_hits]

    # Phase 2: Match and deduplicate
    wiki_matches = _match_wiki_pages(normalized, graph, max_matches=top_k)

    # Phase 3: Wiki graph expansion
    seen_slugs: set[str] = set()
    merged: list[dict] = []

    for vs, page in wiki_matches:
        slug = graph._slug(page.path)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        neighbors = graph.neighbors(slug)
        neighbor_titles = [n.title for n in neighbors[:5]]

        inlink_count = len(graph._inlinks.get(slug, set()))
        wiki_score = min(0.3 + 0.15 * inlink_count, 1.0)
        combined_score = vs * vector_weight + wiki_score * (1 - vector_weight)

        context = page.summary
        if neighbors:
            context += f"\n\nСвязанные страницы: {', '.join(neighbor_titles[:3])}"

        merged.append({
            "id": f"wiki:{slug}",
            "text": context,
            "source": page.path,
            "page_title": page.title,
            "page_type": page.page_type,
            "tags": page.tags,
            "score": round(combined_score, 4),
            "keyword_score": round(vs, 4),
            "wiki_score": round(wiki_score, 4),
            "inlinks": inlink_count,
            "neighbors": neighbor_titles[:5],
        })

    # Phase 4: Graph-only expansion
    if len(merged) < top_k and wiki_matches:
        for _, page in wiki_matches:
            slug = graph._slug(page.path)
            for n in graph.neighbors(slug):
                ns = graph._slug(n.path)
                if ns not in seen_slugs:
                    if len(merged) >= top_k:
                        break
                    seen_slugs.add(ns)
                    merged.append({
                        "id": f"wiki:{ns}",
                        "text": n.summary,
                        "source": n.path,
                        "page_title": n.title,
                        "page_type": n.page_type,
                        "tags": n.tags,
                        "score": 0.2,
                        "keyword_score": 0.0,
                        "wiki_score": 0.2,
                        "inlinks": len(graph._inlinks.get(ns, set())),
                        "neighbors": [x.title for x in graph.neighbors(ns)[:3]],
                    })

    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:top_k]


# ── Wiki ingest ──────────────────────────────────────────────────────────

def wiki_ingest() -> dict:
    """Re-index wiki — reloads graph from disk. No ChromaDB needed."""
    graph = reload_wiki_graph()
    pages = graph.list_all()
    return {
        "ingested": len(pages),
        "pages": [f"wiki/{p.path}" for p in pages],
        "message": f"wiki graph reloaded: {len(pages)} pages indexed",
    }


# ── Wiki status ──────────────────────────────────────────────────────────

def wiki_status() -> dict:
    """Get current wiki + RAG status."""
    graph = get_wiki_graph()
    return {
        "wiki_pages": graph.page_count,
        "mode": "graph-only (Karpathy-style)",
        "chroma_docs": 0,
        "wiki_docs_in_chroma": 0,
    }
