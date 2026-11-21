"""LangGraph workflow plus response metrics and CSV recording."""

import csv
import time
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import GROQ_MODEL, METRICS_FILE
from app.schemas import LinkAnalysisResponse, Platform, SearchQuery, WebsiteEvidence
from app.services.llm_service import generate_report
from app.services.website_extractor import collect_website


class AnalysisState(TypedDict, total=False):
    url: str
    max_pages: int
    evidence: WebsiteEvidence
    response: LinkAnalysisResponse


def collect_node(state: AnalysisState) -> dict:
    return {"evidence": collect_website(state["url"], state.get("max_pages", 3))}


def analyze_node(state: AnalysisState) -> dict:
    evidence = state["evidence"]
    report, usage, latency = generate_report(evidence.model_dump_json())
    pages = evidence.pages

    # Guarantee exactly one distinct query per required platform.
    platforms = list(Platform.__args__)
    original = report.analysis.target_search_queries
    queries = []
    for index, platform in enumerate(platforms):
        if original:
            query = original[index % len(original)].model_copy(update={"platform": platform})
            if any(item.query.casefold() == query.query.casefold() for item in queries):
                query = query.model_copy(update={"query": f"{query.query} {platform}"})
        else:
            query = SearchQuery(query=f"{report.brand.category} {report.brand.name}",
                platform=platform, intent="commercial", business_relevance="Find relevant offerings",
                target_audience="Potential customers")
        queries.append(query)
    report.analysis.target_search_queries = queries
    report.analysis.top_services = report.analysis.top_services[:5]

    quote_matches = 0
    for service in report.analysis.top_services:
        source = next((page for page in pages if page.url == service.source_url), None)
        quote = " ".join(service.evidence_quote.split())
        if source and quote and quote in " ".join(source.text.split()):
            quote_matches += 1

    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    cost = (round(input_tokens * 0.15 / 1_000_000 + output_tokens * 0.60 / 1_000_000, 8)
            if input_tokens is not None and output_tokens is not None else None)
    metrics = {
        "latency_seconds": latency, "provider": "groq", "model": GROQ_MODEL,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "estimated_cost_usd": cost, "json_valid": True,
        "services_with_matching_quotes": quote_matches,
        "content_characters": sum(len(page.text) for page in pages),
        "competitor_suggestions": len(report.analysis.competitor_analysis.competitors),
        "query_count": len(queries), "accuracy_score": None,
        "competitor_relevance_score": None,
        "quality_note": "Accuracy and competitor relevance require human scoring against labeled examples.",
    }
    response = LinkAnalysisResponse(**report.model_dump(), success=True, website=state["url"],
        sources=[page.url for page in pages], model=GROQ_MODEL, usage=usage, metrics=metrics)

    # Keep append-only request measurements beside the application.
    row = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "website": state["url"], "provider": "groq", "model": GROQ_MODEL,
        "latency_seconds": latency, "input_tokens": input_tokens,
        "output_tokens": output_tokens, "estimated_cost_usd": cost,
        "json_valid": True, "content_characters": metrics["content_characters"],
        "services_returned": len(report.analysis.top_services),
        "services_with_matching_quotes": quote_matches,
        "competitors_suggested": metrics["competitor_suggestions"],
        "queries_returned": len(queries), "seo_recommendations_present":
        bool(report.analysis.seo_improvements.primary_keyword),
        "accuracy_score": "", "competitor_relevance_score": "",
    }
    with METRICS_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=row.keys())
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(row)
    return {"response": response}


# LangGraph runs extraction first, then analysis over the collected evidence.
workflow_builder = StateGraph(AnalysisState)
workflow_builder.add_node("collect", collect_node)
workflow_builder.add_node("analyze", analyze_node)
workflow_builder.add_edge(START, "collect")
workflow_builder.add_edge("collect", "analyze")
workflow_builder.add_edge("analyze", END)
analysis_workflow = workflow_builder.compile()


def analyze_website(url: str, max_pages: int = 3) -> LinkAnalysisResponse:
    result = analysis_workflow.invoke({"url": url, "max_pages": max_pages})
    return result["response"]

