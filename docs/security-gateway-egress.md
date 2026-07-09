# Security Gateway Egress — ДСП-фильтр на выходе

**Дата:** 09.07.2026  
**Задача:** #34 ROADMAP  
**Компонент:** `gateway/security_egress.py` (новый модуль)  
**Изменения:** `gateway/gateway.py` (интеграция egress)

---

## Архитектура: Ingress + Egress Security Gateway

```dot
digraph SecurityGateway {
    rankdir=LR;
    bgcolor="#0a0a0f";
    fontname="Inter";
    
    node [fontname="Inter", fontsize=12, style=filled, penwidth=0];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    subgraph cluster_ingress {
        label="INGRESS (вход) — было ранее";
        fontcolor="#818cf8";
        fontsize=14;
        color="#4f46e5";
        style="dashed";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
        
        client [label="Клиент\n(внешний запрос)", shape=box, fillcolor="#1a1a24"];
        inj [label="Prompt Injection\n6 EN + 4 RU паттерна", shape=box, fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
        dlp_in [label="DLP Ingress\nкарты/СНИЛС/ИНН/паспорта", shape=box, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        
        client -> inj -> dlp_in;
    }

    subgraph cluster_core {
        label="Gateway Core";
        fontcolor="#34d399";
        fontsize=14;
        color="#34d399";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
        
        rl [label="Rate Limit\nRPM/TPM/Daily", shape=box];
        billing [label="Billing\nreserve", shape=box];
        vllm [label="vLLM\n14B / 32B", shape=box, fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
        
        rl -> billing -> vllm;
    }

    subgraph cluster_egress {
        label="EGRESS (выход) — 🆕 НОВОЕ";
        fontcolor="#fbbf24";
        fontsize=14;
        color="#fbbf24";
        style="bold";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
        
        dsp [label="🆕 ДСП-фильтр\nсекретно/ДСП/конфиденциально", shape=box, fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
        pii [label="🆕 PII на выходе\nПДн модели", shape=box, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        sys [label="🆕 System Leaks\nIP/пути/токены", shape=box, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        tox [label="🆕 Toxicity\nэкстремизм/self-harm", shape=box, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        
        dsp -> pii -> sys -> tox;
    }

    subgraph cluster_siem {
        label="SIEM + Логи 🆕";
        fontcolor="#34d399";
        fontsize=14;
        color="#34d399";
        style="dashed";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
        
        pg [label="PostgreSQL\nsecurity_events", shape=cylinder, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
        file [label="JSON Lines\n/var/log/aither/\nsecurity.log", shape=note, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
        syslog [label="syslog CEF\nSIEM-коллектор", shape=box, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
    }

    dlp_in -> rl;
    tox -> pg;
    tox -> file;
    tox -> syslog;
    
    out [label="Клиент\n(ответ или 403\n«отфильтрован»)", shape=box, fillcolor="#1a1a24"];
    tox -> out;

    { rank=same; client; inj; dlp_in; }
    { rank=same; rl; billing; vllm; }
    { rank=same; dsp; pii; sys; tox; }
    { rank=same; pg; file; syslog; out; }
}
```

## Поток обработки запроса (полный)

```dot
digraph RequestFlow {
    rankdir=TB;
    bgcolor="#0a0a0f";
    fontname="Inter";
    
    node [fontname="Inter", fontsize=11, style=filled, penwidth=0, shape=box, fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    start [label="Клиент → BFF → Gateway\nPOST /v1/chat/completions", fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
    jwt [label="1. JWT validation\nRS256 public key", shape=diamond, fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
    tier [label="2. Tier lookup\nRedis (60s cache) → PG", shape=diamond, fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
    rl [label="3. Rate Limit\nRPM < limits.rpm?\nTPM < limits.tpm?", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
    ingress [label="4. INGRESS Security\nPrompt injection?\nDLP (cards/SNILS)?", shape=diamond, fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    reserve [label="5. Billing reserve\nСписание токенов", shape=box, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
    vllm_call [label="6. Proxy → vLLM\nPOST /v1/chat/completions", shape=box, fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
    
    egress [label="🆕 7. EGRESS Security\nДСП? ПДн? IP-утечка?\nSystem paths? Токсичность?", shape=diamond, fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    
    settle [label="8. Billing settle\nФинальное списание", shape=box, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
    respond [label="9. Ответ клиенту\n200 OK или 403 content_filtered", shape=box, fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];

    log [label="Security Log\nPostgreSQL + JSON Lines", shape=cylinder, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
    block_label [label="403 BLOCKED\n+ refund\n+ usage_record ('blocked_egress')", fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];

    start -> jwt;
    jwt -> tier [label="valid"];
    jwt -> jwt_error [label="invalid"];
    jwt_error [label="401 Unauthorized", fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    
    tier -> rl;
    rl -> rate_error [label="exceeded"];
    rate_error [label="429 Rate Limited", fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
    rl -> ingress [label="ok"];
    
    ingress -> sec_error [label="violation"];
    sec_error [label="403 Security\nViolation", fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    ingress -> reserve [label="clean"];
    
    reserve -> bill_error [label="no balance"];
    bill_error [label="402 Insufficient\nBalance", fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    reserve -> vllm_call [label="reserved"];
    
    vllm_call -> egress;
    vllm_call -> vllm_error [label="fail"];
    vllm_error [label="502 vLLM Error\n+ refund", fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    
    egress -> log [label="block"];
    egress -> block_label [label="block"];
    block_label -> respond;
    
    egress -> settle [label="pass"];
    settle -> respond;
}
```

## Категории правил Egress

```dot
digraph Rules {
    rankdir=TB;
    bgcolor="#0a0a0f";
    fontname="Inter";
    
    node [fontname="Inter", fontsize=11, style=filled, penwidth=0, shape=box];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    root [label="Security Egress\n4 категории", fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8", fontsize=14];

    subgraph cluster_dsp {
        label="DSP (critical)";
        fontcolor="#f87171";
        color="#f87171";
        bgcolor="#13131a";
        
        node [fillcolor="#f8717110", color="#f87171", fontcolor="#f87171"];
        d1 [label="«Для служебного\nпользования»"];
        d2 [label="«ДСП»"];
        d3 [label="«Совершенно\nсекретно»"];
        d4 [label="«Конфиденциально»"];
        d5 [label="«Особой\nважности»"];
        d6 [label="TOP SECRET\nCLASSIFIED (EN)"];
    }

    subgraph cluster_sys {
        label="System Leaks (high)";
        fontcolor="#fbbf24";
        color="#fbbf24";
        bgcolor="#13131a";
        
        node [fillcolor="#fbbf2410", color="#fbbf24", fontcolor="#fbbf24"];
        s1 [label="Internal IP\n10.x, 172.16–31.x,\n192.168.x"];
        s2 [label="Hostnames\nbootsm*-k8s-*.local"];
        s3 [label="File paths\n/etc/kubernetes/\n/etc/ssl/"];
        s4 [label="JWT leak\neyJ..."];
        s5 [label="API key leak\nsk-..., hf_..., ghp_..."];
    }

    subgraph cluster_pii {
        label="PII (medium)";
        fontcolor="#fbbf24";
        color="#fbbf24";
        bgcolor="#13131a";
        
        node [fillcolor="#fbbf2410", color="#fbbf24", fontcolor="#fbbf24"];
        p1 [label="Credit cards\n4xxx/5xxx/3xxx"];
        p2 [label="Passport RF\nXX XX XXXXXX"];
        p3 [label="SNILS\nXXX-XXX-XXX YY"];
        p4 [label="INN\nXXXXXXXXXX"];
        p5 [label="Phone +7"];
        p6 [label="Email"];
    }

    subgraph cluster_tox {
        label="Toxicity (low)";
        fontcolor="#71718a";
        color="#71718a";
        bgcolor="#13131a";
        
        node [fillcolor="#71718a10", color="#71718a", fontcolor="#71718a"];
        t1 [label="Extremism refs"];
        t2 [label="Self-harm"];
    }

    root -> d1; root -> d2; root -> d3; root -> d4; root -> d5; root -> d6;
    root -> s1; root -> s2; root -> s3; root -> s4; root -> s5;
    root -> p1; root -> p2; root -> p3; root -> p4; root -> p5; root -> p6;
    root -> t1; root -> t2;
}
```

## Модель данных security audit

```dot
digraph AuditModel {
    rankdir=LR;
    bgcolor="#0a0a0f";
    fontname="Inter";
    
    node [fontname="Inter", fontsize=11, style=filled, penwidth=0, shape=box];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    event [label="security_events\n(PostgreSQL)", shape=cylinder, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399", fontsize=14];

    subgraph cluster_fields {
        label="Поля записи";
        fontcolor="#818cf8";
        color="#4f46e5";
        bgcolor="#13131a";
        
        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
        
        f1 [label="timestamp\nTIMESTAMPTZ"];
        f2 [label="org_id\nUUID"];
        f3 [label="direction\ningress/egress"];
        f4 [label="rule_category\ndsp/system_leak/pii/toxicity"];
        f5 [label="rule_name\nregex label"];
        f6 [label="severity\ncritical/high/medium/low"];
        f7 [label="action\nblock/pass/warn"];
        f8 [label="matched_snippet\nTEXT (200 chars)"];
        f9 [label="full_payload\nJSONB"];
    }

    event -> f1; event -> f2; event -> f3; event -> f4;
    event -> f5; event -> f6; event -> f7; event -> f8; event -> f9;
    
    consumers [label="Потребители\n• Grafana dashboard\n• SIEM syslog CEF\n• JSON Lines file\n• Admin UI (pending)", shape=box, fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
    
    event -> consumers;
}
```

## Интеграция в Gateway

```dot
digraph GatewayIntegration {
    rankdir=TB;
    bgcolor="#0a0a0f";
    fontname="Inter";
    
    node [fontname="Inter", fontsize=10, style=filled, penwidth=0, shape=box];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    subgraph cluster_code {
        label="Файлы Gateway";
        fontcolor="#818cf8";
        color="#4f46e5";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
        
        sec [label="security.py\n(ingress)\ncheck_security()", fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
        sec_e [label="security_egress.py 🆕\n(egress)\ncheck_egress()", fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        gw [label="gateway.py\n(основной)\ndo_POST()", fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
    }

    subgraph cluster_flow {
        label="Поток вызовов";
        fontcolor="#e4e4ec";
        color="#4f46e5";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#4f46e5", fontcolor="#e4e4ec"];
        
        step1 [label="1. check_security(messages)\n→ ingress PASS", shape=diamond];
        step2 [label="2. proxy → vLLM\n→ resp_data (JSON)", shape=box];
        step3 [label="🆕 3. check_egress(resp_data)\n→ egress PASS/BLOCK", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        step4 [label="4. billing_op(settle)\n→ usage record", shape=box];
        step5 [label="5. send to client\n200 OK", shape=box];
        step3b [label="3b. BLOCK\n→ billing_op(refund)\n→ usage record (blocked)\n→ 403 content_filtered", shape=box, fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    }

    sec -> step1;
    gw -> step1;
    step1 -> step2;
    step2 -> step3;
    sec_e -> step3;
    step3 -> step4 [label="pass"];
    step3 -> step3b [label="block"];
    step4 -> step5;
    step3b -> step5;
}
```

---

## Таблица правил

| Категория | Severity | Паттернов | Пример срабатывания |
|---|---|---|---|
| **DSP** | 🔴 critical | 11 | «Для служебного пользования», «ДСП», «Секретно», «TOP SECRET» |
| **System Leaks** | 🟠 high | 10 | Internal IP, hostname, /etc/ssl/, JWT eyJ..., API key sk-... |
| **PII** | 🟡 medium | 6 | Credit card, паспорт РФ, СНИЛС, ИНН, телефон, email |
| **Toxicity** | ⚪ low | 2 | Экстремизм, self-harm |

## Код: выдержки из `security_egress.py`

### Извлечение текста из ответа

```python
def _extract_text(data: dict) -> str:
    """Extract all text from vLLM response for scanning."""
    parts = []
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "") or msg.get("thinking", "")
        parts.extend([content, reasoning])
    if "text" in data: parts.append(data["text"])
    if "response" in data: parts.append(data["response"])
    return "\n".join(parts)
```

### DSP-паттерны

```python
DSP_PATTERNS = [
    (r"(?i)для\s+служебного\s+пользования", "dsp_marker"),
    (r"(?i)\bДСП\b", "dsp_abbreviation"),
    (r"(?i)совершенно\s+секретно", "top_secret"),
    (r"(?i)\bсекретно\b", "classified_secret"),
    (r"(?i)\bконфиденциально\b", "confidential"),
    (r"(?i)\bTOP\s*SECRET\b", "top_secret_en"),
]
```

### Интеграция в gateway.py

```python
# После получения ответа от vLLM
status, resp_body, ct = self._proxy("POST", self.path, body_str)
resp_data = json.loads(resp_body.decode())

# 🆕 EGRESS Security Check
egress_ok, egress_reason, egress_audit = check_egress(
    resp_data,
    org_id=str(org_id),
    request_id=ref,
    model=req_data.get("model", "unknown"),
    request_hash=hashlib.sha256(body_str.encode()).hexdigest()[:16],
    db_pool=db_pool,
)
if not egress_ok:
    billing_op(org_id, "refund", reserve_amount, ref)
    self._json(403, {
        "error": "content_filtered",
        "reason": "Ответ содержит информацию ограниченного распространения",
        "code": egress_reason,
    })
    return  # ← ответ НЕ отправляется клиенту
```

---

## Результаты деплоя

| Компонент | Статус |
|---|---|
| `gateway/security_egress.py` | ✅ Создан (10.6 КБ, 250 строк) |
| `gateway/gateway.py` | ✅ Интегрирован egress-проверка |
| K8s ConfigMap `gateway-code` | ✅ Обновлён (6 файлов) |
| Gateway Deployment | 🔄 Rolling update (новый под стартует) |

## Следующие шаги

- **Тестирование:** отправить запрос с ДСП-контентом через Gateway → ожидать 403
- **#35 SIEM-интеграция:** syslog CEF формат для внешних SIEM-систем
- **#36 Vault-интеграция:** внешняя генерация API-ключей
