Relationship Confidence v2

Overview
- The relationship detector now computes a continuous confidence score in [0,1] and returns evidence along with a confidence-aware traversal strategy.
- The workflow uses confidence to dynamically tune retrieval breadth, keyword filtering, traversal aggressiveness, and whether to prefer structured answers over LLM output.

Detector (services/graph_index/relationship_detector.py)
- Score components (capped at 1.0):
  - Pattern match (regex): +0.6
  - Relationship keywords (e.g., "belongs to", "has"): +0.2
  - Entities present (well_id, curve_name, site_id): +0.1 each, up to +0.2
  - Synergy bonus (pattern + keywords): +0.1
- Output includes:
  - confidence: float
  - confidence_evidence: list of reason tags
  - traversal_strategy: { method, expand_direction, edge_type, max_hops, apply_traversal }
    - High (≥0.85): apply_traversal=True, max_hops=2
    - Medium (≥0.6): apply_traversal=True, max_hops=1
    - Low (<0.6): apply_traversal=False

Workflow (services/langgraph/workflow.py)
- Retrieval knobs:
  - top_k default: 30 (high), 15 (medium), 10 (low) unless overridden in metadata
  - Reranker weights: (vector, keyword) = (0.6, 0.4) at high confidence; (0.7, 0.3) otherwise
  - Critical keyword filter: OR at high confidence; AND at lower confidences with a medium-confidence fallback to OR if zero hits
- Well ID handling:
  - We no longer modify filters for well ID up front. Well ID is used for post-filtering and, at high confidence, a targeted `_id` fetch if no results.
- Traversal gating:
  - Controlled by traversal_strategy.apply_traversal and the confidence threshold (≥0.6). Ad-hoc heuristics are removed.
- Structured answers (reasoning step):
  - Enabled for relationship queries when confidence ≥0.7 for robust cases:
    - well_to_curves: deterministically list curve mnemonics
    - curve_to_well: resolve via Traverser to the most likely well
    - curve→document: resolve the parent well and return the LAS document owner
    - relationship COUNT: count curves via Traverser when well ID known, or via expanded docs / semantic tags
- Metadata & tracing:
  - Stores relationship_detection, relationship_confidence, confidence_evidence, and a decision_log of retrieval/traversal choices.

Motivation
- Reduce brittle heuristics by letting the same relationship signal (confidence) modulate how assertive the system is.
- Prefer deterministic, structured responses for well-known relation types at higher confidence, and use LLMs conservatively otherwise.

Future Extensions
- Incorporate early-evidence and graph-evidence boosts (e.g., seed node presence, edge centrality) into confidence.
- Add beam-scored traversal for node expansion to further improve precision.

