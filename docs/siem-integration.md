# SIEM-интеграция — syslog CEF + Security Log Storage

**Дата:** 09.07.2026  
**Задача:** #35 ROADMAP  
**Компонент:** `gateway/security_egress.py` (расширен)  
**Основа:** #34 Security Gateway Egress

---

## Архитектура хранения и доставки security-событий

```dot
digraph SIEM {
    rankdir=TB;
    bgcolor="#0a0a0f";
    fontname="Inter";

    node [fontname="Inter", fontsize=11, style=filled, penwidth=0];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    trigger [label="Security Event\n(DSP/PII/System leak)", shape=box, fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];

    subgraph cluster_gateway {
        label="Gateway Pod";
        fontcolor="#818cf8";
        color="#4f46e5";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];

        code [label="log_security_event()\n3 канала логирования", shape=box, fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
    }

    subgraph cluster_channels {
        label="3 канала доставки";
        fontcolor="#34d399";
        color="#34d399";
        bgcolor="#13131a";

        node [fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];

        pg [label="PostgreSQL\nsecurity_events\nструктурированные\nзапросы", shape=cylinder];
        file [label="JSON Lines\n/var/log/aither/\nsecurity.log\nротация 30 дней", shape=note];
        syslog [label="🆕 Syslog CEF\nUDP/TCP :514\n→ SIEM-коллектор", shape=box, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
    }

    subgraph cluster_consumers {
        label="Потребители";
        fontcolor="#e4e4ec";
        color="#4f46e5";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#4f46e5", fontcolor="#e4e4ec"];

        graf [label="Grafana\nsecurity dashboard", shape=box];
        logstash [label="Logstash/Fluentd\nfile tail → ES", shape=box];
        siem_ext [label="🆕 Внешний SIEM\nArcSight/QRadar/\nMaxPatrol/Splunk", shape=box, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
    }

    trigger -> code;
    code -> pg;
    code -> file;
    code -> syslog;
    pg -> graf;
    file -> logstash;
    syslog -> siem_ext;
}
```

## Формат CEF-сообщения

```dot
digraph CEFFormat {
    rankdir=TB;
    bgcolor="#0a0a0f";
    fontname="Inter";

    node [fontname="Inter", fontsize=10, style=filled, penwidth=0, shape=box];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    subgraph cluster_rfc {
        label="RFC 5424 Header";
        fontcolor="#818cf8";
        color="#4f46e5";
        bgcolor="#13131a";

        node [fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
        pri [label="<PRI>\nfacility*8+severity\nlocal0.CRIT = 130"];
        ver [label="1\nversion"];
        ts [label="TIMESTAMP\nISO 8601"];
        host [label="HOSTNAME"];
        app [label="APP-NAME\naither-gateway"];
        proc [label="PROCID\n-"];
        msgid [label="MSGID\n-"];
    }

    subgraph cluster_cef {
        label="CEF Body";
        fontcolor="#34d399";
        color="#34d399";
        bgcolor="#13131a";

        node [fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
        prefix [label="CEF:0\nversion"];
        vendor [label="Aither\nDevice Vendor"];
        product [label="SecurityGateway\nDevice Product"];
        dev_ver [label="1.0\nDevice Version"];
        sig_id [label="dsp_marker\nSignature ID"];
        sig_name [label="Egress dsp\nSignature Name"];
        cef_sev [label="10\nSeverity (critical)"];
    }

    subgraph cluster_ext {
        label="CEF Extension";
        fontcolor="#fbbf24";
        color="#fbbf24";
        bgcolor="#13131a";

        node [fillcolor="#fbbf2410", color="#fbbf24", fontcolor="#fbbf24", fontsize=9];
        e1 [label="orgId=uuid\nrequestId=xxx\nmodel=qwen\n..."];
    }

    pri -> ver -> ts -> host -> app -> proc -> msgid;
    msgid -> prefix;
    prefix -> vendor -> product -> dev_ver -> sig_id -> sig_name -> cef_sev;
    cef_sev -> e1;
}
```

## Пример CEF-сообщения

```
<130>1 2026-07-09T14:29:48.000Z skravchuk-vps-1 aither-gateway - - - CEF:0|Aither|SecurityGateway|1.0|dsp_marker|Egress dsp|10|orgId=00000000-0000-0000-0000-000000000001 requestId=f58d5826 model=/models/Qwen2.5-14B-Instruct direction=egress ruleCategory=dsp action=block requestHash=70ecdf938851137d snippet=для служебного пользования msg=Security egress: dsp/dsp_marker
```

Разбор по полям:

| Поле | Значение | Описание |
|---|---|---|
| `<130>` | PRI | local0 (16) × 8 + CRIT (2) = 130 |
| `1` | Version | RFC 5424 |
| `2026-07-09T...` | Timestamp | ISO 8601 UTC |
| `aither-gateway` | APP-NAME | Идентификатор приложения |
| `CEF:0` | CEF Version | 0 |
| `Aither` | Vendor | Производитель |
| `SecurityGateway` | Product | Продукт |
| `dsp_marker` | Signature ID | Уникальный ID правила |
| `Egress dsp` | Name | Человекочитаемое имя |
| `10` | Severity | 10 = Critical (CEF scale 0-10) |

## Поток событий безопасности

```dot
digraph EventFlow {
    rankdir=LR;
    bgcolor="#0a0a0f";
    fontname="Inter";

    node [fontname="Inter", fontsize=10, style=filled, penwidth=0, shape=box];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    request [label="Client\nRequest", fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];

    subgraph cluster_gw {
        label="Gateway Processing";
        color="#34d399";
        bgcolor="#13131a";
        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];

        ingress [label="Ingress\nSecurity", fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
        vllm [label="vLLM", fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
        egress [label="🆕 Egress\nSecurity", fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    }

    subgraph cluster_log {
        label="Logging (3 channels)";
        color="#fbbf24";
        bgcolor="#13131a";
        node [fillcolor="#fbbf2410", color="#fbbf24", fontcolor="#fbbf24"];

        decide [label="log_security_event()", shape=diamond, fillcolor="#fbbf2420"];
        pg [label="PG\nsecurity_events", shape=cylinder];
        file [label="JSON Lines\n.log", shape=note];
        syslog_cef [label="Syslog CEF\nUDP :514", shape=box];
    }

    subgraph cluster_siem {
        label="External SIEM";
        color="#f87171";
        bgcolor="#13131a";
        node [fillcolor="#f8717110", color="#f87171", fontcolor="#f87171"];

        collector [label="Syslog\nCollector", shape=box];
        parser [label="CEF Parser\nArcSight/QRadar/\nSplunk/MaxPatrol", shape=box];
    }

    request -> ingress -> vllm -> egress;
    egress -> decide [label="violation"];
    decide -> pg;
    decide -> file;
    decide -> syslog_cef;
    syslog_cef -> collector -> parser;
}
```

## Конфигурация SIEM

| Переменная | По умолчанию | Описание |
|---|---|---|
| `SIEM_ENABLED` | `true` | Включить отправку в SIEM |
| `SIEM_HOST` | `127.0.0.1` | Адрес SIEM-коллектора |
| `SIEM_PORT` | `514` | Порт (514 — стандартный syslog) |
| `SIEM_PROTO` | `udp` | Протокол: `udp` или `tcp` |
| `SIEM_FACILITY` | `local0` | Syslog facility: local0-local7 |
| `SIEM_APP_NAME` | `aither-gateway` | Имя приложения в syslog |
| `SECURITY_LOG_DIR` | `/var/log/aither` | Директория логов |
| `SECURITY_LOG_RETENTION` | `30` | Дней хранения JSON-логов |

## Тестирование

| Тест | Результат |
|---|---|
| DSP → 403 + security_event | ✅ `dsp_marker` в PostgreSQL + JSON log |
| Нормальный запрос → 200 | ✅ Без блокировки |
| Security log файл | ✅ `/var/log/aither/security.log` (756 bytes) |
| CEF формат | ✅ RFC 5424 + CEF:0 header, все поля |
| PRI calculation | ✅ local0.CRIT = 130 |
| Vendor/Product | ✅ Aither/SecurityGateway |
