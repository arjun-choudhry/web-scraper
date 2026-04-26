# Web Scraper - Webpage to PDF

Python web application that accepts one or more URLs, renders each page as a full visual PDF, and returns either a single PDF or a ZIP archive.

## Structure

- `frontend/`: HTML UI templates
- `server/`: FastAPI app, routes, validation, jobs, and rendering services
- `tests/`: validation, archive, and API smoke tests

## Stack

- FastAPI API + server-rendered HTML page
- Playwright (Python) for browser-accurate PDF rendering
- Standard library ZIP packaging

## Run Locally

1. Create a virtual environment and install dependencies:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Install Playwright browser binaries:
   - `python -m playwright install chromium`
3. Start the app:
   - `uvicorn server.main:app --reload`
4. Open:
   - `http://127.0.0.1:8000`

## API

- `POST /api/convert`
  - Body: `{ "urls": ["https://example.com"], "url_text": "https://example.org" }`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/download`

## Notes

- V1 rejects localhost URLs and limits batch size to 30 URLs.
- Single-URL jobs return a direct PDF download; multi-URL jobs return a ZIP.
- Job state is stored in-memory. Restarting the process clears active/history jobs.
