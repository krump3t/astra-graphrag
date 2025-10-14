from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List
from urllib import request, error

from services.config import get_settings
from services.graph_index.retry_utils import retry_with_backoff

JSON = Dict[str, Any]


class AstraApiClient:
    def __init__(self):
        settings = get_settings()
        self.base = (settings.astra_db_api_endpoint or "").rstrip("/")
        self.token = settings.astra_db_application_token
        self.keyspace = settings.astra_db_keyspace or "default_keyspace"
        if not (self.base and self.token):
            raise RuntimeError("Astra API endpoint and token are required. Configure ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN in .env")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Cassandra-Token": self.token,  # Data API auth header
        }

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _post(self, path: str, payload: JSON) -> JSON:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(self._url(path), data=data, headers=self._headers(), method="POST")
        try:
            with request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - network path
            raise RuntimeError(f"Astra POST {path} failed: {exc.code} {exc.read().decode('utf-8', errors='ignore')}")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _get(self, path: str) -> JSON:
        req = request.Request(self._url(path), headers=self._headers(), method="GET")
        try:
            with request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover
            raise RuntimeError(f"Astra GET {path} failed: {exc.code} {exc.read().decode('utf-8', errors='ignore')}")

    # Collections (JSON API)
    def list_collections(self) -> JSON:
        return self._post(f"/api/json/v1/{self.keyspace}", {"findCollections": {}})

    def create_collection(self, name: str, definition: JSON | None = None) -> JSON:
        payload = {"createCollection": {"name": name}}
        if definition:
            payload["createCollection"]["options"] = definition
        return self._post(f"/api/json/v1/{self.keyspace}", payload)

    def upsert_documents(self, collection: str, documents: Iterable[JSON]) -> JSON:
        return self._post(f"/api/json/v1/{self.keyspace}/{collection}", {"insertMany": {"documents": list(documents)}})

    def count_documents(self, collection: str, filter_dict: Dict[str, Any] | None = None, upper_bound: int = 10000) -> int:
        """Count documents matching filter without vector search.

        Args:
            collection: Collection name
            filter_dict: Optional metadata filters
            upper_bound: Maximum number of documents to count

        Returns:
            Count of matching documents
        """
        payload = {
            "countDocuments": {
                "filter": filter_dict or {}
            }
        }
        response = self._post(f"/api/json/v1/{self.keyspace}/{collection}", payload)
        return response.get("status", {}).get("count", 0)

    # Vector service
    def create_vector_collection(self, name: str, dimension: int, metric: str = "cosine") -> JSON:
        definition = {
            "vector": {
                "dimension": dimension,
                "metric": metric,
            }
        }
        return self.create_collection(name, definition)

    def vector_search(
        self,
        collection: str,
        embedding: List[float],
        limit: int = 5,
        filter_dict: Dict[str, Any] | None = None,
        max_documents: int | None = None
    ) -> List[JSON]:
        """Execute vector similarity search with optional metadata filtering.

        Args:
            collection: Collection name
            embedding: Query embedding vector
            limit: Documents per page (max 1000, AstraDB hard limit)
            filter_dict: Optional metadata filters
            max_documents: Maximum total documents to retrieve across all pages (None = no limit)

        Returns:
            List of documents (may be paginated if limit > 1000)
        """
        # AstraDB has hard limit of 1000 docs per request
        page_size = min(limit, 1000)

        all_documents = []
        next_page_state = None

        while True:
            payload = {
                "find": {
                    "filter": filter_dict or {},
                    "sort": {"$vector": embedding},
                    "options": {"limit": page_size}
                }
            }

            # Add pagination state if this is not the first request
            if next_page_state:
                payload["find"]["options"]["pagingState"] = next_page_state

            response = self._post(f"/api/json/v1/{self.keyspace}/{collection}", payload)
            data = response.get("data", {})
            documents = data.get("documents", [])

            all_documents.extend(documents)

            # Check if we've reached the desired limit
            if max_documents and len(all_documents) >= max_documents:
                return all_documents[:max_documents]

            # Check for more pages
            next_page_state = data.get("nextPageState")

            # Stop if no more pages or we've collected enough documents
            if not next_page_state:
                break

            # Stop if we got fewer documents than page_size (no more pages)
            if len(documents) < page_size:
                break

        return all_documents

    def batch_fetch_by_ids(
        self,
        collection: str,
        document_ids: List[str],
        embedding: List[float] | None = None
    ) -> List[JSON]:
        """Fetch multiple documents by their IDs in a single batch request.

        Args:
            collection: Collection name
            document_ids: List of document _id values to fetch
            embedding: Optional embedding for sorting (if None, no sorting applied)

        Returns:
            List of documents matching the IDs
        """
        if not document_ids:
            return []

        # Build filter with $in operator for batch fetch
        filter_dict = {"_id": {"$in": document_ids}}

        payload = {
            "find": {
                "filter": filter_dict,
                "options": {"limit": min(len(document_ids), 1000)}  # Batch size up to 1000
            }
        }

        # Add sorting by vector similarity if embedding provided
        if embedding:
            payload["find"]["sort"] = {"$vector": embedding}

        response = self._post(f"/api/json/v1/{self.keyspace}/{collection}", payload)
        data = response.get("data", {})
        return data.get("documents", [])

