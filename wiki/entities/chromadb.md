---
title: ChromaDB
created: 2026-07-09
updated: 2026-07-09
type: entity
tags: [rag, models, architecture]
sources: []
---

# ChromaDB

Векторная база данных для RAG-подсистемы Aither. Хранит эмбеддинги
документов и страниц [[LLM-Wiki]].

## Конфигурация

- Развёрнута в K8s на n7 (worker)
- Persistence: hostPath `/data/chromadb`
- Версия: 0.6.3
- Коллекция: `documents`

## Embeddings

Используются две модели эмбеддингов:

1. **ONNX MiniLM-L6-V2** (встроенная в ChromaDB) — быстрая, локальная,
   используется [[AI Gateway]] для векторного RAG
2. **multilingual-e5-large** (отдельный сервис `embeddings:8001`) —
   мультиязычная, для высокоточного семантического поиска

## Гибридный RAG

[[LLM-Wiki]] страницы индексируются в ChromaDB через `/v1/rag/wiki-ingest`.
Гибридный запрос (`/v1/rag/hybrid-query`) комбинирует:

1. Векторный поиск ChromaDB (семантическая близость)
2. Обход графа [[LLM-Wiki]] (концептуальные связи через `[[wikilinks]]`)

Результаты сливаются и переранжируются: vector_score × 0.6 + wiki_score × 0.4.
