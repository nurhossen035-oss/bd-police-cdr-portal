# BD Police CDR Intelligence Platform

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Open `http://127.0.0.1:8000`.

## Render deployment

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

Set these Environment Variables in Render before production use:

- `ADMIN_USER`: a unique administrator username
- `ADMIN_PASS`: a strong, unique password (do not keep the sample default)
- `SESSION_SECRET`: a long random secret (at least 32 random characters)
- `COOKIE_SECURE`: set to `true` on Render/HTTPS; set to `false` only for local HTTP testing
- Optional: `CONTACT_NUMBER`, `MAX_UPLOAD_BYTES`

## Supported input files

- `.xlsx`, `.xls`, `.csv`
- Date/time columns commonly named `START_DTTIME`, `START_DATETIME`, `START_TIME`, `CALL_DATE` + `CALL_TIME`, `DATE` + `TIME`, etc.
- Called-party columns such as `B_Party`, `BPARTY`, `CALLED_NUMBER`, `DIALED_NUMBER`, `OTHER_PARTY`.

## Important location handling

An LAC or Cell ID is a network identifier, not a street address or GPS coordinate. This version displays LAC/Cell ID in its own column. It only shows a street/site address and Google Maps link if the uploaded source file contains an explicit address field. No location is guessed from LAC/Cell ID.

## Data handling

Uploaded files are processed in memory and are not saved to disk by this application. Results are held in the browser page until it is refreshed or closed. Do not upload CDR data unless you are authorized to process it. This app is an analysis aid; verify findings against original operator records.

## Login default for first test only

If you have not configured environment variables, the temporary default is `admin` / `police123`. Change both before sharing or using the service in production.
