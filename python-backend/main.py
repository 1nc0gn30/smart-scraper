import os
import logging
from typing import Optional

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse

from scraper import (
    scrape_and_analyze,
    SUPPORTED_TASKS,
    SUPPORTED_MODES,
)

PORT = int(os.getenv("PORT", 8000))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 18))
RAW_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in RAW_ORIGINS.split(",") if o.strip()]

# API_KEY: when set, both Netlify function and direct clients must send X-API-Key
API_KEY = os.getenv("API_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape-bot")

# CORS: In production, set ALLOWED_ORIGINS to your Netlify domain(s), e.g. "https://your-site.netlify.app"
# Never use "*" in production if you can avoid it.
cors_origins = ["*"] if RAW_ORIGINS.strip() == "*" else ALLOWED_ORIGINS

@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = "OPEN (no key)" if not API_KEY else "KEY REQUIRED"
    logger.info("Backend starting | CORS=%s | API key protection: %s", cors_origins, mode)
    if RAW_ORIGINS == "*":
        logger.warning("ALLOWED_ORIGINS=* — set your Netlify site origin(s) in production!")
    yield
    logger.info("Backend shutting down")

app = FastAPI(
    title="Smart Scraper API",
    description="FastAPI backend powering StreamlitNetlifyCollab. Handles scraping + analysis. Designed to be called from Netlify Functions (after auth) or directly from a Streamlit dashboard.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    url: Optional[str] = None
    query: Optional[str] = None
    mode: str = Field(default="url", description="url or keyword")
    task: str = Field(default="headlines")
    max_results: int = Field(default=50, ge=1, le=200)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v not in SUPPORTED_MODES:
            raise ValueError(f"mode must be one of {SUPPORTED_MODES}")
        return v

    @field_validator("task")
    @classmethod
    def validate_task(cls, v):
        if v not in SUPPORTED_TASKS:
            raise ValueError(f"task must be one of {list(SUPPORTED_TASKS.keys())}")
        return v

    @field_validator("url", "query")
    @classmethod
    def validate_input(cls, v, info):
        # At least one of url or query must be present
        data = info.data
        if not data.get("url") and not data.get("query"):
            # This will be validated at call site too
            pass
        if info.field_name == "url" and v:
            parsed = urlparse(v)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError("Invalid URL. Must start with http(s)://")
        return v


def verify_api_key(x_api_key: Optional[str] = Header(default=None)):
    """API key verification.
    - If API_KEY env var is set → header X-API-Key must match (defense-in-depth).
    - If not set → open (useful for pure local dev / trusted internal Streamlit).
    """
    if API_KEY:
        if not x_api_key or x_api_key != API_KEY:
            logger.warning("Rejected request without valid X-API-Key")
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
    return True


# Import the reusable core
# (scraper.py contains fetch logic + all analysis handlers)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "backend": "Smart Scraper API (FastAPI)",
        "version": "2.0.0",
        "supported_tasks": list(SUPPORTED_TASKS.keys()),
        "supported_modes": SUPPORTED_MODES,
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest, _ok: bool = Depends(verify_api_key)):
    """Main analysis endpoint. Used by both Netlify Functions and Streamlit app."""
    if not req.url and not req.query:
        raise HTTPException(status_code=400, detail="Provide either 'url' or 'query'")

    target = req.url or req.query
    logger.info("Analyze request: mode=%s task=%s target=%s", req.mode, req.task, target[:80])

    try:
        result = scrape_and_analyze(
            url=req.url,
            query=req.query,
            mode=req.mode,
            task=req.task,
            max_results=req.max_results,
            timeout=REQUEST_TIMEOUT,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=502, detail=f"Backend processing error: {str(exc)[:200]}")


# Back-compat alias used by some older clients / the initial MVP
@app.post("/scrape")
def scrape_compat(req: AnalyzeRequest, _ok: bool = Depends(verify_api_key)):
    return analyze(req)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level="info",
    )
