# Hospital Pressure Index - Ruhrgebiet

This project builds a local, reproducible Hospital Pressure Index (HPI) for Ruhrgebiet cities. It combines official NRW/Ruhr hospital statistics, hospital registry classification, demographic indicators, socio-economic unemployment indicators, and scenario-based forecasts.

The dashboard is a local Streamlit app with two main views:

- Region overview: KPI cards, Ruhr city pressure map, regional HPI timeline, and city ranking.
- City deep dive: selected-city metrics, pressure drivers, trends, layer comparison, and forecast scenario comparison.

## Dashboard Preview

The screenshots below show the current Streamlit dashboard UI.

![Region overview with pressure map](<static/Screenshot 2026-06-03 at 20-15-08 Hospital Pressure Index - Ruhrgebiet.png>)

![Forecast HPI timeline](<static/Screenshot 2026-06-03 at 20-15-50 Hospital Pressure Index - Ruhrgebiet.png>)

![City deep dive pressure drivers](<static/Screenshot 2026-06-03 at 20-16-54 Hospital Pressure Index - Ruhrgebiet.png>)

![City trend charts](<static/Screenshot 2026-06-03 at 20-19-36 Hospital Pressure Index - Ruhrgebiet.png>)

![Selected city layer comparison](<static/Screenshot 2026-06-03 at 20-21-26 Hospital Pressure Index - Ruhrgebiet.png>)

## Analysis Layers

- All hospitals: base hospital-system HPI.
- Only acute hospitals: HPI adjusted by manually reviewed hospital acute-care relevance.
- Demographics: acute-care-adjusted HPI with demographic and socio-economic pressure indicators.

Forecast mode supports the layers available in the forecast dataset. The app checks for columns before showing layer options, so missing forecast columns do not raise KeyErrors.

## Data Sources

The pipeline uses public/open datasets and local manual review files:

- NRW/Ruhr hospital capacity and utilization statistics.
- NRW hospital registry data.
- NRW demographic tables.
- NRW unemployment indicators.
- Local manual hospital registry review files in `data/manual/`.

The repository does not contain patient-level records. The datasets are city-level aggregates or public hospital-site registry records.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run tests:

```bash
./.venv/bin/python -m pytest
```

Run the dashboard:

```bash
PYTHONPATH=. ./.venv/bin/streamlit run dashboard/app.py
```

## Security Review Findings

Security check date: June 3, 2026.

Local findings:

- No hardcoded API keys, tokens, passwords, bearer tokens, cloud credentials, or private key files were found in the project scan.
- No paid services, paid APIs, cloud deployments, GPUs, paid inference endpoints, or paid storage are required by the project.
- Dependencies in `requirements.txt` are pinned to exact versions.
- `pip check` reported no broken installed requirements.
- The test suite passes: `4 passed`.
- `.gitignore` excludes `.env`, raw data, processed data, local SQLite review databases, and manual review backups.
- `data/manual/hospital_registry_review.db` and `data/manual/backups/` are ignored by git.
- The tracked manual files are CSV review artifacts, not credentials.
- The Streamlit dashboard has no authentication and should be run only locally or on a trusted private network. It is not hardened for public internet deployment.
- The hospital review helper writes to the local SQLite review DB and can export the review CSV through explicit UI button clicks. Keep backups before accepting or exporting manual review changes.
- Download scripts use official/public NRW URLs with `requests.get(..., timeout=60)` and do not require scraping tools or paid APIs.
- No use of `eval`, unsafe pickle loading, shell execution, or browser scraping was found in the application code scan.

Limitations:

- A live CVE audit was not run because `pip-audit`, `bandit`, and `safety` are not installed in the local environment and no new tools were installed.
- The project is assessed as safe for local research and analysis use, not as a production-secured public web service.

