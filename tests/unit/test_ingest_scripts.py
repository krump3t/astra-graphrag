import io
import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from scripts.ingest import fetch_eia_dpr, fetch_usgs_nwis, fetch_kgs_las


class _FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self):  # pragma: no cover - compatibility
        return self.payload

    def __enter__(self):
        return io.BytesIO(self.payload)

    def __exit__(self, exc_type, exc_val, exc_tb):  # pragma: no cover - no cleanup needed
        return False


class FetchEiaDprTests(TestCase):
    @mock.patch("scripts.ingest.fetch_eia_dpr.urlopen", return_value=_FakeResponse(b"hello"))
    def test_fetch_writes_file_and_log(self, mock_urlopen):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            path = fetch_eia_dpr.fetch_eia_dpr(output_dir=out_dir)

            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(), b"hello")

            log_path = out_dir / "download-log.jsonl"
            self.assertTrue(log_path.exists())
            record = json.loads(log_path.read_text().strip())
            self.assertEqual(record["source"], fetch_eia_dpr.EIA_DPR_URL)

            mock_urlopen.assert_called_once_with(fetch_eia_dpr.EIA_DPR_URL)


class FetchUsgsNwisTests(TestCase):
    @mock.patch("scripts.ingest.fetch_usgs_nwis.urlopen", return_value=_FakeResponse(b"{}"))
    def test_fetch_site_json(self, mock_urlopen):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            path = fetch_usgs_nwis.fetch_usgs("03339000", output_dir=out_dir)

            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(), b"{}")

            log_path = out_dir / "download-log.jsonl"
            record = json.loads(log_path.read_text().strip())
            self.assertEqual(record["site"], "03339000")
            self.assertTrue(record["source"].startswith(fetch_usgs_nwis.BASE_URL))

            expected_params = fetch_usgs_nwis.DEFAULT_PARAMS | {"sites": "03339000"}
            mock_urlopen.assert_called_once()
            called_url = mock_urlopen.call_args.args[0]
            for key, value in expected_params.items():
                self.assertIn(f"{key}={value}", called_url)


class FetchKgsLasTests(TestCase):
    @mock.patch("scripts.ingest.fetch_kgs_las.urlopen", return_value=_FakeResponse(b"DATA"))
    def test_fetch_las(self, mock_urlopen):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            path = fetch_kgs_las.fetch_las(output_dir=out_dir)

            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(), b"DATA")

            log_path = out_dir / "download-log.jsonl"
            record = json.loads(log_path.read_text().strip())
            self.assertEqual(record["source"], fetch_kgs_las.DEFAULT_URL)

            mock_urlopen.assert_called_once_with(fetch_kgs_las.DEFAULT_URL)
