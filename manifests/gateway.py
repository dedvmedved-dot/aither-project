"""Aither API Gateway — minimal proxy to vLLM with Redis rate limiting."""
import os, json, time
from urllib.request import Request, urlopen
from http.server import HTTPServer, BaseHTTPRequestHandler
import redis

VLLM_URL = os.environ.get("VLLM_URL", "http://vllm:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis")
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "60"))  # requests per minute per key

r = redis.Redis(host=REDIS_URL, port=6379, decode_responses=True, socket_connect_timeout=2)

class Gateway(BaseHTTPRequestHandler):
    def _check_key(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        key = auth[7:]
        # Check rate limit
        now = int(time.time())
        window = now // 60
        counter_key = f"ratelimit:{key}:{window}"
        count = r.incr(counter_key)
        if count == 1:
            r.expire(counter_key, 120)
        if count > RATE_LIMIT:
            return "rate_limited"
        return "ok"

    def _proxy(self, method, path, body=None):
        url = f"{VLLM_URL}{path}"
        headers = {"Content-Type": "application/json"}
        data = body.encode() if body else None
        req = Request(url, data=data, headers=headers, method=method)
        try:
            resp = urlopen(req, timeout=120)
            return resp.status, resp.read(), resp.headers.get("Content-Type", "application/json")
        except Exception as e:
            return 502, str(e).encode(), "text/plain"

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        if self.path == "/v1/models":
            status, body, ct = self._proxy("GET", self.path)
            self.send_response(status)
            self.send_header("Content-Type", ct)
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/v1/"):
            self._json(404, {"error": "not found"})
            return

        # Rate limit check
        key_status = self._check_key()
        if key_status == "rate_limited":
            self._json(429, {"error": "rate limit exceeded"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"

        # Verify model in request
        try:
            req_data = json.loads(body)
            req_data["model"] = "/models/Qwen2.5-14B-Instruct"  # Override model
            body = json.dumps(req_data)
        except:
            pass

        status, resp_body, ct = self._proxy("POST", self.path, body)
        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.end_headers()
        self.wfile.write(resp_body)

    def log_message(self, format, *args):
        pass  # Silence access logs

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), Gateway)
    print(f"Gateway listening on :{port}")
    server.serve_forever()
