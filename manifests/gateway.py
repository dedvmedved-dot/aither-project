"""Aither API Gateway — proxy to vLLM with JWT RS256 + Redis rate limiting."""
import os, json, time
from urllib.request import Request, urlopen
from http.server import HTTPServer, BaseHTTPRequestHandler
import redis

# pip install pyjwt
import jwt as pyjwt

VLLM_URL = os.environ.get("VLLM_URL", "http://vllm:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis")
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "60"))  # requests/min per org

r = redis.Redis(host=REDIS_URL, port=6379, decode_responses=True,
                socket_connect_timeout=2)

# Load public key for delegation JWT validation
PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")
if not PUBLIC_KEY:
    try:
        with open("/app/delegation/public.pem") as f:
            PUBLIC_KEY = f.read()
    except:
        pass
if not PUBLIC_KEY:
    try:
        with open("./delegation/public.pem") as f:
            PUBLIC_KEY = f.read()
    except:
        pass

print(f"Gateway: public key {'loaded' if PUBLIC_KEY else 'MISSING'} ({len(PUBLIC_KEY)} chars)", flush=True)

class Gateway(BaseHTTPRequestHandler):

    def _check_jwt(self):
        """Validate delegation JWT (RS256). Returns payload or None."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
        try:
            if PUBLIC_KEY:
                payload = pyjwt.decode(token, PUBLIC_KEY, algorithms=["RS256"],
                                       options={"verify_exp": True, "verify_iss": False})
                return payload
        except pyjwt.ExpiredSignatureError:
            return "expired"
        except Exception:
            pass

        # Fallback: raw API key (legacy mode, no JWT)
        return {"legacy_key": token}

    def _check_rate_limit(self, org_id):
        """Rate limit per org_id (60 req/min)."""
        now = int(time.time())
        window = now // 60
        counter_key = f"ratelimit:{org_id}:{window}"
        count = r.incr(counter_key)
        if count == 1:
            r.expire(counter_key, 120)
        return count <= RATE_LIMIT

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

        # Validate JWT
        payload = self._check_jwt()
        if payload is None:
            self._json(401, {"error": "unauthorized — valid delegation token required"})
            return
        if payload == "expired":
            self._json(401, {"error": "delegation token expired"})
            return

        # Rate limit per org
        org_id = payload.get("org_id", "unknown")
        if not self._check_rate_limit(org_id):
            self._json(429, {"error": "rate limit exceeded", "retry_after": 60})
            return

        # Read body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"

        # Override model
        try:
            req_data = json.loads(body)
            req_data["model"] = "/models/Qwen2.5-14B-Instruct"
            body = json.dumps(req_data)
        except:
            pass

        # Proxy to vLLM
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
    print(f"Gateway listening on :{port}", flush=True)
    server.serve_forever()
