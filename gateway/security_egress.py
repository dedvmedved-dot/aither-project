"""
AI Security Gateway — EGRESS filter.
Checks LLM responses for DSP markers, PII leaks, system info, and toxic content
BEFORE they reach the client.

ДСП-фильтр на выходе: проверка ответов модели на наличие информации
ограниченного распространения.
"""
import re
import json
import os
import logging
from datetime import datetime, timezone

# ── Logging setup ──────────────────────────────────────────────────────

LOG_DIR = os.environ.get("SECURITY_LOG_DIR", "/var/log/aither")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("security_egress")
logger.setLevel(logging.INFO)
fh = logging.FileHandler(os.path.join(LOG_DIR, "security.log"))
fh.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(fh)

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
        msg = choice.get("message", {})
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        # Reasoning/thinking (for deepseek, qwen3, etc.)
        reasoning = msg.get("reasoning_content", "") or msg.get("thinking", "")
        if reasoning:
            parts.append(reasoning)
    # Raw text field (some models)
    if "text" in data and isinstance(data["text"], str):
        parts.append(data["text"])
    # Response field
    if "response" in data and isinstance(data["response"], str):
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
    """Log security event to file (JSON Lines) and optionally PostgreSQL."""
    # File log (always)
    logger.info(json.dumps(record, ensure_ascii=False))

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


def check_egress(response_data: dict, org_id: str = "unknown",
                 request_id: str = "", model: str = "unknown",
                 request_hash: str = "", db_pool=None) -> tuple:
    """
    Check LLM response for DSP/PII/system leaks/toxicity BEFORE sending to client.

    Returns (ok: bool, reason: str, audit_record: dict or None).
    """
    text = _extract_text(response_data)

    if not text.strip():
        return True, "", None

    # Check each rule category
    for category, patterns in ALL_EGRESS_RULES.items():
        for pattern, rule_name in patterns:
            match = re.search(pattern, text)
            if match:
                # Determine severity
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
