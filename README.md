# CivicPulse — NYC 311 Slow-Resolution Risk & Backlog Signals

A reproducible pipeline for studying service-request closure risk and unusual complaint volumes using official NYC 311 data. It separates temporal model evaluation from descriptive demand monitoring.

## Data
- 3,655,040 311 requests created during 2025
- 3,655,040 unique request IDs; 0 duplicate IDs
- 3,599,691 requests have a closed timestamp; 55,349 remain without one in the downloaded snapshot
- 916 records have a negative created-to-closed interval and are treated as data-quality exceptions

## Prediction task
Predict at creation time whether a request will take more than 7 days to close (or remains open), using only fields available when the request is created: agency, complaint type, descriptor, location type, ZIP/community board/borough, coordinates, and calendar features.

To ensure at least seven days of outcome follow-up inside the 2025 study window, modeling excludes requests created Dec 25–31. This leaves 3,595,493 eligible requests with a 17.20% slow-resolution rate.

## Evaluation design
- Train period: Jan–Sep 2025; deterministic 700,000-row training sample used for compute efficiency
- Validation: Oct 2025 (336,612 requests), used to choose the classification threshold
- Test: Nov 1–Dec 24, 2025 (577,461 requests)
- Model: sparse one-hot creation-time features + class-balanced logistic SGD classifier

## Held-out test results
- ROC-AUC: 0.961
- PR-AUC: 0.785 vs 0.159 positive-rate baseline
- F1: 0.766
- Precision: 0.684
- Recall: 0.869

PR-AUC is emphasized because only 15.9% of test requests are slow-resolution cases.

## Backlog / demand signal
A separate weekly complaint-type × borough monitor compares each week's volume with its prior 8-week history. It flags cells with z-score >= 3 and prior mean >= 20 requests/week. The complete detected set is stored in `reports/volume_anomalies.csv`.

## Important limitations
`Closed Date` is an administrative closure timestamp, not guaranteed to equal the physical completion time of the underlying issue. The classifier predicts that operational outcome, not citizen satisfaction or causal agency performance. Features are associations and should not be interpreted causally.


## Run locally

Use Python 3.12 in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Tiny connectivity sample (kept separately from training files):
python src/download.py --month 2025-01 --max-rows 100 --output /tmp/civicpulse-sample
# Full 2025 download; takes network, disk and memory:
python src/download.py
python src/train.py
```

Source: [NYC Open Data 311 Service Requests](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9). The download selects modeling fields and excludes street addresses and free-text resolution descriptions. Files remain local and are excluded from Git. The public source can revise historical records: a new download may differ from the recorded snapshot and metrics. Partial samples are for connectivity checks only; keep them outside `data/` before training.

`reports/` contains the recorded aggregate snapshot profile, holdout model results, and anomaly table. `src/train.py` prints new evaluation results rather than silently replacing the recorded results. The historical full-data training run is not rerun by a repository smoke check. Downloading all months and fitting on the 700K training sample requires enough memory to load several million rows; this is a batch research workflow.

## Design decisions

- Fit transformations on the training period only; use later months for validation and held-out testing.
- Use creation-time fields rather than closure/status information as model inputs.
- Compare ranking metrics against the held-out class prevalence; choose classification threshold using October validation data.
- Preserve missing timestamps and surface negative intervals as quality diagnostics. The current model target treats negative intervals as not slow; inspect or exclude these anomalies when adapting the study.
- Interpret administrative closure as an operational proxy, not proof of physical completion or a causal agency-quality measure.
