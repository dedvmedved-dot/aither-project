# Aither — User Acceptance Checklist

**Version:** v1.0  
**Date:** 2026-07-23  
**Document:** `docs/user-acceptance.md`

---

## Overview

This checklist covers all required user-facing functionality of Aither AI Platform Beta v0.9 / Production v1.0. Each item must be verified before accepting the release.

---

## 1. Installation & Setup

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 1.1 | Git clone repository | `git clone https://github.com/dedvmedved-dot/aither-project.git` | Repository cloned successfully |
| 1.2 | Branch checkout | `git checkout aither-v2` | Switched to branch aither-v2 |
| 1.3 | Cluster connectivity | `kubectl get nodes` | 2 nodes Ready |
| 1.4 | Namespace exists | `kubectl get ns aither-inference` | Namespace exists |
| 1.5 | All pods running | `kubectl get pods -n aither-inference` | 11/11 pods Running |
| 1.6 | Registry accessible | `curl http://10.129.13.78:5000/v2/_catalog` | Returns repository list |

## 2. Launch & Health

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 2.1 | Portal Frontend accessible | Via browser: `http://<portal-clusterip>:80` | Login page loads |
| 2.2 | Portal Backend health | `GET /health` | `{"status":"ok"}` |
| 2.3 | AI Platform health | `GET /health` | `{"status":"ok"}` |
| 2.4 | Identity health | `GET /health` | `{"status":"ok"}` |
| 2.5 | Gateway health | `GET /health` | HTTP 200 |
| 2.6 | Gateway ready | `GET /ready` | HTTP 200 |
| 2.7 | Gateway version | `GET /version` | `{"service":"nginx-gateway-32b"}` |

## 3. Authorization

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 3.1 | Login with valid credentials | `POST /api/v1/auth/login` with `admin/admin` | HTTP 200, JWT token returned |
| 3.2 | Login with wrong password | `POST /api/v1/auth/login` with `admin/wrong` | HTTP 401 |
| 3.3 | Login with nonexistent user | `POST /api/v1/auth/login` with `nobody/test` | HTTP 401 |
| 3.4 | Get current user info | `GET /api/v1/auth/me` with valid token | User details returned |
| 3.5 | Access without token | `GET /api/v1/models` without Authorization | HTTP 401 |
| 3.6 | Logout | `POST /api/v1/auth/logout` | HTTP 200 |

## 4. API Key Management

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 4.1 | Create API Key | `POST /api/v1/api-keys` with name | HTTP 201, full key returned |
| 4.2 | List API Keys | `GET /api/v1/api-keys` | HTTP 200, key prefixes only |
| 4.3 | Revoke API Key | `DELETE /api/v1/api-keys/{id}` | HTTP 200 |
| 4.4 | Use API Key | `POST /v1/chat/completions` with `Authorization: Bearer <key>` | HTTP 200 |
| 4.5 | Use revoked key | Same as 4.4 with revoked key | HTTP 401 |
| 4.6 | X-API-Key header | `POST /v1/chat/completions` with `X-API-Key: <key>` | HTTP 200 |
| 4.7 | API Key isolation | User B cannot see User A's keys | Key list is user-scoped |

## 5. Chat Functionality

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 5.1 | List conversations | `GET /api/v1/conversations` | HTTP 200, array |
| 5.2 | Create conversation | `POST /api/v1/conversations` with title | HTTP 201, conversation ID |
| 5.3 | Get conversation | `GET /api/v1/conversations/{id}` | HTTP 200, messages array |
| 5.4 | Send message | `POST /api/v1/conversations/{id}/messages` with content | HTTP 200, AI response |
| 5.5 | Delete conversation | `DELETE /api/v1/conversations/{id}` | HTTP 200 |
| 5.6 | Delete non-existent conversation | `DELETE /api/v1/conversations/99999` | HTTP 404 |
| 5.7 | Assistant list | `GET /api/v1/assistants` | HTTP 200 |
| 5.8 | Create assistant | `POST /api/v1/assistants` with model_id | HTTP 201 |

## 6. OpenAI API Compatibility

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 6.1 | List models (OpenAI format) | `GET /v1/models` with API Key | HTTP 200 |
| 6.2 | Chat completions | `POST /v1/chat/completions` OpenAI format | HTTP 200 |
| 6.3 | Model parameter | `model: "qwen-32b-gptq"` | Accepted |
| 6.4 | Messages parameter | `messages: [{"role":"user","content":"Hi"}]` | Accepted |
| 6.5 | Temperature parameter | `temperature: 0.7` | Accepted |
| 6.6 | max_tokens parameter | `max_tokens: 100` | Accepted |
| 6.7 | stream parameter | `stream: false` | Accepted (true not supported) |
| 6.8 | Invalid model | `model: "nonexistent"` | HTTP 404 |
| 6.9 | Invalid API Key | Wrong key format | HTTP 401 |
| 6.10 | Empty messages | `messages: []` | HTTP 400/422 |

## 7. Chat Persistence

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 7.1 | Messages persist after page refresh | Refresh browser, reopen conversation | All messages visible |
| 7.2 | Messages persist after logout/login | Logout → Login → Open conversation | All messages visible |
| 7.3 | Multiple conversations | Create 3+ conversations | All listed |
| 7.4 | Conversation isolation | Different users see different conversations | User-scoped |

## 8. Backup & Restore

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 8.1 | Backup script exists | `ls scripts/backup.sh` | File exists |
| 8.2 | Backup executes | `bash scripts/backup.sh` | SQL dump created |
| 8.3 | Restore script exists | `ls scripts/restore.sh` | File exists |
| 8.4 | Backup contains data | Check SQL file has INSERT statements | Data present |

## 9. Update

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 9.1 | Git pull | `git pull origin aither-v2` | Latest code |
| 9.2 | Image rebuild | `docker build -t <tag> .` | Image built |
| 9.3 | Image push | `docker push <registry>/<image>:<tag>` | Image pushed |
| 9.4 | Rolling update | `kubectl set image deployment/...` | Pods updated gracefully |

## 10. Recovery

| # | Check | Method | Expected Result |
|---|-------|--------|-----------------|
| 10.1 | Pod restart recovery | Delete a pod | Pod recreates automatically |
| 10.2 | Service recovery | Wait after pod restart | Health check passes |
| 10.3 | Data persistence | Check data after restart | SQLite on PVC intact |

---

## User Acceptance Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Technical Architect | ChatGPT | — | — |
| Implementation | Hermes + DeepSeek | 2026-07-23 | ✅ |
| Pilot User | — | — | — |
| Release Manager | — | — | — |
