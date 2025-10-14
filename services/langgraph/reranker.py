"""Result reranking utilities for improving retrieval quality."""
from typing import List
import re


def compute_keyword_score(query: str, text: str) -> float:
    """Compute keyword overlap score between query and text."""
    query_tokens = set(re.findall(r'\w+', query.lower()))
    text_tokens = set(re.findall(r'\w+', text.lower()))

    if not query_tokens:
        return 0.0

    overlap = query_tokens.intersection(text_tokens)
    return len(overlap) / len(query_tokens)


def rerank_results(
    query: str,
    documents: List[dict],
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    top_k: int = 5
) -> List[dict]:
    """
    Rerank retrieved documents using hybrid scoring.

    Args:
        query: User query string
        documents: List of documents from vector search (assumed pre-ranked by similarity)
        vector_weight: Weight for vector similarity score (0-1)
        keyword_weight: Weight for keyword overlap score (0-1)
        top_k: Number of top results to return

    Returns:
        Reranked list of documents
    """
    if not documents:
        return []

    scored_docs = []
    max_vector_rank = len(documents)

    for rank, doc in enumerate(documents, 1):
        # Vector similarity score (inverse rank normalization)
        vector_score = 1.0 - ((rank - 1) / max_vector_rank)

        # Keyword overlap score
        text = doc.get("text", "")
        keyword_score = compute_keyword_score(query, text)

        # Combined score
        combined_score = (vector_weight * vector_score) + (keyword_weight * keyword_score)

        scored_docs.append((combined_score, doc))

    # Sort by combined score descending
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    # Return top_k documents
    return [doc for score, doc in scored_docs[:top_k]]
