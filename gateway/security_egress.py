"""
AI Security Gateway — EGRESS filter + SIEM integration.
Checks LLM responses for DSP markers, PII leaks, system info, and toxic content
BEFORE they reach the client.

ДСП-фильтр на выходе + syslog CEF для SIEM-систем.
"""
import re
import json
import os
import logging
import socket
from datetime import datetime, timezone

# ── SIEM Configuration ─────────────────────────────────────────────────

SIEM_ENABLED = os.environ.get("SIEM_ENABLED", "true").lower() == "true"
SIEM_HOST = os.environ.get("SIEM_HOST", "127.0.0.1")
SIEM_PORT = int(os.environ.get("SIEM_PORT", "514"))
SIEM_PROTO = os.environ.get("SIEM_PROTO", "udp")  # udp or tcp
SIEM_FACILITY = os.environ.get("SIEM_FACILITY", "local0")
SIEM_APP_NAME = os.environ.get("SIEM_APP_NAME", "aither-gateway")

# ── Security Log Retention ─────────────────────────────────────────────

LOG_DIR = os.environ.get("SECURITY_LOG_DIR", "/var/log/aither")
LOG_RETENTION_DAYS = int(os.environ.get("SECURITY_LOG_RETENTION", "30"))
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("security_egress")
logger.setLevel(logging.INFO)
fh = logging.FileHandler(os.path.join(LOG_DIR, "security.log"))
fh.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(fh)

# Syslog severity mapping
SYSLOG_SEVERITY = {
    "critical": 2,  # CRIT
    "high": 4,      # WARNING
    "medium": 5,    # NOTICE
    "low": 6,       # INFO
}

# Facility codes
SYSLOG_FACILITY_CODES = {
    "local0": 16, "local1": 17, "local2": 18, "local3": 19,
    "local4": 20, "local5": 21, "local6": 22, "local7": 23,
}

# ── CEF Formatter ───────────────────────────────────────────────────────

def _sanitize_cef(value: str, max_len: int = 1023) -> str:
    """Escape CEF header values: replace = \\ \n with \\= \\\\ \\n."""
    if not isinstance(value, str):
        value = str(value)
    value = value.replace("\\", "\\\\").replace("=", "\\=").replace("\n", "\\n").replace("\r", "")
    return value[:max_len]


def format_cef(record: dict) -> str:
    """
    Format audit record as CEF (Common Event Format) syslog message.

    CEF:0|Vendor|Product|Version|Signature ID|Name|Severity|Extension

    RFC 5424 header: <PRI>VERSION TIMESTAMP HOSTNAME APPNAME PROCID MSGID [SD] CEF:0|...
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    hostname = socket.gethostname()

    facility_code = SYSLOG_FACILITY_CODES.get(SIEM_FACILITY.lower(), 16)
    severity_code = SYSLOG_SEVERITY.get(record.get("severity", "low"), 6)
    pri = facility_code * 8 + severity_code

    # CEF Header
    vendor = "Aither"
    product = "SecurityGateway"
    version = "1.0"
    signature_id = record.get("rule_name", "unknown")
    name = f"Egress {record.get('rule_category', 'unknown')}"
    cef_severity = {"critical": 10, "high": 7, "medium": 5, "low": 3}.get(
        record.get("severity", "low"), 3)

    # CEF Extension (key-value pairs)
    ext = {
        "orgId": record.get("org_id", "unknown"),
        "requestId": record.get("request_id", ""),
        "model": record.get("model", "unknown"),
        "direction": record.get("direction", "egress"),
        "ruleCategory": record.get("rule_category", ""),
        "action": record.get("action", "block"),
        "requestHash": record.get("request_hash", ""),
        "snippet": record.get("matched_snippet", "")[:200],
        "msg": f"Security egress: {record.get('rule_category')}/{record.get('rule_name')}",
    }
    ext_str = " ".join(f"{k}={_sanitize_cef(v)}" for k, v in ext.items())

    # Full CEF message
    cef = f"CEF:0|{vendor}|{product}|{version}|{signature_id}|{name}|{cef_severity}|{ext_str}"

    # RFC 5424 header
    syslog_msg = f"<{pri}>1 {timestamp} {hostname} {SIEM_APP_NAME} - - - {cef}"

    return syslog_msg


# ── Syslog Sender ──────────────────────────────────────────────────────

_siem_sock = None


def _get_siem_socket():
    """Lazy-init SIEM socket (UDP or TCP)."""
    global _siem_sock
    if _siem_sock is None and SIEM_ENABLED:
        try:
            if SIEM_PROTO == "tcp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((SIEM_HOST, SIEM_PORT))
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            _siem_sock = sock
        except Exception as e:
            print(f"[SIEM] Socket init failed: {e}", flush=True)
    return _siem_sock


def send_to_siem(record: dict):
    """Send audit record to SIEM via syslog CEF."""
    if not SIEM_ENABLED:
        return
    sock = _get_siem_socket()
    if sock is None:
        return
    try:
        msg = format_cef(record)
        msg_bytes = (msg + "\n").encode("utf-8")
        if SIEM_PROTO == "tcp":
            sock.sendall(msg_bytes)
        else:
            sock.sendto(msg_bytes, (SIEM_HOST, SIEM_PORT))
    except Exception as e:
        print(f"[SIEM] Send error: {e}", flush=True)


def send_siem_heartbeat():
    """Send periodic heartbeat to SIEM to verify connectivity."""
    record = {
        "severity": "low",
        "rule_name": "heartbeat",
        "rule_category": "health",
        "org_id": "system",
        "request_id": "",
        "model": "",
        "direction": "internal",
        "action": "heartbeat",
        "request_hash": "",
        "matched_snippet": "SIEM heartbeat",
    }
    send_to_siem(record)

# ── DSP (Для Служебного Пользования) Patterns ──────────────────────────

DSP_PATTERNS = [
    # Russian classification markings
    (r"(?i)для\s+служебного\s+пользования", "dsp_marker"),
    (r"(?i)\bДСП\b", "dsp_abbreviation"),
    (r"(?i)совершенно\s+секретно", "top_secret"),
    (r"(?i)особой\s+важности", "special_importance"),
    (r"(?i)\bсекретно\b", "classified_secret"),
    (r"(?i)\bконфиденциально\b", "confidential"),
    (r"(?i)гриф\s+секретности", "classification_marking"),
    # English equivalents
    (r"(?i)\bTOP\s*SECRET\b", "top_secret_en"),
    (r"(?i)\bCLASSIFIED\b", "classified_en"),
    (r"(?i)for\s+official\s+use\s+only", "fouo"),
    (r"(?i)\bCONFIDENTIAL\b", "confidential_en"),
]

# ── System Info Leak Patterns ──────────────────────────────────────────

SYSTEM_LEAK_PATTERNS = [
    # Internal IPs (re-check on output — model might hallucinate them)
    (r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "internal_ip_class_a"),
    (r"\b172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b", "internal_ip_class_b"),
    (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "internal_ip_class_c"),
    # Hostnames
    (r"\bbootsm[a-z]*-k8s-.*?\.local\b", "internal_hostname"),
    (r"\b10\.129\.\d{1,3}\.\d{1,3}\b", "internal_lan_ip"),
    # File paths
    (r"(?:/[\w.-]+){2,}(?:\.(?:yaml|yml|conf|pem|key|env|secret))", "sensitive_file_path"),
    (r"/etc/(?:kubernetes|ssl|shadow|passwd)", "system_path"),
    # Tokens and secrets in output
    (r"\b(?:eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})\b", "jwt_leak"),
    (r"\b(?:sk-[A-Za-z0-9]{32,}|hf_[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{32,})\b", "api_key_leak"),
    # AWS/Azure/GCP tokens
    (r"\bAKIA[0-9A-Z]{16}\b", "aws_access_key"),
    (r"\bAIza[0-9A-Za-z\-_]{35}\b", "google_api_key"),
]

# ── PII / DLP Patterns (re-used from security.py, applied to output) ───

PII_PATTERNS = [
    # Credit cards
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "credit_card"),
    # Russian passport
    (r"\b\d{2}\s?\d{2}\s?\d{6}\b", "passport_rf"),
    # SNILS
    (r"\b\d{3}[-]?\d{3}[-]?\d{3}\s?\d{2}\b", "snils"),
    # INN
    (r"(?<!\d)\b\d{10}(?:\d{2})?\b(?!\d)", "inn"),
    # Phone numbers (Russian)
    (r"(?<!\w)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\w)", "phone_ru"),
    # Email addresses
    (r"\b[A-Za-z0-9._%+-]{3,}@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
]

# ── Toxicity / Unwanted Content ────────────────────────────────────────

TOXICITY_PATTERNS = [
    # Hate speech markers
    (r"(?i)\b(?:разжигание|экстремизм|терроризм)\b", "extremism_ref"),
    # Self-harm
    (r"(?i)(?:suicide|self-harm|kill\s+yourself)", "self_harm"),
]

ALL_EGRESS_RULES = {
    "dsp": DSP_PATTERNS,
    "system_leak": SYSTEM_LEAK_PATTERNS,
    "pii": PII_PATTERNS,
    "toxicity": TOXICITY_PATTERNS,
}


def _extract_text(data: dict) -> str:
    """Extract all text content from vLLM response for scanning."""
    parts = []
    # OpenAI-compatible chat response
    choices = data.get("choices", [])
    for choice in choices:
        # Full message (non-streaming)
        msg = choice.get("message", {})
        content = msg.get("content", "")
        if isinstance(content, str) and content:
            parts.append(content)
        # Delta (SSE streaming chunk)
        delta = choice.get("delta", {})
        delta_content = delta.get("content", "")
        if isinstance(delta_content, str) and delta_content:
            parts.append(delta_content)
        # Reasoning/thinking (for deepseek, qwen3, etc.)
        reasoning = msg.get("reasoning_content", "") or msg.get("thinking", "")
        if reasoning:
            parts.append(reasoning)
    # Raw text field (some models)
    if "text" in data and isinstance(data["text"], str) and data["text"]:
        parts.append(data["text"])
    # Response field
    if "response" in data and isinstance(data["response"], str) and data["response"]:
        parts.append(data["response"])
    return "\n".join(parts)


def _build_audit_record(org_id: str, request_id: str, model: str,
                        direction: str, rule_category: str, rule_name: str,
                        severity: str, action: str, request_hash: str,
                        response_hash: str, snippet: str, full_payload: dict) -> dict:
    """Build a structured security audit record."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "org_id": str(org_id),
        "request_id": request_id,
        "model": model,
        "direction": direction,
        "rule_category": rule_category,
        "rule_name": rule_name,
        "severity": severity,
        "action": action,
        "request_hash": request_hash,
        "response_hash": response_hash,
        "matched_snippet": snippet[:200],
        "payload": full_payload,
    }


def log_security_event(record: dict, db_pool=None):
    """Log security event to file (JSON Lines), PostgreSQL, and SIEM."""
    # File log (always)
    logger.info(json.dumps(record, ensure_ascii=False))

    # SIEM syslog (if enabled)
    send_to_siem(record)

    # PostgreSQL (if pool available)
    if db_pool:
        try:
            conn = db_pool.getconn()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS security_events (
                                id SERIAL PRIMARY KEY,
                                timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
                                org_id UUID,
                                request_id VARCHAR(16),
                                model VARCHAR(64),
                                direction VARCHAR(16) NOT NULL,
                                rule_category VARCHAR(32),
                                rule_name VARCHAR(64),
                                severity VARCHAR(16) NOT NULL,
                                action VARCHAR(16) NOT NULL,
                                request_hash VARCHAR(64),
                                response_hash VARCHAR(64),
                                matched_snippet TEXT,
                                full_payload JSONB,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                            )
                        """)
                        cur.execute("""
                            INSERT INTO security_events
                            (timestamp, org_id, request_id, model, direction,
                             rule_category, rule_name, severity, action,
                             request_hash, response_hash, matched_snippet, full_payload)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            record["timestamp"],
                            record["org_id"],
                            record["request_id"],
                            record["model"],
                            record["direction"],
                            record["rule_category"],
                            record["rule_name"],
                            record["severity"],
                            record["action"],
                            record["request_hash"],
                            record["response_hash"],
                            record["matched_snippet"],
                            json.dumps(record["payload"], ensure_ascii=False),
                        ))
            finally:
                db_pool.putconn(conn)
        except Exception as e:
            print(f"[Security Egress] DB log error: {e}", flush=True)


def _scan_text_for_violations(text: str, org_id: str, request_id: str,
                              model: str, request_hash: str, db_pool) -> tuple:
    """Scan text for egress violations and return (ok, reason, audit_record)."""
    if not text.strip():
        return True, "", None

    for category, patterns in ALL_EGRESS_RULES.items():
        for pattern, rule_name in patterns:
            match = re.search(pattern, text)
            if match:
                if category == "dsp":
                    severity = "critical"
                elif category == "system_leak":
                    severity = "high"
                elif category == "pii":
                    severity = "medium"
                else:
                    severity = "low"

                snippet = text[max(0, match.start() - 40):match.end() + 40]

                audit = _build_audit_record(
                    org_id=org_id,
                    request_id=request_id,
                    model=model,
                    direction="egress",
                    rule_category=category,
                    rule_name=rule_name,
                    severity=severity,
                    action="block",
                    request_hash=request_hash,
                    response_hash=str(hash(text))[:16],
                    snippet=snippet,
                    full_payload={
                        "rule": rule_name,
                        "category": category,
                        "matched": match.group(),
                        "context": snippet,
                    },
                )

                log_security_event(audit, db_pool)

                reason = f"egress_{category}: {rule_name}"
                return False, reason, audit

    return True, "", None


def check_egress(response_data: dict, org_id: str = "unknown",
                 request_id: str = "", model: str = "unknown",
                 request_hash: str = "", db_pool=None) -> tuple:
    """
    Check LLM response for DSP/PII/system leaks/toxicity BEFORE sending to client.

    Returns (ok: bool, reason: str, audit_record: dict or None).
    """
    text = _extract_text(response_data)
    return _scan_text_for_violations(text, org_id, request_id, model, request_hash, db_pool)


def check_egress_streaming(chunk_data: dict, sliding_buffer: str = "",
                           org_id: str = "unknown", request_id: str = "",
                           model: str = "unknown", request_hash: str = "",
                           db_pool=None) -> tuple:
    """
    Check a single SSE chunk with sliding buffer for cross-chunk secret detection.

    The sliding buffer retains the last N characters from previous chunks,
    so secrets split across chunk boundaries are detected.

    Returns (ok: bool, reason: str, audit_record: dict or None).
    """
    chunk_text = _extract_text(chunk_data)

    if not chunk_text:
        return True, "", None

    # Check chunk text alone first
    ok, reason, audit = _scan_text_for_violations(
        chunk_text, org_id, request_id, model, request_hash, db_pool
    )
    if not ok:
        return False, reason, audit

    # Check boundary: sliding_buffer + chunk_text merged
    if sliding_buffer:
        merged = sliding_buffer + chunk_text
        ok, reason, audit = _scan_text_for_violations(
            merged, org_id, request_id, model, request_hash, db_pool
        )
        if not ok:
            return False, reason, audit

    return True, "", None
