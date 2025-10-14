from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from services.graph_index.utils import load_env_file

SENSITIVE_KEYS = {
    "astra_db_application_token",
    "watsonx_api_key",
}


def _get_env(key: str) -> str | None:
    value = os.getenv(key)
    return value.strip() if value else None


@dataclass(frozen=True)
class Settings:
    astra_db_api_endpoint: str | None = None
    astra_db_application_token: str | None = None
    astra_db_database_id: str | None = None
    astra_db_keyspace: str | None = None
    astra_db_collection: str | None = None

    watsonx_api_key: str | None = None
    watsonx_project_id: str | None = None
    watsonx_url: str | None = None

    watsonx_embed_model_id: str = "ibm/granite-embedding-278m-multilingual"
    watsonx_gen_model_id: str = "ibm/granite-13b-instruct-v2"
    watsonx_version: str = "2023-05-29"

    # Context compaction controls
    context_compact_threshold: float = 0.25  # compact when remaining < 25%
    max_prompt_chars: int = 120000  # approximate context window size in characters
    chars_per_token: int = 4  # heuristic for reserving new tokens

    def masked(self) -> dict[str, str | None]:
        data = self.__dict__.copy()
        for key in list(data.keys()):
            if key in SENSITIVE_KEYS and data[key]:
                data[key] = "***"
        return data

    def require(self, attr: str) -> str:
        value = getattr(self, attr)
        if not value:
            raise RuntimeError(f"Required setting '{attr}' is not configured.")
        return value


def _build_settings() -> Settings:
    load_env_file()
    return Settings(
        astra_db_api_endpoint=_get_env("ASTRA_DB_API_ENDPOINT"),
        astra_db_application_token=_get_env("ASTRA_DB_APPLICATION_TOKEN"),
        astra_db_database_id=_get_env("ASTRA_DB_DATABASE_ID"),
        astra_db_keyspace=_get_env("ASTRA_DB_KEYSPACE"),
        astra_db_collection=_get_env("ASTRA_DB_COLLECTION"),
        watsonx_api_key=_get_env("WATSONX_API_KEY"),
        watsonx_project_id=_get_env("WATSONX_PROJECT_ID"),
        watsonx_url=_get_env("WATSONX_URL"),
        watsonx_embed_model_id=_get_env("WATSONX_EMBED_MODEL_ID") or Settings.watsonx_embed_model_id,
        watsonx_gen_model_id=_get_env("WATSONX_GEN_MODEL_ID") or Settings.watsonx_gen_model_id,
        watsonx_version=_get_env("WATSONX_VERSION") or Settings.watsonx_version,
        # Context compaction
        context_compact_threshold=float(_get_env("CONTEXT_COMPACT_THRESHOLD") or Settings.context_compact_threshold),
        max_prompt_chars=int(_get_env("MAX_PROMPT_CHARS") or Settings.max_prompt_chars),
        chars_per_token=int(_get_env("CHARS_PER_TOKEN") or Settings.chars_per_token),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return _build_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()  # type: ignore[attr-defined]
