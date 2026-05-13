# AI Text Processor

> Paste any text — or a URL — and get back a concise AI summary, three key takeaways, a logged row in Google Sheets, and an email delivery. End-to-end pipeline built with **Streamlit + FastAPI + n8n + Google Gemini**.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688) ![Streamlit](https://img.shields.io/badge/Streamlit-1.39-red) ![n8n](https://img.shields.io/badge/n8n-workflow-EA4B71)

---

## What it does

You give it text (or an article URL). It returns:

- **Summary** — a polished 2–4 sentence summary
- **3 key points** — the most important takeaways from the text
- **Logged history** — every request appended to a Google Sheet
- **Email delivery** — the summary lands in the user's inbox

A Google Gemini agent (running inside an n8n AI Agent node) handles all the language work, with a per-session memory buffer keyed on the request ID.

## Architecture

```
┌────────────┐    ┌──────────────┐    ┌───────────────────────────┐
│ Streamlit  │───▶│ FastAPI      │───▶│ n8n  ─ Webhook            │
│ (frontend) │    │ (backend)    │    │       └─ AI Agent         │
└────────────┘    └──────────────┘    │            ├─ Gemini LLM  │
       ▲                              │            └─ Memory      │
       │                              │       ─ Build Record      │
       │                              │       ─ Google Sheets ───▶│ Sheet
       │                              │       ─ Gmail ──────────▶ │ Inbox
       └──────────── JSON response ◀──│       ─ Respond Webhook   │
                                      └───────────────────────────┘
```

### Why this split?

| Layer | Responsibility |
| --- | --- |
| **Frontend** (Streamlit) | Collect email + text/URL, show summary nicely |
| **Backend** (FastAPI) | Validate input, generate `session_id`, **scrape URL if provided**, forward to n8n |
| **n8n** | Orchestrate the AI call, persistence (Sheets), delivery (Gmail) — all visually, with one-click credentials |

## Features

- Two input modes: **paste text** or **paste URL** (server scrapes visible content with BeautifulSoup, strips nav/footer/scripts)
- Stateful per-session memory buffer in the AI Agent
- 8-column structured logging in Google Sheets
- Email notification via Gmail
- Every step inspectable in n8n's Executions panel
- Clean JSON response surfaced back in the UI

---

## Quick start

### Prerequisites

1. **Python 3.10+** — <https://www.python.org/downloads/>
2. **An n8n instance** — easiest is the free [n8n Cloud trial](https://n8n.io). To self-host: `npx n8n` (Node 18+).
3. **Google Gemini API key** — <https://aistudio.google.com/apikey> (free tier works).
4. **A Google account** — for Sheets + Gmail OAuth.

### 1. Clone and prepare

```powershell
git clone https://github.com/<your-username>/ai-text-processor.git
cd ai-text-processor
```

### 2. Create a Google Sheet

1. Go to <https://sheets.google.com> → new blank sheet, name it anything (e.g. `AI Text Processing Log`).
2. In row 1, fill A1 → H1 with these exact headers:
   ```
   Session ID | Email | Source | Source URL | Original Text | Summary | Key Points | Timestamp
   ```
3. Keep the tab name as `Sheet1`.

### 3. Import the workflow into n8n

1. In n8n: **Workflows → Import from File** → pick `workflow.json`.
2. The workflow appears with 8 nodes connected as in the architecture diagram.

### 4. Wire up your own credentials in n8n

Each auth-needing node shows a red badge after import. Open each one and create a credential:

#### a. Google Gemini

- Open **Google Gemini Chat Model** node.
- Credential dropdown → **+ Create new** → paste your API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
- Optionally change the model from the dropdown (e.g. `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash`).

#### b. Google Sheets

- Open **Google Sheets** node → credential → **+ Create new → Google Sheets OAuth2** → sign in with Google.
- In the same node, pick your Sheet from the **Document** dropdown and `Sheet1` from the **Sheet** dropdown.

#### c. Gmail

- Open **Send Email** node → credential → **+ Create new → Gmail OAuth2** → sign in with Google.

> On self-hosted n8n you'll need to register an OAuth client in Google Cloud Console (one-time, ~5 min). On n8n Cloud it's a single click. See <https://docs.n8n.io/integrations/builtin/credentials/google/>.

### 5. Activate the workflow & grab the webhook URL

1. **Save** the workflow.
2. Toggle **Inactive → Active** (top right).
3. Open the **Webhook** node → copy the **Production URL**. It looks like:
   - n8n Cloud: `https://<your-subdomain>.app.n8n.cloud/webhook/ai-text-processing`
   - Self-hosted: `http://localhost:5678/webhook/ai-text-processing`

### 6. Run the backend

```powershell
cd backend
Copy-Item .env.example .env
# Open .env and paste your webhook URL into N8N_WEBHOOK_URL=...
.\run.ps1
```

This creates a virtualenv, installs deps, and starts FastAPI on <http://localhost:8000>.

Sanity check: <http://localhost:8000> should return `"n8n_webhook_configured": true`.

### 7. Run the frontend (open a second terminal)

```powershell
cd frontend
Copy-Item .env.example .env
.\run.ps1
```

A browser opens at <http://localhost:8501>.

### 8. Try it

1. In the sidebar click **Check backend health** — should say OK.
2. Enter your email + paste any article in the **Paste Text** tab.
3. Click **Process**. Within ~10 seconds you'll see the summary + 3 key points.
4. Verify the side effects:
   - A new row appears in your Google Sheet.
   - You receive an email with the summary.
   - The n8n **Executions** tab shows every node green.

### 9. Bonus: process a URL

Switch to the **From URL** tab, paste a public article (e.g. a Wikipedia page), submit, and the backend will scrape the page and feed the cleaned text through the same pipeline.

---

## Project structure

```
.
├── frontend/                 Streamlit UI
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   └── run.ps1
├── backend/                  FastAPI service
│   ├── main.py               POST /process — validates, scrapes URLs, forwards to n8n
│   ├── requirements.txt
│   ├── .env.example
│   └── run.ps1
├── workflow.json             Importable n8n workflow (sanitised template)
├── .gitignore
└── README.md
```

## API

### `POST /process`

Request:

```json
{
  "email": "user@example.com",
  "text": "Artificial Intelligence is transforming healthcare..."
}
```

Or for URL mode:

```json
{
  "email": "user@example.com",
  "url": "https://example.com/article"
}
```

Response:

```json
{
  "status": "accepted",
  "session_id": "9f3c2a4b1e7d",
  "source": "text",
  "chars_sent": 412,
  "n8n_status_code": 200,
  "n8n_response": {
    "status": "ok",
    "session_id": "9f3c2a4b1e7d",
    "summary": "…",
    "key_points": ["…", "…", "…"]
  }
}
```

### Health endpoints

- `GET /` — service info + whether the n8n URL is configured
- `GET /health` — simple liveness probe

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Backend returns `502 Failed to reach n8n` | Wrong URL in `backend/.env`. Must be the **Production** URL of the Webhook node, and the workflow must be **Active**. |
| Webhook returns `404 not registered` | Workflow is inactive, or you used the *Test URL* without first clicking **Execute Workflow** in n8n. |
| Gemini node returns `401` / `403` | Invalid API key, or your Gemini API key has no quota / billing enabled. |
| Google Sheets node `404` | You forgot to pick the document & tab from the dropdowns after import. |
| Empty cells in the sheet | Column mapping is set to *Auto-map*. Switch to *Map Each Column Manually* and use the 8 mappings in `workflow.json`. |
| Email never arrives | Check spam folder; also check the Gmail node in n8n Executions for an error. |
| URL scrape returns empty text | The page is rendered with JavaScript. Try a plain HTML article (e.g. Wikipedia). |
