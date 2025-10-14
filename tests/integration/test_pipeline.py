import csv
import json
from io import BytesIO
import tempfile
from pathlib import Path
from unittest import TestCase, mock
from zipfile import ZipFile

from scripts.ingest import fetch_eia_dpr, fetch_usgs_nwis, fetch_kgs_las
from services.config.settings import Settings
from scripts.processing import eia_to_csv, usgs_to_csv, las_to_metadata, graph_from_processed, embed_nodes
from services.graph_index import paths


class _BytesResponse:
    def __init__(self, payload: bytes):
        self._payload = payload
        self._buffer: BytesIO | None = None

    def __enter__(self):
        self._buffer = BytesIO(self._payload)
        return self._buffer

    def __exit__(self, exc_type, exc, tb):
        if self._buffer is not None:
            self._buffer.close()
        return False


def _make_eia_workbook() -> bytes:
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>
  <Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>
  <Default Extension='xml' ContentType='application/xml'/>
  <Override PartName='/xl/workbook.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'/>
  <Override PartName='/xl/worksheets/sheet1.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'/>
  <Override PartName='/xl/sharedStrings.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml'/>
</Types>""")
        zf.writestr("_rels/.rels", """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>
  <Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='xl/workbook.xml'/>
</Relationships>""")
        zf.writestr("xl/_rels/workbook.xml.rels", """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>
  <Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet' Target='worksheets/sheet1.xml'/>
  <Relationship Id='rId2' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings' Target='sharedStrings.xml'/>
</Relationships>""")
        zf.writestr("xl/workbook.xml", """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<workbook xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>
  <sheets>
    <sheet name='Sheet1' sheetId='1' r:id='rId1' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'/>
  </sheets>
</workbook>""")
        zf.writestr("xl/sharedStrings.xml", """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<sst xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>
  <si><t>FieldA</t></si>
  <si><t>FieldB</t></si>
  <si><t>TextVal</t></si>
</sst>""")
        zf.writestr("xl/worksheets/sheet1.xml", """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>
  <sheetData>
    <row r='1'><c r='A1' t='s'><v>0</v></c><c r='B1' t='s'><v>1</v></c></row>
    <row r='2'><c r='A2'><v>123</v></c><c r='B2' t='s'><v>2</v></c></row>
  </sheetData>
</worksheet>""")
    return buf.getvalue()


def _make_usgs_payload() -> bytes:
    payload = {
        "value": {
            "timeSeries": [
                {
                    "sourceInfo": {
                        "siteCode": [{"value": "03339000"}],
                        "siteName": "Sample Site",
                    },
                    "variable": {
                        "variableCode": [{"value": "00060"}],
                        "variableDescription": "Discharge, cubic feet per second",
                    },
                    "values": [
                        {
                            "qualifier": [{"qualifierCode": "P"}],
                            "method": [{"methodID": "123"}],
                            "value": [
                                {
                                    "dateTime": "2025-01-01T00:00:00.000-06:00",
                                    "value": "10.5",
                                    "qualifiers": ["P"],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }
    return json.dumps(payload).encode("utf-8")


def _make_las_payload() -> bytes:
    return b"""# STAT . Kansas: Example State\n# SECT . 28: Section info\n~Curve Information\nDEPT.FT : Depth\nGR.API : Gamma Ray\n"""


class PipelineIntegrationTests(TestCase):
    def setUp(self):
        self.tmp_root = Path(tempfile.mkdtemp())
        patches = [
            mock.patch("services.graph_index.paths.RAW_EIA_DIR", self.tmp_root / "raw/structured/eia_dpr"),
            mock.patch("services.graph_index.paths.RAW_USGS_DIR", self.tmp_root / "raw/semi/usgs"),
            mock.patch("services.graph_index.paths.RAW_LAS_DIR", self.tmp_root / "raw/unstructured/las"),
            mock.patch("services.graph_index.paths.PROCESSED_TABLES_DIR", self.tmp_root / "processed/tables"),
            mock.patch("services.graph_index.paths.PROCESSED_GRAPH_DIR", self.tmp_root / "processed/graph"),
            mock.patch("services.graph_index.paths.PROCESSED_EMBEDDINGS_DIR", self.tmp_root / "processed/embeddings"),
        ]
        self._patches = [p.start() for p in patches]
        for patcher in patches:
            self.addCleanup(patcher.stop)

    @mock.patch("services.graph_index.embedding.get_settings", return_value=Settings())
    @mock.patch("scripts.ingest.fetch_kgs_las.urlopen", return_value=_BytesResponse(_make_las_payload()))
    @mock.patch("scripts.ingest.fetch_usgs_nwis.urlopen", return_value=_BytesResponse(_make_usgs_payload()))
    @mock.patch("scripts.ingest.fetch_eia_dpr.urlopen", return_value=_BytesResponse(_make_eia_workbook()))
    def test_end_to_end_pipeline(self, *_mocks):
        fetch_eia_dpr.fetch_eia_dpr(output_dir=paths.RAW_EIA_DIR)
        fetch_usgs_nwis.fetch_usgs("03339000", output_dir=paths.RAW_USGS_DIR)
        fetch_kgs_las.fetch_las(output_dir=paths.RAW_LAS_DIR)

        eia_csv = eia_to_csv.export_latest_eia_csv()
        usgs_csv = usgs_to_csv.export_latest_usgs_csv()
        las_json = las_to_metadata.export_las_metadata()

        self.assertTrue(eia_csv.exists())
        self.assertTrue(usgs_csv.exists())
        self.assertTrue(las_json.exists())

        header, row = None, None
        with eia_csv.open(encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            row = next(reader)
        self.assertEqual(header, ["FieldA", "FieldB"])
        self.assertEqual(row[0], "123")

        with usgs_csv.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            first = next(reader)
        self.assertEqual(first["site_code"], "03339000")
        self.assertEqual(first["value"], "10.5")

        data = json.loads(las_json.read_text(encoding="utf-8"))
        self.assertEqual(data["stats"].get("stat"), "Example State")
        self.assertEqual(len(data["curves"]), 2)

        graph_path = graph_from_processed.build_combined_graph()
        self.assertTrue(graph_path.exists())
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(graph.get("nodes", [])), 1)
        self.assertGreaterEqual(len(graph.get("edges", [])), 1)

        embedding_path = embed_nodes.generate_node_embeddings()
        payload = json.loads(embedding_path.read_text(encoding="utf-8"))
        self.assertIn(payload.get("use_placeholder"), [True, False])
        self.assertGreaterEqual(len(payload.get("items", [])), 1)
