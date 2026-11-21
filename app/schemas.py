"""Pydantic request and response schemas used by FastAPI and the LLM."""

from typing import Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Record(BaseModel):
    # Reject misspelled keys so the API and generated model output stay clear.
    model_config = ConfigDict(extra="forbid")


class LinkAnalysisRequest(Record):
    url: HttpUrl
    max_pages: int = Field(default=3, ge=1, le=3)


class Brand(Record):
    name: str
    summary: str
    category: str
    products_and_services: list[str]


class Competitor(Record):
    name: str
    comparable_because: str
    possible_strengths: list[str]
    possible_gaps: list[str]
    basis: Literal["AI suggestion; independent verification needed"]


class CompetitorAnalysis(Record):
    competitors: list[Competitor]
    brand_advantages: list[str]
    positioning_opportunities: list[str]


Platform = Literal["Google", "Facebook", "Instagram", "LinkedIn", "X"]


class SearchQuery(Record):
    query: str
    platform: Platform
    intent: str
    business_relevance: str
    target_audience: str


class SEOImprovements(Record):
    primary_keyword: str
    secondary_keywords: list[str]
    long_tail_keywords: list[str]
    business_keywords: list[str]
    recommended_title: str
    meta_description: str
    supporting_content: list[str]


class Service(Record):
    name: str
    description: str
    target_industry: str
    target_customer: str
    main_benefit: str
    basis: Literal["stated", "inferred"]
    source_url: str
    evidence_quote: str


class TargetAudience(Record):
    primary_audience: list[str]
    secondary_audience: list[str]
    industry_segments: list[str]
    business_types: list[str]
    customer_profiles: list[str]
    geographical_focus: list[str]
    needs_and_challenges: list[str]
    interests: list[str]
    recommended_marketing_segments: list[str]


class Analysis(Record):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery]
    seo_improvements: SEOImprovements
    top_services: list[Service]
    target_audience: TargetAudience


class Report(Record):
    brand: Brand
    analysis: Analysis
    limitations: list[str]


class LinkAnalysisResponse(Report):
    success: bool
    website: str
    sources: list[str]
    model: str
    usage: dict
    metrics: dict


class Page(Record):
    url: str
    title: str
    meta_description: str
    text: str


class WebsiteEvidence(Record):
    pages: list[Page]


def _empty_value(annotation):
    """Return a safe default for a schema field omitted by a model."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is list:
        return []
    if origin is Literal:
        return args[0]
    if annotation is str:
        return ""
    if annotation is bool:
        return False
    if annotation is int or annotation is float:
        return 0
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return fill_missing_fields(annotation, {})
    return None


def fill_missing_fields(model_type: type[BaseModel], value: dict) -> dict:
    """Recursively fill missing fields; existing model-provided values remain intact."""
    for name, field in model_type.model_fields.items():
        if name not in value:
            value[name] = field.get_default() if not field.is_required() else _empty_value(field.annotation)
        elif isinstance(value[name], dict) and isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel):
            fill_missing_fields(field.annotation, value[name])
    return value

