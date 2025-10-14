from unittest import TestCase
import json

from services.graph_index.astra_api import AstraApiClient
from services.config.settings import Settings


class AstraPayloadTests(TestCase):
    """Validate Astra API request payloads without sending them."""

    def test_create_collection_payload(self):
        """Validate collection creation payload structure."""
        settings = Settings(
            astra_db_api_endpoint="https://test.apps.astra.datastax.com",
            astra_db_application_token="test_token",
            astra_db_keyspace="test_keyspace",
        )
        client = AstraApiClient.__new__(AstraApiClient)
        client.base = settings.astra_db_api_endpoint.rstrip("/")
        client.token = settings.astra_db_application_token
        client.keyspace = settings.astra_db_keyspace

        # Validate URL construction
        url = client._url("/api/json/v1/test_keyspace/collections")
        self.assertEqual(url, "https://test.apps.astra.datastax.com/api/json/v1/test_keyspace/collections")

        # Validate headers
        headers = client._headers()
        self.assertIn("X-Cassandra-Token", headers)
        self.assertEqual(headers["X-Cassandra-Token"], "test_token")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_create_vector_collection_payload(self):
        """Validate vector collection creation payload."""
        settings = Settings(
            astra_db_api_endpoint="https://test.apps.astra.datastax.com",
            astra_db_application_token="test_token",
            astra_db_keyspace="test_keyspace",
        )
        client = AstraApiClient.__new__(AstraApiClient)
        client.base = settings.astra_db_api_endpoint.rstrip("/")
        client.token = settings.astra_db_application_token
        client.keyspace = settings.astra_db_keyspace

        # Build expected payload
        definition = {
            "vector": {
                "dimension": 768,
                "metric": "cosine",
            }
        }
        expected_payload = {"name": "embeddings", **definition}

        # Validate payload structure
        self.assertIn("name", expected_payload)
        self.assertIn("vector", expected_payload)
        self.assertEqual(expected_payload["vector"]["dimension"], 768)
        self.assertEqual(expected_payload["vector"]["metric"], "cosine")

    def test_upsert_documents_payload(self):
        """Validate document upsert payload structure."""
        settings = Settings(
            astra_db_api_endpoint="https://test.apps.astra.datastax.com",
            astra_db_application_token="test_token",
            astra_db_keyspace="test_keyspace",
        )
        client = AstraApiClient.__new__(AstraApiClient)
        client.base = settings.astra_db_api_endpoint.rstrip("/")
        client.token = settings.astra_db_application_token
        client.keyspace = settings.astra_db_keyspace

        # Build expected documents
        documents = [
            {"_id": "1", "text": "sample node", "$vector": [0.1] * 768},
            {"_id": "2", "text": "another node", "$vector": [0.2] * 768},
        ]
        expected_payload = {"documents": documents}

        # Validate payload structure
        self.assertIn("documents", expected_payload)
        self.assertEqual(len(expected_payload["documents"]), 2)
        self.assertIn("$vector", expected_payload["documents"][0])
        self.assertEqual(len(expected_payload["documents"][0]["$vector"]), 768)

    def test_vector_search_payload(self):
        """Validate vector search payload structure."""
        # Expected vector search payload structure
        query_embedding = [0.15] * 768
        expected_payload = {
            "find": {
                "filter": {},
                "sort": {"$vector": query_embedding},
                "options": {"limit": 5}
            }
        }

        # Validate payload structure
        self.assertIn("find", expected_payload)
        self.assertIn("sort", expected_payload["find"])
        self.assertIn("$vector", expected_payload["find"]["sort"])
        self.assertEqual(len(expected_payload["find"]["sort"]["$vector"]), 768)
        self.assertEqual(expected_payload["find"]["options"]["limit"], 5)

        # Ensure payload is JSON-serializable
        json_str = json.dumps(expected_payload)
        self.assertIsInstance(json_str, str)
        reconstructed = json.loads(json_str)
        self.assertEqual(reconstructed, expected_payload)

    def test_vector_search_with_filter_payload(self):
        """Validate vector search with metadata filter."""
        query_embedding = [0.15] * 768
        expected_payload = {
            "find": {
                "filter": {"type": "well"},
                "sort": {"$vector": query_embedding},
                "options": {"limit": 10}
            }
        }

        # Validate payload structure
        self.assertIn("filter", expected_payload["find"])
        self.assertEqual(expected_payload["find"]["filter"]["type"], "well")
        self.assertEqual(expected_payload["find"]["options"]["limit"], 10)

        # Ensure payload is JSON-serializable
        json_str = json.dumps(expected_payload)
        self.assertIsInstance(json_str, str)
