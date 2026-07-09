# Vault-интеграция — внешняя генерация API-ключей + политики ИБ

**Дата:** 09.07.2026  
**Задача:** #36 ROADMAP  
**Компонент:** `gateway/vault.py` (новый модуль, 250 строк)  

---

## Архитектура: Vault как внешний источник ключей

```dot
digraph VaultArch {
    rankdir=TB;
    bgcolor="#0a0a0f";
    fontname="Inter";

    node [fontname="Inter", fontsize=11, style=filled, penwidth=0];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    subgraph cluster_platform {
        label="Aither Platform";
        fontcolor="#818cf8";
        color="#4f46e5";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];

        bff [label="BFF (Portal)\nPOST /api-keys\n🆕 → vault_create_key()", fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
        gw [label="Gateway (K8s)\n_check_jwt()\n🆕 → vault_validate_key()", fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
        
        cache [label="Redis\nvault:key:*\nTTL=60s", shape=cylinder, fillcolor="#fbbf2410", color="#fbbf24", fontcolor="#fbbf24"];
        pg_local [label="PostgreSQL\nportal_api_keys\n(локальный кэш)", shape=cylinder, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
    }

    subgraph cluster_vault {
        label="🆕 Корпоративный Vault";
        fontcolor="#fbbf24";
        color="#fbbf24";
        bgcolor="#13131a";
        style="bold";

        node [fillcolor="#fbbf2410", color="#fbbf24", fontcolor="#fbbf24"];

        pki [label="PKI Engine\naither-pki\nissue api-key", shape=box];
        kv [label="KV Store\nsecret/aither/keys\nkey metadata + policies", shape=box];
        pol [label="Security Policies\nmax_rpm/max_tpm\nmodels/ip_whitelist\nexpires_at", shape=note, fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    }

    bff -> pki [label="create", color="#fbbf24"];
    pki -> kv [label="store", color="#fbbf24"];
    pol -> kv [label="attach", color="#f87171"];
    
    gw -> cache [label="1. check cache", color="#fbbf24"];
    gw -> kv [label="2. miss → Vault", color="#fbbf24"];
    gw -> pg_local [label="3. fallback", color="#34d399", style="dashed"];
    kv -> cache [label="cache 60s", color="#fbbf24"];
    
    bff -> pg_local [label="cache key", color="#34d399", style="dashed"];
}
```

## Поток создания и валидации ключа

```dot
digraph KeyFlow {
    rankdir=TB;
    bgcolor="#0a0a0f";
    fontname="Inter";

    node [fontname="Inter", fontsize=10, style=filled, penwidth=0, shape=box];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    subgraph cluster_create {
        label="Создание ключа (BFF)";
        fontcolor="#818cf8";
        color="#4f46e5";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
        
        c1 [label="POST /org/:id/api-keys\nowner + org_id", shape=box];
        c2 [label="🆕 vault_create_api_key()\nPOST /v1/aither-pki/issue", shape=box, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        c3 [label="Vault PKI\n→ serial + cert + policies", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        c4 [label="ak-<SHA256(serial)>\nprefix: ak-XXXXXXXXXX", shape=box, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
        c5 [label="Кэшировать в PG\nportal_api_keys\n+ policies metadata", shape=cylinder, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
    }

    subgraph cluster_validate {
        label="Валидация при запросе (Gateway)";
        fontcolor="#34d399";
        color="#34d399";
        bgcolor="#13131a";

        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];
        
        v1 [label="Authorization: Bearer ak-...", shape=box];
        v2 [label="🆕 vault_validate_key()\n1. Redis cache (60s)?", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        v3 [label="2. Vault KV GET\nsecret/aither/keys/...", shape=box, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        v4 [label="3. Fallback PG\nportal_api_keys", shape=box, fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
        v5 [label="✅ Valid → apply policies\nmax_rpm, allowed_models, ...", shape=box, fillcolor="#6366f120", color="#6366f1", fontcolor="#818cf8"];
        v6 [label="❌ Invalid → 401", shape=box, fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];
    }

    c1 -> c2 -> c3 -> c4 -> c5;
    v1 -> v2;
    v2 -> v5 [label="hit"];
    v2 -> v3 [label="miss"];
    v3 -> v5 [label="valid"];
    v3 -> v4 [label="not found"];
    v4 -> v5 [label="found"];
    v4 -> v6 [label="not found"];
}
```

## Политики ИБ → Rate Limiting

```dot
digraph PolicyFlow {
    rankdir=LR;
    bgcolor="#0a0a0f";
    fontname="Inter";

    node [fontname="Inter", fontsize=10, style=filled, penwidth=0, shape=box];
    edge [fontname="Inter", fontsize=9, color="#71718a"];

    vault_pol [label="Vault Policies\n{\n  max_rpm: 60\n  max_tpm: 100000\n  allowed_models: [14b,32b]\n  ip_whitelist: [10.0.0.0/8]\n}", shape=note, fillcolor="#fbbf2410", color="#fbbf24", fontcolor="#fbbf24"];

    subgraph cluster_gw {
        label="Gateway Enforcement";
        color="#34d399";
        bgcolor="#13131a";
        node [fillcolor="#1a1a24", color="#1f1f2e", fontcolor="#e4e4ec"];

        rpm [label="Rate Limiter\nRPM < max_rpm?", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        tpm [label="Rate Limiter\nTPM < max_tpm?", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        model [label="Model Access\nmodel in\nallowed_models?", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        ip [label="IP Restriction\nsource_ip in\nip_whitelist?", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
        expiry [label="Expiry Check\nnow < expires_at?", shape=diamond, fillcolor="#fbbf2420", color="#fbbf24", fontcolor="#fbbf24"];
    }

    result_ok [label="✅ Allow", fillcolor="#34d39915", color="#34d399", fontcolor="#34d399"];
    result_block [label="❌ Block", fillcolor="#f8717120", color="#f87171", fontcolor="#f87171"];

    vault_pol -> rpm;
    rpm -> result_block [label="exceeded"];
    rpm -> tpm [label="ok"];
    tpm -> result_block [label="exceeded"];
    tpm -> model [label="ok"];
    model -> result_block [label="not allowed"];
    model -> ip [label="ok"];
    ip -> result_block [label="restricted"];
    ip -> expiry [label="ok"];
    expiry -> result_block [label="expired"];
    expiry -> result_ok [label="ok"];
}
```

## Ключевые функции vault.py

| Функция | Назначение | Кто вызывает |
|---|---|---|
| `vault_create_api_key()` | Выпуск ключа через Vault PKI | BFF (Portal) |
| `vault_validate_key()` | Проверка ключа + возврат политик | Gateway (_check_jwt) |
| `vault_revoke_key()` | Отзыв ключа в Vault | BFF (Portal) |
| `vault_health()` | Проверка связности с Vault | Health check |

## Режимы работы

| Режим | `VAULT_ENABLED` | Поведение |
|---|---|---|
| **Production** | `true` | Vault → Redis cache (60s) → PostgreSQL fallback |
| **Development** | `false` | Только PostgreSQL (текущее поведение) |

## Конфигурация (env vars)

| Переменная | По умолчанию |
|---|---|
| `VAULT_ENABLED` | true |
| `VAULT_ADDR` | http://vault:8200 |
| `VAULT_TOKEN` | (обязательно) |
| `VAULT_PKI_PATH` | aither-pki |
| `VAULT_PKI_ROLE` | api-key |
| `VAULT_TIMEOUT` | 5 |
