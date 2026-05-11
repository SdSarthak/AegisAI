from app.models.ai_system import RiskAssessment


def calculate_compliance_score(assessment: RiskAssessment) -> float:
    """
    Calculate weighted compliance score from assessment sub-scores.
    Returns a value between 0.0 and 100.0.
    """

    scores = [
        assessment.data_governance_score,
        assessment.transparency_score,
        assessment.human_oversight_score,
        assessment.robustness_score,
    ]

    valid_scores = [score for score in scores if score is not None]

    if not valid_scores:
        return float(assessment.overall_score or 0)

    return round(sum(valid_scores) / len(valid_scores), 2)