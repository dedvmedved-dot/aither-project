"""
Cost-aware routing for Aither Gateway.

Analyzes incoming chat request and selects the most cost-effective vLLM endpoint.
"""
import os
import json
import re

# vLLM endpoint URLs (configured via environment)
VLLM_14B_URL = os.environ.get("VLLM_URL", "http://vllm:8000")
VLLM_32B_URL = os.environ.get("VLLM_32B_URL", "http://vllm-qwen32b:8000")

# Complexity keywords (Russian + English)
COMPLEX_KEYWORDS = [
    "объясни", "сравни", "анализ", "проанализируй", "опиши подробно",
    "explain", "compare", "analyze", "describe in detail",
    "разбери", "исследуй", "дай развёрнутый ответ",
    "break down", "investigate", "elaborate",
]

# Short-query threshold (characters)
SHORT_THRESHOLD = 150
# Long-query threshold (characters)
LONG_THRESHOLD = 600


def analyze_complexity(messages: list) -> dict:
    """
    Analyze messages for complexity signals.
    Returns dict with keys: total_chars, has_code, is_complex, is_short, complexity_score
    """
    if not messages:
        return {"total_chars": 0, "has_code": False, "is_complex": False,
                "is_short": True, "complexity_score": 0}

    total_chars = 0
    has_code = False
    is_complex = False
    score = 0

    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        total_chars += len(content)
        content_lower = content.lower()

        # Code detection: triple backticks or indented code blocks
        if "```" in content:
            has_code = True
            score -= 10  # code questions are usually well-defined → 14B is fine

        # Complexity keyword detection
        for kw in COMPLEX_KEYWORDS:
            if kw in content_lower:
                is_complex = True
                score += 20
                break

        # Multi-part questions (numbered/comma-separated)
        if re.search(r"(?:\d+[\.\)]\s|[Вв]о-первых|[Вв]о-вторых)", content):
            is_complex = True
            score += 15

        # Request for long output (essay, report, document)
        if re.search(r"(напиши|составь|создай|сгенерируй)\s+(статью|отч[её]т|документ|эссе|реферат|обзор)",
                     content_lower):
            is_complex = True
            score += 25

    is_short = total_chars < SHORT_THRESHOLD
    is_long = total_chars > LONG_THRESHOLD

    if is_long:
        score += 30
    elif is_short and not has_code:
        score -= 5

    return {
        "total_chars": total_chars,
        "has_code": has_code,
        "is_complex": is_complex or is_long,
        "is_short": is_short,
        "complexity_score": score,
    }


from typing import Optional

def select_model(messages: list, explicit_model: Optional[str] = None) -> tuple:
    """
    Select the best model and vLLM URL for the given messages.

    Args:
        messages: List of chat messages [{"role": "user", "content": "..."}]
        explicit_model: User-requested model name ("qwen2.5-14b", "qwen2.5-32b", "auto", or None)

    Returns:
        (model_id, vllm_url, model_path, reason)
    """
    # ── Model name constants ──────────────────────────────
    MODEL_14B_ID = "qwen2.5-14b"
    MODEL_32B_ID = "qwen2.5-32b"
    MODEL_14B_PATH = "/models/Qwen2.5-14B-Instruct"
    MODEL_32B_PATH = "qwen2.5-32b"

    # ── Explicit model selection ──────────────────────────
    if explicit_model:
        model_lower = explicit_model.lower()
        if "32b" in model_lower or "32" in model_lower:
            return MODEL_32B_ID, VLLM_32B_URL, MODEL_32B_PATH, "explicit:32b"
        if "14b" in model_lower or "14" in model_lower:
            return MODEL_14B_ID, VLLM_14B_URL, MODEL_14B_PATH, "explicit:14b"
        # Unknown model — fall through to auto-routing

    # ── Auto routing ──────────────────────────────────────
    analysis = analyze_complexity(messages)
    score = analysis["complexity_score"]

    # Decision logic
    if score >= 15:
        return MODEL_32B_ID, VLLM_32B_URL, MODEL_32B_PATH, \
            f"auto:complex(score={score})"
    elif analysis["has_code"] and not analysis["is_complex"]:
        return MODEL_14B_ID, VLLM_14B_URL, MODEL_14B_PATH, \
            f"auto:code(chars={analysis['total_chars']})"
    elif analysis["is_short"]:
        return MODEL_14B_ID, VLLM_14B_URL, MODEL_14B_PATH, \
            f"auto:short(chars={analysis['total_chars']})"
    else:
        return MODEL_14B_ID, VLLM_14B_URL, MODEL_14B_PATH, \
            f"auto:default(chars={analysis['total_chars']})"


def check_fallback(target_url: str) -> str:
    """
    Quick health-check of target vLLM. Returns fallback URL if target is down.
    (Simple TCP connect — not full health check.)
    """
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(target_url)
    host = parsed.hostname
    port = parsed.port or 8000

    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return target_url  # OK
    except Exception:
        # 32B down → fallback to 14B
        if target_url == VLLM_32B_URL:
            return VLLM_14B_URL
        # 14B down → try 32B as last resort
        return VLLM_32B_URL
