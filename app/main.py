"""FastAPI app exposing the single assignment endpoint."""

import logging

from fastapi import FastAPI, HTTPException

from app.schemas import LinkAnalysisRequest, LinkAnalysisResponse
from app.services.analysis_service import analyze_website

app = FastAPI(title="Website Link Analysis", version="1.0")
logger = logging.getLogger(__name__)


@app.post("/link-analysis", response_model=LinkAnalysisResponse,
          responses={502: {"description": "Website or Groq analysis failed"}})
def link_analysis(request: LinkAnalysisRequest):
    """Read a public website and return structured marketing and SEO insights."""
    try:
        return analyze_website(str(request.url), request.max_pages)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Link analysis failed")
        raise HTTPException(502, f"Analysis failed ({type(exc).__name__}).") from exc

