# RAG System Evaluation Framework

## Overview

This evaluation framework provides comprehensive testing and metrics for the GraphRAG system with ground truth validation.

## Components

### 1. Evaluation Dataset (`eval_dataset.json`)

Contains test cases with:
- **Query**: User question to test
- **Expected entities**: Entities that should appear in retrieved context
- **Expected keywords**: Keywords that should appear in the generated answer
- **Ground truth**: Reference answer for comparison
- **Category**: Test category (factual_retrieval, comparison, technical_explanation, etc.)

**Current Dataset**: 8 test cases covering:
- Factual retrieval (3)
- Comparison (1)
- Technical explanation (1)
- Temporal queries (1)
- Geographic queries (1)
- Technical details (1)

### 2. Evaluation Metrics (`metrics.py`)

Implements standard RAG evaluation metrics:

#### Core Metrics

1. **Faithfulness** (0-1)
   - Measures if answer is grounded in retrieved context
   - Formula: % of answer tokens that appear in contexts
   - Higher = better grounding

2. **Answer Relevance** (0-1)
   - Measures relevance of answer to query
   - Formula: Token overlap between query and answer
   - Higher = more relevant

3. **Context Precision** (0-1)
   - Measures if retrieved contexts contain expected entities
   - Formula: % of expected entities found in contexts
   - Higher = better retrieval quality

4. **Context Recall** (0-1)
   - Measures coverage of ground truth by retrieved contexts
   - Formula: Token overlap between contexts and ground truth
   - Higher = more complete context

5. **Keyword Score** (0-1)
   - Checks if answer contains expected keywords
   - Formula: % of expected keywords found in answer
   - Higher = better keyword coverage

6. **Aggregate Score** (0-1)
   - Weighted combination of metrics
   - Weights: faithfulness (0.3), relevance (0.3), precision (0.2), keywords (0.2)

### 3. Evaluation Harness (`run_evaluation.py`)

Automated testing framework that:
- Loads test cases from dataset
- Runs each query through the workflow
- Computes evaluation metrics
- Generates aggregate statistics
- Saves detailed results to JSON

#### Usage

```bash
python tests/evaluation/run_evaluation.py
```

#### Output

- Console: Real-time test progress and metrics
- JSON file: `eval_results_TIMESTAMP.json` with detailed results

### 4. Tracing & Logging (`tracing.py`, `run_with_tracing.py`)

Debug utilities for detailed workflow analysis:

#### Components

- **WorkflowTracer**: Logs each workflow step with timing
- **RetrievalLogger**: Detailed retrieval debugging (embeddings, docs, filters)
- **GenerationLogger**: Generation debugging (prompts, responses, timing)

#### Usage

```bash
python workflows/langgraph/run_with_tracing.py "What well data is in Kansas?" --trace-dir logs
```

#### Output Locations

- `logs/traces/`: Workflow execution traces
- `logs/retrieval/`: Retrieval-specific logs
- `logs/generation/`: Generation-specific logs

## Evaluation Results Interpretation

### Good Performance Thresholds

- **Faithfulness**: > 0.7 (answer is grounded)
- **Answer Relevance**: > 0.5 (answer addresses query)
- **Context Precision**: > 0.6 (good retrieval)
- **Aggregate Score**: > 0.6 (overall good performance)

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Low faithfulness | Answer hallucinates | Improve prompt grounding instructions |
| Low answer relevance | Off-topic generation | Improve retrieval or prompt |
| Low context precision | Poor retrieval | Tune embeddings or reranking |
| Missing keywords | Generation quality | Refine generation prompt |

## Extending the Framework

### Adding New Test Cases

Edit `eval_dataset.json`:

```json
{
  "id": "unique_test_id",
  "query": "Your test question",
  "expected_entities": ["entity1", "entity2"],
  "expected_answer_contains": ["keyword1", "keyword2"],
  "ground_truth": "Reference answer for comparison",
  "category": "factual_retrieval"
}
```

### Custom Metrics

Add new metric functions to `metrics.py`:

```python
def compute_custom_metric(query: str, answer: str, contexts: List[str]) -> float:
    # Your metric logic
    return score
```

Update `evaluate_rag_response()` to include the new metric.

## Best Practices

1. **Run evaluations regularly** after code changes
2. **Track metrics over time** to monitor improvements/regressions
3. **Use tracing** when debugging specific failures
4. **Expand dataset** as new use cases emerge
5. **Set baselines** for acceptable performance thresholds
6. **Context management**: Compact contexts when remaining window space < 25% (recommended threshold: `CONTEXT_COMPACT_THRESHOLD=0.25`).

## Example Workflow

1. Make changes to retrieval/generation code
2. Run evaluation: `python tests/evaluation/run_evaluation.py`
3. Review aggregate metrics and category performance
4. For failures, use tracing: `python workflows/langgraph/run_with_tracing.py "failing query"`
5. Analyze trace logs to identify issues
6. Iterate and re-evaluate

## Output Example

```
EVALUATION SUMMARY
======================================================================

Total tests: 8
Successful: 8
Failed: 0
Success rate: 1.0

Average Metrics:
  faithfulness: 0.723
  answer_relevance: 0.512
  context_precision: 0.667
  aggregate_score: 0.621

Category Performance:
  factual_retrieval: 0.653
  comparison: 0.589
  technical_explanation: 0.612
```
