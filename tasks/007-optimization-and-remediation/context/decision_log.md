# Decision Log - Task 007

This document records major decisions made during Task 007 execution in chronological order.

---

## 2025-10-14: Task 007 Scope Defined

**Decision**: Focus on optimization (performance, cost, prompts, LLM selection) and LocalOrchestrator production hardening; explicitly exclude watsonx.orchestrate migration per user preference.

**Rationale**: User feedback: "I still prefer to focus on a utilizing a local orchestrator and will migrate to orchestrate at a later time." Additionally, Anthropic guidance (E-007-003) validates simple, composable patterns over complex frameworks.

**Impact**: Task duration 17-22 hours (achievable); LocalOrchestrator hardening prioritized as Phase 4 (HIGH); watsonx.orchestrate migration deferred to future task.

**Reference**: User request for limitation remediation from Tasks 001-006; hypothesis.md "Out of Scope" section; ADR-007-005

---

## 2025-10-14: Context Scaffolding Complete

**Decision**: Created all 11 required context files per SCA v9-Compact protocol before starting implementation.

**Files Created**:
- hypothesis.md (5 metrics, statistical tests, baselines, targets, success criteria)
- design.md (7 phases with code examples, architecture diagrams, commit strategy)
- evidence.json (8 sources: 6 P1, 2 P2, 18 quotes ≤25 words)
- data_sources.json (6 inputs, 9 outputs, 6 transformations with SHA256 checksums)
- adr.md (9 ADRs covering monitoring, prompts, LocalOrchestrator, statistical validation)
- risks.md (10 risks with mitigation strategies and contingency plans)
- assumptions.md (18 assumptions with validation checklist across 7 categories)
- glossary.md (35+ terms across 8 categories: monitoring, prompts, LLM, stats, orchestration)
- executive_summary.md (1-page task overview with metrics table, phase summary, risks)
- context_map.md (navigation guide with reading paths, file relationships, search tips)
- decision_log.md (this file)

**Rationale**: SCA protocol requires comprehensive context before coding to ensure evidence-based, scientifically rigorous implementation.

**Impact**: Phase 0 complete (100% of context files created). Ready to proceed to Phase 1 (Instrumentation & Monitoring).

**Reference**: SCA v9-Compact protocol; context_map.md for file relationships

---

## 2025-10-14: Statistical Validation Strategy Defined

**Decision**: Use paired t-tests (α=0.05, n=20) for latency, cost, and semantic similarity comparisons; binomial test for LocalOrchestrator accuracy.

**Rationale**:
- Paired design controls for query difficulty (each query is its own control), maximizing statistical power
- Large effect sizes (40% latency improvement, 20% cost reduction) are detectable with n=20
- Binomial test is appropriate for binary outcomes (term extraction success/failure)

**Impact**: Clear validation criteria for all 5 metrics; scientifically rigorous results; power analysis confirms n=20 is adequate.

**Reference**: ADR-007-008 (Paired t-Tests); hypothesis.md (Metric 1-5 validation); assumptions.md (ASSUME-007-013, ASSUME-007-014)

---

## 2025-10-14: LocalOrchestrator Production Hardening Prioritized

**Decision**: Elevate LocalOrchestrator hardening to HIGH priority Phase 4 (previously MEDIUM priority in initial plan draft).

**Rationale**:
- User explicitly prefers LocalOrchestrator over watsonx.orchestrate migration
- Anthropic best practices (E-007-003) validate simple orchestrator approach
- Current implementation is proof-of-concept (121 NLOC, only 5 test cases)
- Production readiness (error handling, retry logic, telemetry) is critical for user-facing feature

**Impact**: Phase 4 allocated 2-3 hours; targets ≥90% term extraction accuracy on 20 test queries, graceful error handling, ≥90% branch coverage.

**Reference**: ADR-007-005 (LocalOrchestrator vs watsonx.orchestrate); design.md Phase 4; hypothesis.md Metric 3

---

## 2025-10-14: Monitoring Architecture Selected (Singleton + MELT)

**Decision**: Implement singleton MetricsCollector with MELT-inspired design (Metrics, Events, Logs, no Traces).

**Rationale**:
- Singleton provides global access without dependency injection complexity
- MELT framework (E-007-004) is industry best practice for LLM observability
- Traces (distributed tracing) are overhead for single-process system; defer to future
- Thread-safe queue + async file writing minimizes instrumentation overhead (<5ms target)

**Impact**: Phase 1 implementation clear; metrics logged to separate JSON files per type (latency, cost, cache, orchestrator).

**Reference**: ADR-007-001 (Singleton MetricsCollector); design.md Phase 1; evidence.json E-007-004

---

## 2025-10-14: Prompt Template System with Versioning Chosen

**Decision**: Create code-based prompt library (services/prompts/) with `PromptTemplate` base class and versioned subclasses.

**Rationale**:
- Code-based templates are version-controlled (git diff shows prompt changes clearly)
- Versioning (V1, V2, ...) enables A/B testing and rollback if prompts regress
- Template classes (ChainOfThoughtPrompt, FewShotPrompt) document best practices
- Simpler than external file storage (YAML/JSON) or prompt management service (LangChain Hub)

**Impact**: Phase 3 creates services/prompts/ module; maintains baseline prompts for comparison; enables incremental prompt validation.

**Reference**: ADR-007-004 (Prompt Template System); design.md Phase 3; evidence.json E-007-001, E-007-005

---

## 2025-10-14: Model Selection Criteria Defined (Cost OR Accuracy)

**Decision**: Benchmark granite-13b-instruct-v2 vs granite-3-3-8b-instruct; select model achieving **20% cost reduction OR 10% accuracy improvement** (not both required).

**Rationale**:
- OR condition allows flexibility: either outcome is valuable
- 20% cost reduction = ~$20-50/month savings (measurable impact)
- 10% accuracy improvement = significant user-facing benefit
- Hard requirement: ≥95% E2E test pass rate maintained (no functional regressions)

**Impact**: Phase 2 runs 20 test queries on both models; measures latency, cost (tokens × price), semantic similarity; documents decision in model_benchmark_results.json.

**Reference**: ADR-007-003 (Cost-Performance Trade-off); hypothesis.md Metric 2; evidence.json E-007-002, E-007-006

---

## 2025-10-14: Risk Prioritization Established

**Decision**: Identify 3 critical/high risks requiring immediate attention:
1. **RISK-007-002** (Prompt optimization regression) - MEDIUM likelihood, HIGH impact
2. **RISK-007-005** (Time overrun) - MEDIUM likelihood, MEDIUM impact
3. **RISK-007-007** (Cache invalidation bugs) - MEDIUM likelihood, MEDIUM impact

**Rationale**:
- Prompt regression could break E2E tests (hard requirement: ≥95% pass rate)
- Time overrun could force scope reduction (17-22 hour estimate may be insufficient)
- Cache bugs could cause incorrect responses (hard to debug, user-facing impact)

**Impact**:
- Prompt regression: Maintain baseline prompts (V1) for rollback, test incrementally on subset
- Time overrun: Prioritize HIGH phases (1-4), defer MEDIUM phases (5-6) if needed
- Cache bugs: Comprehensive cache key (query, context_hash, prompt, temperature, max_new_tokens), TTL, logging

**Reference**: risks.md (10 risks documented); hypothesis.md (risk mitigation table)

---

## 2025-10-14: Evidence Base Established (8 Sources)

**Decision**: Selected 8 research sources (6 P1, 2 P2) to support optimization strategies:
- **E-007-001**: Chain-of-thought prompting (arXiv, Wei et al.) - validates CoT but warns granite-13b may be too small
- **E-007-002**: LLM cost optimization (arXiv) - validates benchmarking approach
- **E-007-003**: Building effective agents (Anthropic) - validates LocalOrchestrator over complex frameworks
- **E-007-004**: LLM observability with OpenTelemetry - validates MELT framework
- **E-007-005**: Few-shot prompting (promptingguide.ai) - validates structured output approach
- **E-007-006**: LLM cost management (Symflower) - validates 30x price differences, smaller models
- **E-007-007**: LangGraph workflows (P2) - validates workflow vs agent patterns
- **E-007-008**: SigNoz LLM observability (P2) - validates early instrumentation integration

**Rationale**: All 5 metrics have ≥1 P1 source; quotes ≤25 words (protocol requirement); retrieval date 2025-10-14 (current).

**Impact**: Evidence-based validation for all design decisions; citations available for ADRs.

**Reference**: evidence.json (8 sources documented); adr.md (ADRs cite evidence)

---

## Template for Future Decisions

<!--
## YYYY-MM-DD: [Decision Title]

**Decision**: [What was decided]

**Rationale**: [Why this decision was made]

**Impact**: [What changed as a result]

**Reference**: [Links to related context files, ADRs, or evidence]

---
-->

---

**Next Phase**: Phase 1 - Instrumentation & Monitoring
**Next Actions**:
1. Validate assumptions (ASSUME-007-001 through ASSUME-007-006) before starting Phase 1
2. Create `services/monitoring/` module (MetricsCollector, LatencyTracker, CostTracker)
3. Integrate instrumentation into workflow.py, generation.py, local_orchestrator.py
4. Run E2E tests to verify no functional regressions from instrumentation
5. Commit Phase 1 changes: "feat: Add monitoring infrastructure (Task 007 Phase 1)"

---

**Last Updated**: 2025-10-14
**Phase 0 Status**: ✅ Complete (11/11 context files created)
