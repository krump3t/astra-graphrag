

from scripts.ingest.fetch_eia_dpr import fetch_eia_dpr
from scripts.ingest.fetch_usgs_nwis import fetch_usgs
from scripts.ingest.fetch_kgs_las import fetch_las

from . import paths


def ensure_raw_datasets() -> None:
    """Rehydrate core datasets if the canonical directories are empty."""

    if not paths.RAW_EIA_DIR.exists() or not any(paths.RAW_EIA_DIR.iterdir()):
        fetch_eia_dpr()

    if not paths.RAW_USGS_DIR.exists() or not any(paths.RAW_USGS_DIR.iterdir()):
        fetch_usgs("03339000")

    if not paths.RAW_LAS_DIR.exists() or not any(paths.RAW_LAS_DIR.iterdir()):
        fetch_las()
