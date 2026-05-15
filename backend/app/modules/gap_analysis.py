"""Gap analysis module — compute compliance gaps from risk assessment."""

from typing import List, Dict, Any, Optional
from app.models.ai_system import RiskLevel, ComplianceStatus


def analyze_gaps(risk_level: RiskLevel, questionnaire_responses: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyze compliance gaps based on risk level and questionnaire responses.
    
    Returns list of gaps with type, severity, description, and recommendation.
    """
    gaps = []

    # UNACCEPTABLE systems have immediate prohibition gaps
    if risk_level == RiskLevel.UNACCEPTABLE:
        gaps.append({
            "gap_type": "prohibited_use",
            "severity": "critical",
            "description": "This AI system falls under EU AI Act Article 5 (Prohibited Practices)",
            "recommendation": "This system cannot be deployed or operated. Consider redesigning to remove prohibited characteristics.",
            "affected_articles": ["Article 5"],
        })
        return gaps

    # HIGH risk gaps
    if risk_level == RiskLevel.HIGH:
        # Check for explainability gap
        if not questionnaire_responses.get("explainability_documentation"):
            gaps.append({
                "gap_type": "explainability",
                "severity": "high",
                "description": "Lack of documented explainability measures for high-risk AI system",
                "recommendation": "Implement explainability mechanisms (LIME, SHAP, rule extraction) and document them per Article 14",
                "affected_articles": ["Article 13", "Article 14"],
            })

        # Check for human oversight gap
        if not questionnaire_responses.get("human_oversight"):
            gaps.append({
                "gap_type": "oversight",
                "severity": "high",
                "description": "No human oversight mechanisms documented for high-risk system",
                "recommendation": "Establish human-in-the-loop processes and document oversight procedures per Article 14(4)",
                "affected_articles": ["Article 14"],
            })

        # Check for data governance gap
        if not questionnaire_responses.get("data_governance"):
            gaps.append({
                "gap_type": "data_governance",
                "severity": "high",
                "description": "Data governance procedures not documented",
                "recommendation": "Implement and document data governance framework covering bias, quality, and management per Article 10",
                "affected_articles": ["Article 10"],
            })

        # Check for documentation gap
        if not questionnaire_responses.get("technical_documentation"):
            gaps.append({
                "gap_type": "documentation",
                "severity": "high",
                "description": "Technical documentation incomplete or missing",
                "recommendation": "Prepare comprehensive technical documentation including system design, testing, and performance data per Article 13",
                "affected_articles": ["Article 13"],
            })

        # Check for risk management gap
        if not questionnaire_responses.get("risk_management_system"):
            gaps.append({
                "gap_type": "risk_management",
                "severity": "high",
                "description": "Risk management system not implemented",
                "recommendation": "Establish a risk management system following Annex IV framework",
                "affected_articles": ["Annex IV"],
            })

        # Check for monitoring gap
        if not questionnaire_responses.get("post_market_monitoring"):
            gaps.append({
                "gap_type": "monitoring",
                "severity": "high",
                "description": "Post-market monitoring plan not documented",
                "recommendation": "Develop post-market monitoring plan to track system performance and identify new risks per Article 17",
                "affected_articles": ["Article 17"],
            })

    # LIMITED risk gaps (transparency)
    if risk_level in [RiskLevel.LIMITED, RiskLevel.HIGH]:
        if questionnaire_responses.get("interacts_with_humans") and not questionnaire_responses.get(
            "transparency_notice"
        ):
            gaps.append({
                "gap_type": "transparency",
                "severity": "medium",
                "description": "Transparency obligations not met for systems interacting with users",
                "recommendation": "Provide clear notices when users interact with AI systems per Article 52",
                "affected_articles": ["Article 52"],
            })

        if questionnaire_responses.get("generates_synthetic_content") and not questionnaire_responses.get(
            "synthetic_content_disclosure"
        ):
            gaps.append({
                "gap_type": "synthetic_content_disclosure",
                "severity": "medium",
                "description": "AI-generated content not properly disclosed",
                "recommendation": "Ensure users are informed when interacting with synthetic content per Article 52",
                "affected_articles": ["Article 52"],
            })

    # Fundamental rights gaps
    if questionnaire_responses.get("affects_fundamental_rights") and not questionnaire_responses.get(
        "fundamental_rights_mitigation"
    ):
        gaps.append({
            "gap_type": "fundamental_rights",
            "severity": "high",
            "description": "No documented mitigation for fundamental rights impacts",
            "recommendation": "Perform and document fundamental rights impact assessment with mitigation measures",
            "affected_articles": ["Recital 27"],
        })

    return gaps


def calculate_compliance_score(risk_level: RiskLevel, gaps: List[Dict[str, Any]]) -> float:
    """
    Calculate overall compliance score (0-100) based on risk level and identified gaps.
    
    Args:
        risk_level: Classification risk level
        gaps: List of identified gaps
        
    Returns:
        Compliance score (0-100)
    """
    if risk_level == RiskLevel.UNACCEPTABLE:
        return 0.0

    # Start with risk level baseline
    if risk_level == RiskLevel.HIGH:
        score = 30.0  # High risk starts at 30%
    elif risk_level == RiskLevel.LIMITED:
        score = 60.0  # Limited risk starts at 60%
    else:  # MINIMAL
        score = 85.0  # Minimal risk starts at 85%

    # Deduct points per gap
    gap_deduction = {
        "critical": 25,
        "high": 15,
        "medium": 8,
        "low": 3,
    }

    for gap in gaps:
        severity = gap.get("severity", "medium")
        deduction = gap_deduction.get(severity, 5)
        score = max(0, score - deduction)

    return score
