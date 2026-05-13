"""
FastAPI backend for the AI Text Processing Workflow.

Receives an email + text (or URL) from the frontend, generates a unique
session_id, optionally scrapes the URL, and forwards everything to the
n8n webhook for AI summarisation and downstream processing.
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator

load_dotenv()

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "60"))

app = FastAPI(
    title="AI Text Processing API",
    description="Bridges the frontend with the n8n AI workflow.",
    version="1.0.0",
)

# Open CORS so the Streamlit / React / static frontend can call us locally.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    email: EmailStr
    text: Optional[str] = Field(default=None, description="Raw text to process")
    url: Optional[str] = Field(default=None, description="Optional website URL (bonus)")

    @field_validator("text")
    @classmethod
    def _strip_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class ProcessResponse(BaseModel):
    status: str
    session_id: str
    source: str
    chars_sent: int
    n8n_status_code: int
    n8n_response: dict | str


def scrape_url(url: str) -> str:
    """Fetch a web page and return cleaned visible text. Used for the bonus task."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = " ".join(text.split())

    if not text:
        raise HTTPException(status_code=400, detail="Could not extract any text from the URL.")

    # Cap extracted text so we don't blow up the LLM context / Sheets cell.
    return text[:8000]


@app.get("/")
def root() -> dict:
    return {
        "status": "ok",
        "service": "AI Text Processing API",
        "n8n_webhook_configured": bool(N8N_WEBHOOK_URL),
    }


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}


@app.post("/process", response_model=ProcessResponse)
def process(payload: ProcessRequest) -> ProcessResponse:
    if not N8N_WEBHOOK_URL:
        raise HTTPException(
            status_code=500,
            detail="N8N_WEBHOOK_URL is not configured. Set it in backend/.env",
        )

    if not payload.text and not payload.url:
        raise HTTPException(status_code=400, detail="Provide either 'text' or 'url'.")

    if payload.url:
        text_content = scrape_url(payload.url)
        source = "url"
    else:
        text_content = payload.text or ""
        source = "text"

    if len(text_content) < 20:
        raise HTTPException(status_code=400, detail="Input text is too short to process.")

    session_id = uuid.uuid4().hex[:12]

    forward_payload = {
        "session_id": session_id,
        "email": payload.email,
        "text": text_content,
        "source": source,
        "source_url": payload.url or "",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            n8n_resp = client.post(N8N_WEBHOOK_URL, json=forward_payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach n8n: {exc}") from exc

    try:
        n8n_body: dict | str = n8n_resp.json()
    except ValueError:
        n8n_body = n8n_resp.text

    if n8n_resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"n8n returned {n8n_resp.status_code}: {n8n_body}",
        )

    return ProcessResponse(
        status="accepted",
        session_id=session_id,
        source=source,
        chars_sent=len(text_content),
        n8n_status_code=n8n_resp.status_code,
        n8n_response=n8n_body,
    )
