# Agents Charter

## Core Objective
Deliver an AstraDB-backed GraphRAG system that fuses structured, semi-structured, and unstructured subsurface data, supports LangGraph-based reasoning where needed, and demonstrates a lightweight ML training loop.

## Role Definitions

### 1. Data Ingestion Agent
- Responsibilities: harvest EIA XLS, USGS JSON, KGS LAS, and supplemental sources; normalize metadata; log provenance.
- Success Criteria: raw artifacts stored under data/raw, provenance entries recorded, idempotent reruns.
- Guardrails: respect source rate limits, never persist secrets.

### 2. Graph Construction Agent
- Responsibilities: build entity/relationship graph, create community summaries, generate embeddings, load AstraDBVectorStore collections.
- Success Criteria: validated schema snapshots in graphs/snapshots, embeddings registered in Astra, changelog updated.
- Guardrails: verify chunking thresholds, retain prompt versions, fail fast on schema drift.

### 3. Orchestration Agent (LangGraph)
- Responsibilities: design durable workflows for hybrid retrieval (graph + vector + ML scoring), enable human-in-the-loop checkpoints.
- Success Criteria: workflows housed in workflows/langgraph, observability hooks capture run traces, recovery from checkpointed state proved.
- Guardrails: branch only when scripts cannot cover use case, enforce timeout budgets, capture state diffs for review.

### 4. ML Steward
- Responsibilities: engineer features, train & evaluate logistic regression (or similar) models, expose inference services.
- Success Criteria: reproducible training notebooks/scripts, metrics logged in /docs/decisions, model artifacts versioned in models/ml.
- Guardrails: avoid data leakage, document assumptions, surface explainability notes.

## Communication Cadence
- Daily progress notes ? /docs/standups.md (or project tracker).
- Architectural or data decisions ? /docs/decisions/ADR-*.md.
- Escalation hierarchy: Technical blockers ? platform lead; dataset/licensing questions ? data steward; compliance concerns ? project owner.

## Definition of Done
A sprint slice is complete when data provenance is tracked, tests covering the change set pass, documentation is updated, and stakeholders have reviewable artifacts (notebooks, diffs, prompts, model cards).

## Context Management
- Always perform context compacting when the remaining context window space drops below 25%.
