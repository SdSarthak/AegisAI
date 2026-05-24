from pydantic import BaseModel, Field
from typing import List

class ExplainRequest(BaseModel):
    description: str = Field(
        ...,
        description="An AI system description to classify and explain",
        json_schema_extra={"example": "An AI system that automatically screens job applications and ranks candidates"}
    )

class ArticleInfo(BaseModel):
    article: str
    title: str
    summary: str

class ExplainResponse(BaseModel):
    risk_level: str
    confidence: float
    reasons: List[str]
    relevant_articles: List[ArticleInfo]
    recommendations: List[str]
    triggered_keywords: List[str]
    similar_systems: List[str]
