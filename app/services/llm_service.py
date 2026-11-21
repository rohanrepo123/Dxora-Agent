"""Groq model call and Pydantic validation for generated report JSON."""

import json
import time

from fastapi import HTTPException
from langchain_groq import ChatGroq
from pydantic import ValidationError

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.schemas import Report, fill_missing_fields


def generate_report(evidence_json: str) -> tuple[Report, dict, float]:
    """Call the single configured Groq model and return report, usage and latency."""
    if not GROQ_API_KEY:
        raise HTTPException(503, "Configure GROQ_API_KEY in the environment.")

    model = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY,
                     max_tokens=6000, timeout=90, max_retries=0)
    structured_model = model.with_structured_output(
        Report, method="json_mode", include_raw=True
    )
    from app.services.competitor_service import build_analysis_prompt

    started = time.monotonic()
    result = structured_model.invoke([
        ("system", build_analysis_prompt()),
        ("human", evidence_json),
    ])
    elapsed = round(time.monotonic() - started, 2)
    report = result["parsed"]

    if report is None:
        # Fill only omitted fields. Existing model values are retained and then
        # validated against the full response schema.
        content = result["raw"].content if result.get("raw") else ""
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        try:
            report = Report.model_validate(fill_missing_fields(Report, json.loads(content)))
        except (ValueError, TypeError, ValidationError) as exc:
            raise ValueError(f"Model JSON does not match the report schema: {exc}") from exc

    usage = getattr(result["raw"], "usage_metadata", {}) or {}
    return report, usage, elapsed

