# Wiki Schema

## Domain
Платформа Aither — Token-as-a-Service: vLLM-инференс, биллинг, безопасность, мультиарендность.
Документирует архитектуру, компоненты, модели, протоколы, политики безопасности и процедуры эксплуатации.

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `vllm-inference.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
---
```

## Tag Taxonomy
- architecture: gateway, vllm, kubernetes, networking, storage
- security: dlp, vault, siem, auth, pki, policies
- models: qwen, inference, lora, fine-tuning
- billing: tariffs, rates, yookassa, accounting
- operations: deployment, monitoring, backup, troubleshooting
- concepts: rag, wiki, multi-tenant, failover

## Page Thresholds
- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions or minor details
- **Split a page** when it exceeds ~200 lines

## Update Policy
When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Flag for review
