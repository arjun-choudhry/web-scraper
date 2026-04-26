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

## Authentication

The app supports multiple authentication methods:

### Browser Session (Recommended for already-signed-in users)

If you're already signed in to a site in your browser, use the "Browser Session" option. This reads cookies from your current session to access protected content.

To use this method:

1. Open Developer Tools (F12) on the site you want to scrape
2. Go to **Application** → **Cookies**
3. Run this in the Console to export cookies:

```javascript
JSON.stringify(document.cookie.split(';').map(c => {
  const [name, value] = c.trim().split('=');
  return { name, value, domain: window.location.hostname, path: '/' };
}))
```

4. Save the output to `auth_cookies.json`
5. Use "Browser Session" option with `auth_cookies.json`

### Cookie-based Authentication

1. Capture cookies from a signed-in session:
   ```bash
   python scripts/capture_cookies.py "https://example.com/login" -o auth_cookies.json
   ```
2. Sign in in the browser window that opens
3. Close the browser when done - cookies are saved to `auth_cookies.json`
4. Use the cookie file in your conversion request

### Popup Authentication

1. Select "Popup Auth" in the UI
2. Enter the login URL (e.g., `https://example.com/login`)
3. A popup will open for you to sign in
4. After signing in, the session cookies are captured and used for rendering

## Notes

- If a site blocks automated browsers with "not secure" warnings, use the manual cookie export method above from your actual signed-in browser session.
- Some sites (like Google) may still block automated browsers regardless of configuration. In those cases, manual cookie export from your real browser is the most reliable approach.

## Notes

- V1 rejects localhost URLs and limits batch size to 30 URLs.
- Single-URL jobs return a direct PDF download; multi-URL jobs return a ZIP.
- Job state is stored in-memory. Restarting the process clears active/history jobs.
