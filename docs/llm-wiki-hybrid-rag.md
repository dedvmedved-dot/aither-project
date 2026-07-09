# LLM-Wiki + гибридный RAG для Aither

**Дата:** 10.07.2026  
**Задача:** #37 дорожной карты  
**Статус:** ✅ Выполнено

---

## Архитектура

Подсистема реализует Karpathy-style knowledge base — персистентный граф
взаимосвязанных Markdown-страниц с гибридным поиском.

```
Запрос → Gateway
           ├── Keyword search (wiki_graph.search)
           ├── Graph expansion (wikilinks, 1-hop)
           ├── Merge + deduplicate
           ├── Re-rank (keyword × 0.7 + wiki-connectivity × 0.3)
           └── Ответ: top_k результатов с соседями по графу
```

```dot
digraph wiki_rag {
    rankdir=TB;
    bgcolor="#ffffff";
    node [fontname="Arial", fontsize=11];

    query [label="Запрос\nпользователя", shape=oval, style=filled, fillcolor="#e3f2fd"];
    gw [label="AI Gateway\n/v1/rag/hybrid-query", shape=box, style=filled, fillcolor="#fff3e0"];
    kw [label="Keyword\nSearch", shape=box, style=filled, fillcolor="#e8f5e9"];
    graph [label="Wiki Graph\n[[wikilinks]]", shape=box, style=filled, fillcolor="#f3e5f5"];
    merge [label="Merge +\nRe-rank", shape=box, style=filled, fillcolor="#fce4ec"];
    result [label="Результаты\n+ соседи", shape=oval, style=filled, fillcolor="#e3f2fd"];

    query -> gw;
    gw -> kw;
    kw -> graph;
    kw -> merge;
    graph -> merge;
    merge -> result;
    result -> gw;
}
```

## Компоненты

### 1. Wiki-граф (`wiki/`)

8 страниц знаний о платформе Aither с перекрёстными `[[wikilinks]]`:

| Страница | Тип | Связей |
|---|---|---|
| AI Gateway | entity | 10 out, → Vault, Security, SIEM, vLLM... |
| vLLM Inference | entity | 9 out |
| Multi-Tenant Architecture | concept | 8 out |
| Security Egress | entity | 4 out |
| SIEM Integration | entity | 4 out |
| ChromaDB | entity | 3 out |
| LLM-Wiki | concept | 3 out |
| Vault PKI | entity | 1 out |

### 2. Wiki Graph Engine (`gateway/wiki_graph.py`)

- Парсинг YAML frontmatter
- Извлечение `[[wikilinks]]`
- Индексация: прямые и обратные ссылки
- BFS-обход графа (radius N)
- Полнотекстовый поиск по заголовкам/тегам/контенту
- Поддержка иерархической (`entities/`, `concepts/`) и плоской (ConfigMap) структуры

### 3. Hybrid RAG Engine (`gateway/hybrid_rag.py`)

Алгоритм гибридного запроса:

1. **Keyword search** — полнотекстовый поиск по wiki-страницам
2. **Graph expansion** — 1-hop обход через `[[wikilinks]]`
3. **Merge** — дедупликация по slug
4. **Re-rank** — `keyword_score × 0.7 + wiki_score × 0.3`
5. **Graph-only fill** — если результатов меньше top_k, добираем из соседей по графу

### Wiki Score

```python
wiki_score = min(0.3 + 0.15 × inlink_count, 1.0)
```

Страницы с большим числом входящих ссылок получают более высокий вес.

## API эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| POST | `/v1/rag/hybrid-query` | Гибридный поиск (keyword + graph) |
| POST | `/v1/rag/wiki-ingest` | Перезагрузка wiki-графа с диска |
| GET | `/v1/rag/status` | Статус wiki + RAG |

### Пример запроса

```json
POST /v1/rag/hybrid-query
{
  "query": "как работает безопасность и фильтрация",
  "top_k": 3,
  "wiki_radius": 1
}
```

### Пример ответа

```json
{
  "query": "как работает безопасность и фильтрация",
  "results": [
    {
      "id": "wiki:ai-gateway",
      "text": "Центральный компонент платформы Aither...",
      "page_title": "AI Gateway",
      "page_type": "entity",
      "tags": ["gateway", "architecture", "security"],
      "score": 0.7025,
      "keyword_score": 0.875,
      "wiki_score": 0.3,
      "inlinks": 0,
      "neighbors": ["Vault PKI", "Security Egress", "SIEM Integration"]
    }
  ],
  "mode": "hybrid"
}
```

## Интеграция с Gateway

Gateway (`gateway.py`) загружает wiki-граф при старте:

```
[Init] Loading wiki graph...
[Init] Wiki graph loaded: 8 pages
Gateway listening on :8080
```

Запросы к `/v1/rag/*` проходят JWT/API-key аутентификацию
и проверку tier-доступа (`rag_enabled`).

## Отличия от традиционного RAG

| Аспект | Традиционный RAG | LLM-Wiki RAG |
|---|---|---|
| Хранение | Векторная БД | Markdown + граф |
| Поиск | Cosine similarity | Keyword + wikilinks |
| Связи | Нет (только близость) | Явные `[[wikilinks]]` |
| Обновление | Реиндексация всей БД | Редактирование .md файла |
| Зависимости | Embedding model, vector DB | Нет (pure Python) |
| Объяснимость | «Ближайший вектор» | «Связано через wikilink» |

## Планы развития

- 🔜 Интеграция с векторным поиском (когда ChromaDB будет стабилен)
- 🔜 Наполнение wiki документацией, SOP, troubleshooting
- 🔜 Авто-обновление wiki из CI/CD артефактов
- 🔜 Multi-hop reasoning (radius > 1)
