import json

import time
from typing import Any, Dict
from urllib import error, parse, request

from services.config import get_settings

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


class WatsonxGenerationClient:
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
        self.model_id = model_id or settings.watsonx_gen_model_id
        self.version = settings.watsonx_version

        self._token: str | None = None
        self._token_expiry: float = 0.0

        if not all([self.api_key, self.project_id, self.url, self.model_id]):
            raise RuntimeError("Watsonx generation configuration incomplete. Set WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL in .env")

    def _post(self, url: str, data: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
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

    def _get_token(self) -> str:
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

    def generate(self, prompt: str, **parameters: Any) -> str:
        if not prompt:
            return ""

        token = self._get_token()
        endpoint = f"{self.url}/ml/v1/text/generation?version={self.version}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Project-Id": self.project_id,
        }
        body = json.dumps(
            {
                "model_id": self.model_id,
                "input": prompt,
                "parameters": parameters or {"decoding_method": "greedy", "max_new_tokens": 256},
                "project_id": self.project_id,
            }
        ).encode("utf-8")
        payload = self._post(endpoint, data=body, headers=headers)
        results = payload.get("results") or []
        if results and isinstance(results, list):
            text = results[0].get("generated_text") or results[0].get("output_text")
            if isinstance(text, str):
                return text
        return json.dumps(payload)


def get_generation_client() -> WatsonxGenerationClient:
    return WatsonxGenerationClient()
