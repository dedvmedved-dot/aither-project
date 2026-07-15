#!/usr/bin/env python3
"""ChromaDB text-query proxy — accepts text, returns vector search results."""
import json, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import chromadb

COLLECTION = "textbook"
CHROMA_PATH = "/chroma/chroma"

# One-time init
client = chromadb.Client()

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence logs

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/status":
            try:
                col = client.get_collection(COLLECTION)
                self._send_json({
                    "collection": COLLECTION,
                    "documents": col.count(),
                    "embed_dim": 384,
                    "status": "ok",
                })
            except Exception as e:
                self._send_json({"error": str(e), "status": "error"}, 500)
        elif path == "/health":
            self._send_json({"status": "ok"})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/query":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                query_text = body.get("query", body.get("query_texts", [""]))
                if isinstance(query_text, list):
                    query_text = query_text[0] if query_text else ""
                top_k = body.get("top_k", body.get("n_results", 5))

                col = client.get_collection(COLLECTION)
                results = col.query(
                    query_texts=[query_text],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"],
                )

                # Convert to simplified format matching hybrid_rag expectations
                items = []
                if results.get("ids") and results["ids"]:
                    for i, doc_id in enumerate(results["ids"][0]):
                        meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                        dist = results["distances"][0][i] if results.get("distances") else 1.0
                        doc = results["documents"][0][i] if results.get("documents") else ""

                        items.append({
                            "id": doc_id,
                            "document": doc,
                            "metadata": meta,
                            "distance": dist,
                            "page_title": f"{meta.get('chapter', '')} › {meta.get('section', '')}",
                            "source": meta.get("source", ""),
                            "preview": doc[:300],
                            "relevance": round(1.0 - min(dist, 1.0), 3),
                        })

                self._send_json({
                    "query": query_text,
                    "count": len(items),
                    "results": items,
                })
            except Exception as e:
                self._send_json({"error": str(e), "count": 0, "results": []}, 500)
        else:
            self._send_json({"error": "not found"}, 404)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    server = HTTPServer(("0.0.0.0", port), ProxyHandler)
    print(f"ChromaDB proxy listening on :{port}", flush=True)
    server.serve_forever()
