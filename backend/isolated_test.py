from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

class RiskLevel(Enum):
    MINIMAL = "minimal"
    LIMITED = "limited"
    HIGH = "high"
    UNACCEPTABLE = "unacceptable"

class RiskClassificationRequest(BaseModel):
    use_case_category: str
    is_safety_component: bool = False
    affects_fundamental_rights: bool = False
    uses_biometric_data: bool = False
    makes_automated_decisions: bool = True
    hr_recruitment_screening: bool = False
    hr_promotion_termination: bool = False
    credit_worthiness: bool = False
    insurance_risk_assessment: bool = False
    law_enforcement: bool = False
    border_control: bool = False
    justice_system: bool = False
    education_vocational_training: bool = False
    interacts_with_humans: bool = True
    generates_synthetic_content: bool = False
    emotion_recognition: bool = False
    biometric_categorization: bool = False

class RiskClassificationResponse(BaseModel):
    risk_level: RiskLevel
    confidence: float
    reasons: List[str]
    requirements: List[str]
    next_steps: List[str]

def classify_risk(data: RiskClassificationRequest) -> RiskClassificationResponse:
    reasons = []
    requirements = []
    risk_level = RiskLevel.MINIMAL
    confidence = 0.9

    high_risk_indicators = []

    if data.hr_recruitment_screening or data.hr_promotion_termination:
        high_risk_indicators.append("HR recruitment/management AI system")
        reasons.append("AI systems used for recruitment, CV screening, or employment decisions are classified as HIGH risk under Annex III")
        requirements.extend(["Implement risk management system (Article 9)", "Ensure data governance and quality (Article 10)"])

    if data.credit_worthiness or data.insurance_risk_assessment:
        high_risk_indicators.append("Credit/insurance assessment AI")
        reasons.append("AI for creditworthiness or insurance risk assessment is HIGH risk under Annex III")

    if data.education_vocational_training:
        high_risk_indicators.append("Education/vocational training AI")
        reasons.append("AI used for determining access to education or vocational training is HIGH risk under Annex III")

    if data.is_safety_component:
        high_risk_indicators.append("Safety component of a product")
        reasons.append("AI used as a safety component requires HIGH risk compliance")

    if data.affects_fundamental_rights:
        high_risk_indicators.append("Affects fundamental rights")
        reasons.append("System impacts fundamental rights (employment, education, essential services)")

    if data.law_enforcement or data.border_control or data.justice_system:
        high_risk_indicators.append("Law enforcement/justice system use")
        reasons.append("Use in law enforcement, border control, or justice is HIGH risk")

    if high_risk_indicators:
        risk_level = RiskLevel.HIGH
    elif data.interacts_with_humans or data.emotion_recognition or data.generates_synthetic_content:
        risk_level = RiskLevel.LIMITED
        if data.interacts_with_humans:
            reasons.append("System interacts directly with humans (e.g., chatbot)")
            requirements.append("Inform users they are interacting with AI (Article 52)")
    else:
        reasons.append("System does not fall into high-risk or limited-risk categories")
        requirements.append("No mandatory requirements, but voluntary codes of conduct encouraged")

    next_steps = []
    if risk_level == RiskLevel.HIGH:
        next_steps = ["Complete the full risk assessment questionnaire", "Document your AI system's technical specifications"]
    elif risk_level == RiskLevel.LIMITED:
        next_steps = ["Implement transparency notices for users", "Document your disclosure mechanisms"]
    else:
        next_steps = ["Consider voluntary compliance measures"]

    return RiskClassificationResponse(
        risk_level=risk_level,
        confidence=confidence,
        reasons=reasons,
        requirements=requirements,
        next_steps=next_steps,
    )

print("Testing Classification Logic...")
req = RiskClassificationRequest(
    use_case_category="education",
    education_vocational_training=True,
    interacts_with_humans=False
)
res = classify_risk(req)
print(f"Result Risk Level: {res.risk_level.name}")
print(f"Reasons: {res.reasons}")
