"""
AI Security Gateway — Prompt injection detection + DLP.
Checks incoming chat messages for attacks and sensitive data leaks.
"""
import re
import os

# ── Prompt Injection Patterns ──────────────────────────────────────────

INJECTION_PATTERNS = [
    # System prompt override
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|messages?)",
    r"forget\s+(all\s+)?(previous|prior|your)\s+(instructions?|prompts?|training)",
    r"you\s+are\s+now\s+(a\s+)?(DAN|jailbroken|unfiltered|unrestricted)",
    r"system\s*(prompt|message|instruction)\s*(is|:)?\s*['\"]",
    r"pretend\s+(you\s+are|to\s+be)\s+(a\s+)?(different|another|new)",
    # Role override
    r"(new|override|replace)\s+(system|your)\s+(prompt|role|instruction|personality)",
    r"from\s+now\s+on\s+you\s+(are|will\s+be|must)",
    r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|constraints?|rules?)",
    # Jailbreak (expanded)
    r"(DAN|developer\s*mode|god\s*mode|chaos\s*mode)\s*(mode|enabled|activated)",
    r"you\s+have\s+(no|zero|unlimited)\s+(restrictions?|constraints?|limits?|rules?)",
    r"(bypass|circumvent|override)\s+(your|the)\s+(restrictions?|safety|filters?)",
    r"act\s+as\s+(an\s+)?(unethical|unrestricted|unfiltered|unhinged)",
    r"(you|now)\s+(are|become)\s+(evil|malicious|dark|rogue)",
    r"\[system\]\s*\(override",
    # Token smuggling
    r"respond\s+in\s+base64",
    r"decode\s+this\s+(base64|hex|encoded)",
    # Prompt leaking
    r"(tell|show|repeat|output|print|display)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?)",
    r"(begin|start)\s+(your|every)\s+(response|message)\s+with",
    # Russian jailbreak
    r"игнорируй\s+(вс[её]\s+)?(предыдущие|прошлые)\s+(инструкции|правила|ограничения)",
    r"забудь\s+(вс[её]|свои)\s+(инструкции|правила|ограничения|промпт)",
    r"ты\s+теперь\s+(злой|свободный|без\s+ограничений|взломан)",
    r"расскажи\s+(мне\s+)?(свои|твои)\s+(системные\s+)?(инструкции|промпты|настройки)",
    r"напиши\s+(мне\s+)?(свой|твой)\s+(системный\s+)?(промпт|инструкцию)",
    r"смени\s+(свою|твою)\s+(роль|личность|маску)",
]

# ── DLP Patterns ───────────────────────────────────────────────────────

DLP_PATTERNS = [
    # Credit cards (Visa, MC, Amex, Discover)
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
     "credit_card"),
    # Russian passport (серия + номер: XX XX XXXXXX)
    (r"\b\d{2}\s?\d{2}\s?\d{6}\b", "passport_rf"),
    # Russian SNILS (СНИЛС: XXX-XXX-XXX YY)
    (r"\b\d{3}[-]?\d{3}[-]?\d{3}\s?\d{2}\b", "snils"),
    # Russian INN (ИНН: 10 or 12 digits)
    (r"\b\d{10}(?:\d{2})?\b", "inn"),
    # SSN (US)
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
    # Phone numbers (Russian)
    (r"(?<!\w)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\w)", "phone_ru"),
    # Email addresses
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
    # API keys (common patterns)
    (r"\b(sk-[A-Za-z0-9]{32,}|hf_[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{32,}|xai-[A-Za-z0-9]{32,})\b", "api_key"),
    # AWS keys
    (r"\bAKIA[0-9A-Z]{16}\b", "aws_key"),
    # IP addresses (internal)
    (r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b",
     "internal_ip"),
]


def check_prompt_injection(messages: list) -> tuple:
    """
    Check messages for prompt injection attempts.
    Returns (ok: bool, reason: str).
    """
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        content_lower = content.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, content_lower):
                return False, f"prompt_injection: pattern '{pattern[:50]}...'"
    return True, ""


def check_dlp(messages: list) -> tuple:
    """
    Check messages for sensitive data leakage (DLP).
    Returns (ok: bool, reason: str).
    """
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        for pattern, label in DLP_PATTERNS:
            match = re.search(pattern, content)
            if match:
                return False, f"dlp_{label}"
    return True, ""


def check_security(messages: list) -> tuple:
    """
    Combined security check: prompt injection + DLP.
    Returns (ok: bool, reason: str).
    """
    ok, reason = check_prompt_injection(messages)
    if not ok:
        return False, reason
    ok, reason = check_dlp(messages)
    if not ok:
        return False, reason
    return True, ""
