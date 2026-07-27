# CHANGE-0022-C3 R7-R5-EMG-GW-R5 — Section 5: Gateway Authentication Fix

## Date
2026-07-27

## File Modified
`gateway/auth.py` — полная переработка (116 → 267 строк)

## Что сделано

### AuthResult dataclass — добавлены поля
- `scopes: list[str]` — список scope'ов из JWT/API key
- `role: str` — роль (admin/user)
- `jti: str` — JWT ID
- `credential_id: str` — идентификатор credential
- `credential_type: str` — тип: "jwt_delegation" | "api_key" | "vault_key"

### JWT RS256 validation — полная проверка ВСЕХ обязательных claim'ов
- `MANDATORY_CLAIMS` = [iss, aud, sub, org_id, user_id, tier, scopes, jti, iat, nbf, exp]
- `pyjwt.decode()` с `options={"verify_exp": True, "verify_iss": True, "verify_aud": True, "verify_iat": True, "verify_nbf": True, "require": MANDATORY_CLAIMS}`
- Audience: `"aither-gateway"` — ОБЯЗАТЕЛЬНО (не опционально)
- Issuer: `settings.jwt_issuer or "aither-bff"` — проверяется pyjwt
- Каждый тип ошибки — отдельный except (ExpiredSignatureError, ImmatureSignatureError, MissingRequiredClaimError, InvalidIssuerError, InvalidAudienceError)
- Post-decode double-check: все mandatory claims должны присутствовать
- Double-check audience: "aither-gateway" должен быть в aud (строка или список)

### API key validation — полная миграция на hash-only
- **REMOVED**: raw-token fallback (`"Fallback: try raw token"`)
- Только hash lookup (`SHA-256(raw_token)`)
- Проверки:
  - `key_status == "revoked"` → 401
  - `key_status != "active"` → 401
  - `expires_at` проверка (ISO-строка или timestamp)
  - `user_status != "active"` → 401
  - `org_status != "active"` → 401
- Model scopes из `portal_api_keys.model_scopes`
- RAG scopes из `portal_api_keys.rag_scopes`
- `last_used_at` обновление через `now()`
- DB-ошибка → fail-closed (`reason="db_error"`)

### Что удалено
- Строки 88-97 старого `auth.py`: raw-token fallback lookup
- Audience optional check (`if aud and "aither-gateway" not in str(aud)`) — заменён на mandatory
- Все `except: pass` — заменены на конкретные exception handlers

### Верификация
```bash
cd /root/aither-project-r7-canonical
python3 -c "
import ast
with open('gateway/auth.py') as f: code = f.read()
ast.parse(code)
print('AST parse OK, lines:', len(code.splitlines()))
"
# → AST parse OK, lines: 267
```
