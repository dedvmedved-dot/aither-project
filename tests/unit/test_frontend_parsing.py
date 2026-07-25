"""
Unit tests: Frontend parsing logic (zone detection, error mapping,
            model selector, API response extraction).

Mirrors logic from aither-v2/services/portal-frontend/app.js
All functions are JS → Python ports for unit-testing the logic.
"""

import re


# ── Reference implementations (ported from app.js) ──────────────────

def detect_zone(hostname: str) -> str:
    """Determine zone from hostname.

    Ported from app.js:
        function detectZone() {
            const host = window.location.hostname;
            if (host.includes('10.129') || host.includes('test') || host === 'localhost') {
                return 'TEST ZONE';
            }
            return 'INTERNET';
        }
    """
    if "10.129" in hostname or "test" in hostname or hostname == "localhost":
        return "TEST ZONE"
    return "INTERNET"


def get_zone_class(zone: str) -> str:
    """Get CSS class for zone badge.

    Ported from app.js: ZONE_CLASS = ZONE === 'INTERNET' ? 'zone-internet' : 'zone-test'
    """
    return "zone-internet" if zone == "INTERNET" else "zone-test"


def map_chat_error(status_code: int, detail: str | None = None) -> str:
    """Map HTTP status code to Russian error message.

    Ported from app.js → showChatError():
        const errors = {
            401: 'Ошибка авторизации. Войдите заново.',
            403: 'Доступ запрещён. Недостаточно прав.',
            404: 'Модель или endpoint не найден.',
            422: 'Некорректный запрос.',
            429: 'Превышен лимит запросов. Подождите минуту.',
            500: 'Внутренняя ошибка сервера.',
            502: 'Ошибка шлюза.',
            503: 'Сервис временно недоступен.',
            504: 'Таймаут — модель не успела ответить.',
            0: 'Ошибка сети — проверьте подключение.',
        };
    """
    errors = {
        401: "Ошибка авторизации. Войдите заново.",
        403: "Доступ запрещён. Недостаточно прав.",
        404: "Модель или endpoint не найден.",
        422: "Некорректный запрос.",
        429: "Превышен лимит запросов. Подождите минуту.",
        500: "Внутренняя ошибка сервера.",
        502: "Ошибка шлюза.",
        503: "Сервис временно недоступен.",
        504: "Таймаут — модель не успела ответить.",
        0: "Ошибка сети — проверьте подключение.",
    }
    if status_code in errors:
        return errors[status_code]
    return f"Ошибка HTTP {status_code}: {detail or 'неизвестная ошибка'}"


def get_model_description(model: str) -> str:
    """Get description for model selector info.

    Ported from app.js → updateModelInfo():
        if (model === 'qwen-14b') { ... 'Чат-модель — оптимизирована для диалогов' }
        else { ... 'Базовая модель — продолжает текст (не чат)' }
    """
    if model == "qwen-14b":
        return "Чат-модель — оптимизирована для диалогов"
    return "Базовая модель — продолжает текст (не чат)"


def extract_chat_response(data: dict) -> str | None:
    """Extract assistant reply from API response.

    Ported from app.js → sendChatMessage():
        if (res.data.choices && res.data.choices[0]) { ... choice.message?.content || choice.text }
        else if (res.data.content) { reply = res.data.content; }
        else if (res.data.response) { reply = res.data.response; }
        ...
        reply = res.data.choices?.[0]?.text || 'Пустой ответ от модели.';
    """
    if not data:
        return None
    # choices[0].message.content (OpenAI format)
    choices = data.get("choices", [])
    if choices and len(choices) > 0:
        choice = choices[0]
        msg = choice.get("message")
        if msg and isinstance(msg, dict):
            return msg.get("content") or ""
        if "text" in choice:
            return choice["text"] or ""
        return str(choice)
    # Direct content field
    if "content" in data:
        return data["content"]
    # Direct response field
    if "response" in data:
        return data["response"]
    return None


def strip_scope_display(scopes: list[str]) -> list[str]:
    """Strip scope strings for display in UI table.

    Ported from app.js → loadApiKeys():
        (k.scopes || []).map(s => s.replace('model:', '').replace(':chat-adapter',':chat').replace(':chat',''))

    The JS .replace(':chat','') strips all occurrences of literal ':chat'.
    """
    result = []
    for s in scopes:
        s = s.replace("model:", "")
        s = s.replace(":chat-adapter", ":chat")
        s = s.replace(":chat", "")  # strip all ':chat' like JS
        result.append(s)
    return result


# ── Tests: Zone Detection ───────────────────────────────────────────

class TestZoneDetection:
    """Zone detection from hostname."""

    def test_internet_hosts(self):
        """Public hosts resolve to INTERNET."""
        for host in ["fb1.spb.ru", "aither.ai", "example.com"]:
            assert detect_zone(host) == "INTERNET", f"{host} → not INTERNET"

    def test_test_zone_by_ip_prefix(self):
        """10.129.x.x hosts resolve to TEST ZONE."""
        assert detect_zone("10.129.13.78") == "TEST ZONE"
        assert detect_zone("10.129.1.1") == "TEST ZONE"

    def test_test_zone_by_test_keyword(self):
        """Hostnames containing 'test' resolve to TEST ZONE."""
        assert detect_zone("test.aither.ai") == "TEST ZONE"
        assert detect_zone("staging-test.local") == "TEST ZONE"

    def test_localhost(self):
        """localhost resolves to TEST ZONE."""
        assert detect_zone("localhost") == "TEST ZONE"

    def test_zone_class_mapping(self):
        """Zone → CSS class mapping."""
        assert get_zone_class("INTERNET") == "zone-internet"
        assert get_zone_class("TEST ZONE") == "zone-test"


# ── Tests: Error Mapping ────────────────────────────────────────────

class TestErrorMapping:
    """HTTP error code → Russian error message."""

    def test_known_error_codes(self):
        """All 10 known codes map to Russian messages."""
        codes_and_checks = [
            (401, "авторизации"),
            (403, "запрещён"),
            (404, "не найден"),
            (422, "Некорректный"),
            (429, "лимит"),
            (500, "сервера"),
            (502, "шлюза"),
            (503, "недоступен"),
            (504, "Таймаут"),
            (0, "сети"),
        ]
        for code, keyword in codes_and_checks:
            msg = map_chat_error(code)
            assert keyword.lower() in msg.lower(), (
                f"Code {code}: expected '{keyword}' in '{msg}'"
            )

    def test_unknown_error_code(self):
        """Unknown codes get a generic message with the code number."""
        msg = map_chat_error(418, "I'm a teapot")
        assert "418" in msg
        assert "teapot" in msg

    def test_error_no_detail(self):
        """When no detail is provided, fallback text is used."""
        msg = map_chat_error(999)
        assert "999" in msg
        assert "неизвестная ошибка" in msg


# ── Tests: Model Selector ───────────────────────────────────────────

class TestModelSelector:
    """Model selector info text logic."""

    def test_14b_description(self):
        """qwen-14b shows chat-model description."""
        desc = get_model_description("qwen-14b")
        assert "Чат-модель" in desc
        assert "диалогов" in desc

    def test_32b_description(self):
        """qwen-32b-base shows base-model description."""
        desc = get_model_description("qwen-32b-base")
        assert "Базовая модель" in desc
        assert "не чат" in desc

    def test_unknown_model_description(self):
        """Any model other than qwen-14b gets the base-model description."""
        desc = get_model_description("gpt-4")
        assert "Базовая модель" in desc


# ── Tests: API Response Extraction ──────────────────────────────────

class TestResponseExtraction:
    """Extract assistant reply from various API response shapes."""

    def test_openai_format(self):
        """choices[0].message.content (14B chat)."""
        data = {
            "choices": [
                {"message": {"role": "assistant", "content": "Привет! Чем помочь?"}}
            ]
        }
        assert extract_chat_response(data) == "Привет! Чем помочь?"

    def test_text_field_format(self):
        """choices[0].text (32B completion)."""
        data = {"choices": [{"text": "продолжает предложение..."}]}
        assert extract_chat_response(data) == "продолжает предложение..."

    def test_direct_content(self):
        """Direct content field on response."""
        data = {"content": "Прямой ответ"}
        assert extract_chat_response(data) == "Прямой ответ"

    def test_direct_response(self):
        """Direct response field."""
        data = {"response": "Ответ через response"}
        assert extract_chat_response(data) == "Ответ через response"

    def test_empty_and_none(self):
        """Empty data or missing fields → None."""
        assert extract_chat_response({}) is None
        assert extract_chat_response({"choices": []}) is None
        assert extract_chat_response(None) is None

    def test_empty_content_not_confused_with_falsy(self):
        """Empty string content is returned (not None)."""
        data = {"choices": [{"message": {"content": ""}}]}
        assert extract_chat_response(data) == ""

    def test_choice_without_message_or_text(self):
        """Choice dict without message/text → stringified."""
        data = {"choices": [{"index": 0, "finish_reason": "stop"}]}
        result = extract_chat_response(data)
        assert result is not None  # falls back to str(choice)


# ── Tests: Scope Display Stripping ──────────────────────────────────

class TestScopeDisplayStripping:
    """Strip scope strings for UI display."""

    def test_chat_scope(self):
        """'model:14b:chat' → '14b'."""
        assert strip_scope_display(["model:14b:chat"]) == ["14b"]

    def test_chat_adapter_scope(self):
        """'model:32b:chat-adapter' → '32b' (after :chat-adapter→:chat→strip :chat)."""
        assert strip_scope_display(["model:32b:chat-adapter"]) == ["32b"]

    def test_completion_scope(self):
        """'model:32b:completion' → '32b:completion'."""
        assert strip_scope_display(["model:32b:completion"]) == ["32b:completion"]

    def test_multiple_scopes(self):
        """Multiple scopes are all stripped correctly."""
        scopes = ["model:14b:chat", "model:32b:chat-adapter", "model:32b:completion"]
        result = strip_scope_display(scopes)
        assert result == ["14b", "32b", "32b:completion"]

    def test_empty_list(self):
        """Empty scope list stays empty."""
        assert strip_scope_display([]) == []
