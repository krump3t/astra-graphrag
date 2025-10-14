from pathlib import Path

RAW_EIA_DIR = Path("data/raw/structured/eia_dpr")
RAW_USGS_DIR = Path("data/raw/semi_structured/usgs_nwis")
RAW_LAS_DIR = Path("data/raw/unstructured/kgs_las")
RAW_FORCE2020_LAS_DIR = Path("data/raw/force2020/las_files")

PROCESSED_TABLES_DIR = Path("data/processed/tables")
PROCESSED_GRAPH_DIR = Path("data/processed/graph")
PROCESSED_EMBEDDINGS_DIR = Path("data/processed/embeddings")

CONFIG_ENV_DIR = Path("configs/env")
CONFIG_PROMPTS_DIR = Path("configs/prompts")

GRAPH_INDEX_DIR = Path("services/graph_index")
LANGGRAPH_DIR = Path("workflows/langgraph")
