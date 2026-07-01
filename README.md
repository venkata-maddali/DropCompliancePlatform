# DROP Compliance Platform Tool

This project implements a generic Python + MySQL workflow for companies that need to comply with DROP-style data download and upload cycles.

## What it does

1. Downloads a ZIP file from the DROP `/download/data` endpoint.
2. Extracts the email CSV and reads the `DropID` / `HashEmail` pairs.
3. Compares each hash to a MySQL table of raw customer emails that are hashed with SHA-256 before comparison.
4. Resolves each record to one of the required statuses:
   - `deleted`
   - `opted_out`
   - `not_found`
5. Writes a new CSV with the same file name and the `DropID` / `Status` columns.
6. Uploads the CSV to `/download/upload`.
7. Processes a returned failure CSV (for example from email attachment or local file) and generates an amended file for `/download/amend`.

## Suggested database design

The schema in [schema.sql](schema.sql) is designed for auditability and future event analysis:

- `raw_emails`: source-of-truth customer records with hashed emails and consent/deletion status.
- `drop_cycle_runs`: one row per DROP cycle to track the run metadata.
- `drop_results`: one row per processed record to preserve evidence for audits.
- `drop_amendments`: records the corrected status after a failure report is processed.

## Repository setup

This project is ready to be tracked as a Git repository. After installing Git, initialize the repo and create the initial commit:

```powershell
cd "c:\Users\venka\Documents\DROP Compliance Platform (DCP)"
git init
git add .
git commit -m "Initial version of DROP Compliance Platform tool"
```

If you want to publish the project to GitHub later, add the remote and push the initial branch.

## Generic design for any company

The tool is intentionally configurable so it can be reused for similar compliance use cases across companies:

- The DROP endpoints are configurable through environment variables so you can point to a different provider or path without changing code.
- The hash strategy is centralized and can be swapped if your organization uses a different algorithm.
- The MySQL schema keeps audit-friendly history for each cycle and each amendment.
- The workflow can be wrapped in a scheduler or a lightweight web UI for operational use.

## Quick start

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy [.env.example](.env.example) to `.env` and update the values.
3. Initialize the MySQL schema:
   ```bash
   python main.py init-db
   ```
4. Import raw emails from a CSV file:
   ```bash
   python main.py import-raw-emails --input-csv path/to/raw_emails.csv
   ```
5. Run a DROP cycle:
   ```bash
   python main.py run-cycle --cycle-date 2026-07-01 --output-dir ./output
   ```
6. Process a failure report and create an amended file:
   ```bash
   python main.py process-amendment --run-id 1 --report-csv ./output/failure_report.csv
   ```
7. Start the web UI:
   ```bash
   python app.py
   ```
8. Start the scheduler:
   ```bash
   python scheduler.py
   ```

## Externalized configuration

All runtime settings are controlled through environment variables. Copy [.env.example](.env.example) to `.env` and update the values for your environment.

Key settings include:

- `DROP_BASE_URL`
- `DROP_API_KEY`
- `DROP_DOWNLOAD_ENDPOINT`
- `DROP_UPLOAD_ENDPOINT`
- `DROP_AMEND_ENDPOINT`
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`
- `OUTPUT_DIR`
- `WEB_PORT`
- `SCHEDULE_INTERVAL_DAYS`

## CSV expectations

### Raw emails import format

The import command expects a CSV with at least these columns:

- `email`
- `deleted` (optional; `true/false`/`1/0`)
- `opted_out` (optional; `true/false`/`1/0`)

### DROP input format

The downloaded DROP source CSV should contain:

- `DropID`
- `HashEmail`

### Output format

The generated CSV will contain:

- `DropID`
- `Status`
