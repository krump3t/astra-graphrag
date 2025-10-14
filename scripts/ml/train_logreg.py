import argparse
import json
import pickle
from pathlib import Path

from services.graph_index import paths

try:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report
except ImportError as exc:  # pragma: no cover - scikit-learn optional
    raise SystemExit(
        "scikit-learn and numpy are required for the ML demo. Install them with pip install numpy scikit-learn."
    ) from exc


def _load_usgs_dataset():
    csv_path = paths.PROCESSED_TABLES_DIR / "usgs_streamflow_latest.csv"
    if not csv_path.exists():
        raise SystemExit("usgs_streamflow_latest.csv not found. Run scripts/processing/usgs_to_csv.py first.")

    values = []
    qualifiers = []
    with csv_path.open(encoding="utf-8") as fh:
        header = fh.readline().strip().split(",")
        columns = {name: idx for idx, name in enumerate(header)}
        for line in fh:
            if not line.strip():
                continue
            parts = line.strip().split(",")
            try:
                flow = float(parts[columns["value"]])
            except (ValueError, KeyError):
                continue
            values.append(flow)
            qualifier = parts[columns.get("qualifiers", len(parts)-1)] if "qualifiers" in columns else ""
            qualifiers.append(1.0 if "P" in qualifier.upper() else 0.0)

    if not values:
        raise SystemExit("No numeric streamflow values available for ML demo.")

    X = np.column_stack([values, qualifiers])
    threshold = float(np.median(values))
    y = (np.array(values) >= threshold).astype(int)
    return X, y


def train(output_dir: Path | None = None) -> tuple[Path, Path]:
    X, y = _load_usgs_dataset()
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)

    y_pred = model.predict(X)
    report = classification_report(y, y_pred, output_dict=True, zero_division=0)

    target_dir = output_dir or Path("models/ml")
    target_dir.mkdir(parents=True, exist_ok=True)

    model_path = target_dir / "streamflow_logreg.pkl"
    metrics_path = target_dir / "streamflow_logreg_metrics.json"

    with model_path.open("wb") as fh:
        pickle.dump(model, fh)

    with metrics_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    return model_path, metrics_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a simple logistic regression on USGS streamflow data.")
    parser.add_argument("--output-dir", type=Path, help="Optional directory for models and metrics.")
    args = parser.parse_args()

    model_path, metrics_path = train(args.output_dir)
    print(f"Saved model to {model_path}")
    print(f"Saved metrics to {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
