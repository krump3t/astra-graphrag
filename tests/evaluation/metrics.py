"""RAG evaluation metrics for assessing retrieval and generation quality."""
import re
from typing import List, Dict, Any, Tuple


def compute_token_overlap(text1: str, text2: str) -> float:
    """Compute normalized token overlap between two texts."""
    tokens1 = set(re.findall(r'\w+', text1.lower()))
    tokens2 = set(re.findall(r'\w+', text2.lower()))

    if not tokens1 or not tokens2:
        return 0.0

    overlap = tokens1.intersection(tokens2)
    return len(overlap) / max(len(tokens1), len(tokens2))


def compute_faithfulness(answer: str, retrieved_contexts: List[str]) -> float:
    """
    Measure if the answer is grounded in the retrieved context.

    Faithfulness score = % of answer tokens that appear in retrieved contexts
    """
    if not answer or not retrieved_contexts:
        return 0.0

    answer_tokens = set(re.findall(r'\w+', answer.lower()))
    if not answer_tokens:
        return 0.0

    # Build context token set
    context_text = " ".join(retrieved_contexts)
    context_tokens = set(re.findall(r'\w+', context_text.lower()))

    # Calculate grounded tokens
    grounded = answer_tokens.intersection(context_tokens)
    return len(grounded) / len(answer_tokens)


def compute_answer_relevance(query: str, answer: str) -> float:
    """
    Measure how relevant the answer is to the query.

    Simple token overlap between query and answer.
    """
    return compute_token_overlap(query, answer)


def compute_context_precision(
    query: str,
    retrieved_contexts: List[str],
    expected_entities: List[str]
) -> float:
    """
    Measure if retrieved contexts contain expected entities.

    Precision = % of expected entities found in contexts
    """
    if not expected_entities:
        return 1.0  # No expectations, perfect by default

    context_text = " ".join(retrieved_contexts).lower()

    found_entities = sum(
        1 for entity in expected_entities
        if entity.lower() in context_text
    )

    return found_entities / len(expected_entities)


def compute_context_recall(
    retrieved_contexts: List[str],
    ground_truth: str
) -> float:
    """
    Measure how much of the ground truth is covered by retrieved contexts.

    Recall = token overlap between contexts and ground truth
    """
    if not retrieved_contexts or not ground_truth:
        return 0.0

    context_text = " ".join(retrieved_contexts)
    return compute_token_overlap(context_text, ground_truth)


def check_answer_contains(answer: str, expected_keywords: List[str]) -> Tuple[float, List[str]]:
    """
    Check if answer contains expected keywords.

    Returns:
        (score, missing_keywords) where score is fraction of keywords found
    """
    if not expected_keywords:
        return 1.0, []

    answer_lower = answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    missing = [kw for kw in expected_keywords if kw.lower() not in answer_lower]

    return len(found) / len(expected_keywords), missing


def evaluate_rag_response(
    query: str,
    answer: str,
    retrieved_contexts: List[str],
    ground_truth: str = "",
    expected_entities: List[str] = None,
    expected_keywords: List[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive evaluation of a RAG system response.

    Returns:
        Dictionary containing all evaluation metrics and diagnostic info
    """
    expected_entities = expected_entities or []
    expected_keywords = expected_keywords or []

    # Core RAG metrics
    faithfulness = compute_faithfulness(answer, retrieved_contexts)
    answer_relevance = compute_answer_relevance(query, answer)
    context_precision = compute_context_precision(query, retrieved_contexts, expected_entities)

    # Optional ground truth metrics
    context_recall = compute_context_recall(retrieved_contexts, ground_truth) if ground_truth else None
    ground_truth_overlap = compute_token_overlap(answer, ground_truth) if ground_truth else None

    # Keyword checks
    keyword_score, missing_keywords = check_answer_contains(answer, expected_keywords)

    # Aggregate score (weighted average)
    weights = {
        "faithfulness": 0.3,
        "answer_relevance": 0.3,
        "context_precision": 0.2,
        "keyword_score": 0.2
    }

    aggregate = (
        weights["faithfulness"] * faithfulness +
        weights["answer_relevance"] * answer_relevance +
        weights["context_precision"] * context_precision +
        weights["keyword_score"] * keyword_score
    )

    return {
        "metrics": {
            "faithfulness": round(faithfulness, 3),
            "answer_relevance": round(answer_relevance, 3),
            "context_precision": round(context_precision, 3),
            "context_recall": round(context_recall, 3) if context_recall is not None else None,
            "ground_truth_overlap": round(ground_truth_overlap, 3) if ground_truth_overlap is not None else None,
            "keyword_score": round(keyword_score, 3),
            "aggregate_score": round(aggregate, 3)
        },
        "diagnostics": {
            "num_contexts": len(retrieved_contexts),
            "answer_length": len(answer.split()),
            "missing_keywords": missing_keywords,
            "expected_entities_found": f"{int(context_precision * len(expected_entities))}/{len(expected_entities)}" if expected_entities else "N/A"
        }
    }
