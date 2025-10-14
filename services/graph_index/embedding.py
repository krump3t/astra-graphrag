
import json
import os

import time
from typing import Iterable, List
from urllib import error, parse, request

from services.config import get_settings



DEFAULT_EMBED_MODEL = os.getenv("WATSONX_EMBED_MODEL_ID", "ibm/granite-embedding-278m-multilingual")
DEFAULT_VERSION = os.getenv("WATSONX_VERSION", "2023-05-29")
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


class WatsonxEmbeddingClient:
    def __init__(
        self,
        api_key: str | None = None,
        project_id: str | None = None,
        url: str | None = None,
        model_id: str | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.watsonx_api_key
        self.project_id = project_id or settings.watsonx_project_id
        self.url = (url or settings.watsonx_url or "").rstrip("/")
        self.model_id = model_id or settings.watsonx_embed_model_id
        self.version = settings.watsonx_version

        self._token: str | None = None
        self._token_expiry: float = 0.0

        if not all([self.api_key, self.project_id, self.url, self.model_id]):
            raise RuntimeError("Watsonx embedding configuration incomplete. Set WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL in .env")

    def _post(self, url: str, data: bytes, headers: dict[str, str]) -> dict:
        req = request.Request(url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=60) as resp:
                payload = resp.read().decode("utf-8")
                status = resp.status
        except error.HTTPError as exc:  # pragma: no cover - network failure path
            payload = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {payload}") from exc
        except error.URLError as exc:  # pragma: no cover
            raise RuntimeError(f"Network error: {exc}") from exc
        if status >= 400:  # pragma: no cover
            raise RuntimeError(f"Request failed with status {status}: {payload}")
        return json.loads(payload)

    def _get_iam_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        data = parse.urlencode(
            {
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self.api_key,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = self._post(IAM_TOKEN_URL, data=data, headers=headers)
        self._token = payload.get("access_token")
        expires_in = payload.get("expires_in", 3600)
        self._token_expiry = time.time() + expires_in
        if not self._token:
            raise RuntimeError("Failed to obtain IAM token")
        return self._token

    def _call_watsonx_embeddings(self, texts: list[str]) -> List[list[float]]:
        token = self._get_iam_token()
        endpoint = f"{self.url}/ml/v1/text/embeddings?version={self.version}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Project-Id": self.project_id,
        }
        body = json.dumps(
            {
                "inputs": texts,
                "project_id": self.project_id,
                "model_id": self.model_id,
            }
        ).encode("utf-8")
        payload = self._post(endpoint, data=body, headers=headers)
        raw = payload.get("results") or payload.get("data")
        if not isinstance(raw, list):
            raise RuntimeError("Unexpected embedding response format")
        vectors = [item.get("embedding") for item in raw]
        if any(vector is None for vector in vectors) or len(vectors) != len(texts):
            raise RuntimeError("Incomplete embedding response")
        return vectors

    def embed_texts(self, texts: Iterable[str], batch_size: int = 500) -> List[list[float]]:
        """Generate embeddings for texts with automatic batching.

        Args:
            texts: Texts to embed
            batch_size: Maximum texts per API request (Watsonx limit: 1000, default: 500 for safety)

        Returns:
            List of embedding vectors
        """
        texts = list(texts)
        if not texts:
            return []

        # Process in batches if necessary
        if len(texts) <= batch_size:
            return self._call_watsonx_embeddings(texts)

        # Batch processing
        all_vectors = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} texts)...")
            vectors = self._call_watsonx_embeddings(batch)
            all_vectors.extend(vectors)

        return all_vectors


def get_embedding_client() -> WatsonxEmbeddingClient:
    return WatsonxEmbeddingClient()
