# ML Scripts

| Script | Purpose | Output |
| --- | --- | --- |
| 	rain_logreg.py | Fits a logistic regression on the processed USGS streamflow dataset (value vs. high-flow label). Requires 
umpy and scikit-learn. | models/ml/streamflow_logreg.pkl, models/ml/streamflow_logreg_metrics.json |

Run from project root:

`
python scripts/ml/train_logreg.py
`

Install dependencies first if needed: pip install numpy scikit-learn.
