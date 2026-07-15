"""
Pydantic schemas for the Risk Classification Explainer API.

These models define the request and response structure for
POST /api/v1/classification/explain
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.ai_system import RiskLevel


class ExplainRequest(BaseModel):
    """Request model — just a plain text description of the AI system."""

    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Plain text description of the AI system to classify and explain.",
        examples=[
            "An AI system that automatically screens job applications and ranks candidates based on their CVs.",
            "A chatbot that answers customer support queries on our website.",
            "An AI model that predicts creditworthiness for loan applications.",
        ],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "description": "An AI system that screens job applications and ranks candidates automatically without human review."
            }
        }


class TriggeredFactor(BaseModel):
    """A single EU AI Act risk factor that was triggered by the description."""

    factor_id: str = Field(..., description="ID of the triggered risk factor")
    question: str = Field(..., description="The questionnaire question this maps to")
    article: str = Field(..., description="Relevant EU AI Act article")
    triggered_by: List[str] = Field(
        ..., description="Keywords in the description that triggered this factor"
    )


class RelevantArticle(BaseModel):
    """A relevant EU AI Act article with summary."""

    article: str = Field(..., description="Article reference e.g. 'Annex III point 4(a)'")
    title: str = Field(..., description="Short title of the article")
    summary: str = Field(..., description="Plain English summary of what this article requires")


class ExplainResponse(BaseModel):
    """Full explainability report for an AI system description."""

    # Core classification
    risk_level: RiskLevel = Field(..., description="Classified risk level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0")

    # Explanation
    triggered_factors: List[TriggeredFactor] = Field(
        ..., description="Risk factors triggered by the description"
    )
    triggered_keywords: List[str] = Field(
        ..., description="Keywords extracted from the description that influenced classification"
    )

    # Legal context
    relevant_articles: List[RelevantArticle] = Field(
        ..., description="Relevant EU AI Act articles with plain English summaries"
    )

    # Action items
    reasons: List[str] = Field(..., description="Human-readable reasons for this classification")
    requirements: List[str] = Field(..., description="Legal requirements for this risk level")
    recommendations: List[str] = Field(..., description="Concrete next steps to achieve compliance")

    # Meta
    description_analyzed: str = Field(..., description="The input description that was analyzed")
    disclaimer: str = Field(
        default="This is a preliminary AI-powered classification. Always consult a qualified legal expert for formal EU AI Act compliance assessment.",
        description="Legal disclaimer"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "risk_level": "HIGH",
                "confidence": 0.94,
                "triggered_factors": [
                    {
                        "factor_id": "hr_recruitment_screening",
                        "question": "Is the system used for recruitment, CV screening, candidate filtering, or candidate ranking?",
                        "article": "Annex III point 4(a)",
                        "triggered_by": ["screens", "job applications", "ranks candidates"]
                    }
                ],
                "triggered_keywords": ["screens", "job applications", "ranks", "candidates", "automatically"],
                "relevant_articles": [
                    {
                        "article": "Annex III point 4(a)",
                        "title": "High-risk AI in Employment",
                        "summary": "AI systems used for recruitment or selection of natural persons are classified as high-risk"
                    }
                ],
                "reasons": ["AI systems used for recruitment and CV screening are HIGH risk under Annex III"],
                "requirements": ["Implement risk management system (Article 9)", "Enable human oversight (Article 14)"],
                "recommendations": ["Complete the full risk assessment questionnaire", "Implement human oversight before final hiring decisions"],
                "description_analyzed": "An AI system that screens job applications and ranks candidates automatically.",
                "disclaimer": "This is a preliminary AI-powered classification. Always consult a qualified legal expert for formal EU AI Act compliance assessment."
            }
        }
