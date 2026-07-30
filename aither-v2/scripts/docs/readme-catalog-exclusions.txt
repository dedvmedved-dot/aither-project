# README Catalog Exclusions
# Each line is either an exact path, a glob pattern, or a directory prefix (ending with /).
# Lines starting with # are comments.

# --- Binary documents (Word) — described as group "RAG Docs" ---
services/portal-backend/rag-docs/Aither_textbook_5_volumes_NATIVE_LAYOUT/*

# --- SVG diagram — described with .dot source ---
services/portal-backend/rag-docs/diagrams/aither-2026-topology.svg

# --- Placeholder directories ---
04-tensor-parallelism/.gitkeep
05-gateway-redis/.gitkeep
06-portal-spa-bff-sse/.gitkeep
07-oauth/.gitkeep
services/bff/app/.gitkeep
services/portal/src/.gitkeep
tools/benchmarks/.gitkeep

# --- Bulk evidence directories (documented at directory level in catalog) ---
evidence/*
docs/evidence/*
docs/mvp-roadmap/*/evidence/*
docs/mvp-roadmap/*/logs/*
docs/mvp-roadmap/*/integrity/*
manifests/mvp-roadmap/*/.gitkeep
release/mvp-rc1/*/.gitkeep
scripts/mvp/.gitkeep
reports/*
reports/*/*
docs/mvp-roadmap/*/*/.gitkeep

# --- Tools (deprecated) — documented at directory level ---
tools/bff/*
tools/portal/*
tools/benchmarks/*

# --- Deploy scripts — documented at directory level ---
deploy/*
deploy/*/*

# --- Reports, docs, manifests bulk (documented at directory level) ---
docs/mvp-roadmap/*/evidence/*

# --- Planned directories (not yet created) ---
scripts/ops/*
scripts/security/*
tests/*
