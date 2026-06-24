"""
Risk Classification Explainer Engine

Converts a plain-text AI system description into a structured
RiskClassificationRequest by extracting keywords and mapping them
to EU AI Act risk factors — then enriches the result with
legal article references and plain-English explanations.

No external LLM or API required — pure Python, works offline.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from app.models.ai_system import RiskLevel
from app.schemas.ai_system import RiskClassificationRequest
from app.schemas.explain import (
    ExplainRequest,
    ExplainResponse,
    RelevantArticle,
    TriggeredFactor,
)


# ── Keyword → Risk Factor mapping ──
# Each entry maps a risk factor ID to a list of keyword patterns
# that indicate this factor is relevant.

FACTOR_KEYWORDS: dict[str, List[str]] = {
    "hr_recruitment_screening": [
        "recruit", "recruitment", "hiring", "hire", "cv", "resume",
        "job application", "candidate screening", "candidate ranking",
        "applicant", "shortlist", "talent acquisition", "staffing",
        "screen job", "filter candidate", "rank candidate",
    ],
    "hr_promotion_termination": [
        "promot", "terminat", "fire employee", "layoff", "performance evaluat",
        "employee evaluat", "performance review", "performance", "task allocat",
        "workforce manag", "employee monitor",
    ],
    "credit_worthiness": [
        "credit", "loan", "creditworthiness", "credit score", "lending",
        "mortgage", "debt", "repayment", "credit risk", "financial eligib",
        "credit decision",
    ],
    "insurance_risk_assessment": [
        "insurance", "insur", "premium", "underwriting", "actuarial",
        "risk pricing", "coverage eligib", "claim assessment",
    ],
    "is_safety_component": [
        "safety component", "safety system", "safety critical",
        "autonomous vehicle", "self-driving", "medical device",
        "surgical robot", "aviation", "railway", "nuclear",
        "industrial safety", "emergency system",
    ],
    "affects_fundamental_rights": [
        "fundamental right", "education access", "essential service",
        "housing", "welfare benefit", "social service",
        "employment opportunit", "discriminat", "equal opportunit",
    ],
    "uses_biometric_data": [
        "biometric", "facial recognition", "face recognit",
        "fingerprint", "iris scan", "voice recognit", "gait recognit",
        "biometric identif", "biometric verif",
    ],
    "makes_automated_decisions": [
        "automated decision", "automatic decision", "without human",
        "no human review", "fully automated", "autonomous decision",
        "algorithmic decision", "decision without oversight",
    ],
    "law_enforcement": [
        "law enforcement", "police", "criminal", "surveillance",
        "crime predict", "predictive polic", "suspect identif",
        "court", "legal decision", "parole", "sentencing",
    ],
    "border_control": [
        "border control", "immigration", "asylum", "visa",
        "migration", "customs", "passport control", "entry decision",
    ],
    "justice_system": [
        "judicial", "court decision", "legal outcome", "judge",
        "legal ruling", "criminal justice", "parole board",
    ],
    "interacts_with_humans": [
        "chatbot", "virtual assistant", "conversational ai",
        "customer service bot", "chat interface", "voice assistant",
        "dialogue system", "interactive ai", "user interaction",
    ],
    "generates_synthetic_content": [
        "deepfake", "synthetic content", "ai generated", "generate image",
        "generate video", "generate audio", "text generation",
        "content generation", "synthetic media", "fake video",
    ],
    "emotion_recognition": [
        "emotion recognit", "sentiment analys", "mood detect",
        "affect recognit", "facial emotion", "emotion detect",
        "emotional state",
    ],
    "biometric_categorization": [
        "biometric categor", "categorize by appearance",
        "gender classification", "age classification",
        "ethnicity classif",
    ],
}


# ── EU AI Act article reference library ──

ARTICLE_LIBRARY: dict[str, RelevantArticle] = {
    "hr_recruitment_screening": RelevantArticle(
        article="Annex III point 4(a)",
        title="High-risk AI in Employment — Recruitment",
        summary="AI systems used for recruitment, CV screening, or candidate ranking are classified as HIGH risk. They require conformity assessment, human oversight, and technical documentation before deployment.",
    ),
    "hr_promotion_termination": RelevantArticle(
        article="Annex III point 4(b)",
        title="High-risk AI in Employment — Promotion & Termination",
        summary="AI used for promotion, termination, performance evaluation, or task allocation decisions is HIGH risk and requires full compliance with Chapter III Section 2 obligations.",
    ),
    "credit_worthiness": RelevantArticle(
        article="Annex III point 5(b)",
        title="High-risk AI in Finance — Creditworthiness",
        summary="AI systems that evaluate creditworthiness or access to financial resources are HIGH risk, requiring transparency, human oversight, and data governance measures.",
    ),
    "insurance_risk_assessment": RelevantArticle(
        article="Annex III point 5(c)",
        title="High-risk AI in Finance — Insurance",
        summary="AI used for insurance risk assessment, pricing, or eligibility is HIGH risk under EU AI Act Annex III.",
    ),
    "is_safety_component": RelevantArticle(
        article="Article 6(1)",
        title="Safety Component Classification",
        summary="AI systems used as safety components of products covered by EU harmonisation legislation are HIGH risk and require third-party conformity assessment.",
    ),
    "affects_fundamental_rights": RelevantArticle(
        article="Article 6(2)",
        title="Fundamental Rights Impact",
        summary="AI systems that affect fundamental rights including employment, education, and access to essential services fall under HIGH risk classification.",
    ),
    "uses_biometric_data": RelevantArticle(
        article="Annex III point 1",
        title="Biometric Identification Systems",
        summary="AI systems using biometric data for remote identification are HIGH risk. Real-time biometric identification in public spaces is largely prohibited under Article 5.",
    ),
    "makes_automated_decisions": RelevantArticle(
        article="Article 6 / Annex III",
        title="Automated Decision-Making",
        summary="Systems making consequential automated decisions without meaningful human review are HIGH risk. Article 14 requires human oversight mechanisms.",
    ),
    "law_enforcement": RelevantArticle(
        article="Annex III point 6",
        title="Law Enforcement AI",
        summary="AI used by or for law enforcement — including crime prediction and suspect identification — is HIGH risk and subject to strict transparency and oversight requirements.",
    ),
    "border_control": RelevantArticle(
        article="Annex III point 7",
        title="Migration and Border Control AI",
        summary="AI used for migration, asylum, or border control decisions is HIGH risk, requiring conformity assessment and human oversight before deployment.",
    ),
    "justice_system": RelevantArticle(
        article="Annex III point 8",
        title="Administration of Justice AI",
        summary="AI assisting judicial authorities or influencing legal outcomes is HIGH risk. Such systems must not replace judicial decision-making.",
    ),
    "interacts_with_humans": RelevantArticle(
        article="Article 52(1)",
        title="Transparency — Human Interaction",
        summary="AI systems that interact directly with humans (e.g. chatbots) must inform users they are interacting with AI, unless this is obvious from context.",
    ),
    "generates_synthetic_content": RelevantArticle(
        article="Article 52(3)",
        title="Transparency — Synthetic Content",
        summary="AI systems generating synthetic audio, images, video, or text must label the content as AI-generated to prevent deception.",
    ),
    "emotion_recognition": RelevantArticle(
        article="Article 52(3)",
        title="Transparency — Emotion Recognition",
        summary="Operators of emotion recognition systems must inform the persons exposed to the system about its operation.",
    ),
    "biometric_categorization": RelevantArticle(
        article="Article 52 / Annex III",
        title="Biometric Categorization",
        summary="AI systems that categorize individuals based on biometric data into groups (e.g. by gender, ethnicity) face strict transparency and potentially HIGH risk obligations.",
    ),
}


# ── Recommendations per risk level ──

RECOMMENDATIONS: dict[RiskLevel, List[str]] = {
    RiskLevel.HIGH: [
        "Complete the full EU AI Act conformity assessment before deployment",
        "Implement a documented risk management system (Article 9)",
        "Establish data governance and quality procedures (Article 10)",
        "Prepare and maintain technical documentation (Article 11)",
        "Enable comprehensive logging and record-keeping (Article 12)",
        "Implement clear transparency notices for affected persons (Article 13)",
        "Set up meaningful human oversight mechanisms (Article 14)",
        "Ensure accuracy, robustness, and cybersecurity measures (Article 15)",
        "Register the AI system in the EU AI Act database (Article 71) before deployment",
        "Conduct a fundamental rights impact assessment",
    ],
    RiskLevel.LIMITED: [
        "Implement clear disclosure notices informing users they interact with AI",
        "Label any AI-generated content appropriately",
        "Document all interaction points with users",
        "Review and update transparency mechanisms regularly",
        "Monitor for any scope changes that could elevate risk level",
    ],
    RiskLevel.MINIMAL: [
        "Consider adopting voluntary codes of conduct",
        "Monitor EU AI Act regulatory updates — scope may expand",
        "Document your AI governance practices proactively",
        "Implement basic transparency practices as good practice",
    ],
}


def _normalize(text: str) -> str:
    """Lowercase and normalize text for keyword matching."""
    return text.lower().strip()


def _extract_keywords(description: str) -> List[str]:
    """Extract meaningful keywords from the description, deduplicating while preserving order."""
    normalized = _normalize(description)
    # Remove common stop words, keep meaningful terms
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "that", "this",
        "which", "who", "what", "when", "where", "how", "and", "or",
        "but", "in", "on", "at", "to", "for", "of", "with", "by",
        "from", "as", "into", "through", "during", "our", "their",
        "its", "it", "we", "they", "system", "ai", "model", "tool",
    }
    words = re.findall(r'\b[a-z]{2,}\b', normalized)
    print(f'DEBUG words={words}', file=sys.stderr)
    # Deduplicate while preserving first-occurrence order
    seen: set[str] = set()
    unique: list[str] = []
    for w in words:
        if w not in stop_words and w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def _match_factors(
    description: str,
) -> List[Tuple[str, List[str]]]:
    """
    Match description against all risk factor keyword patterns.
    Returns list of (factor_id, matched_keywords) tuples.
    """
    normalized = _normalize(description)
    matched = []

    for factor_id, keywords in FACTOR_KEYWORDS.items():
        triggered_by = []
        for kw in keywords:
            if kw in normalized:
                triggered_by.append(kw)
        if triggered_by:
            matched.append((factor_id, triggered_by))

    return matched


def _build_questionnaire(
    matched_factor_ids: List[str],
) -> RiskClassificationRequest:
    """
    Build a RiskClassificationRequest from matched factor IDs.
    All factors default to False; matched ones are set to True.
    """
    kwargs = {
         "use_case_category"           : "other",
        "is_safety_component"         : "is_safety_component" in matched_factor_ids,
        "affects_fundamental_rights"  : "affects_fundamental_rights" in matched_factor_ids,
        "uses_biometric_data"         : "uses_biometric_data" in matched_factor_ids,
        "makes_automated_decisions"   : "makes_automated_decisions" in matched_factor_ids,
        "hr_recruitment_screening"    : "hr_recruitment_screening" in matched_factor_ids,
        "hr_promotion_termination"    : "hr_promotion_termination" in matched_factor_ids,
        "credit_worthiness"           : "credit_worthiness" in matched_factor_ids,
        "insurance_risk_assessment"   : "insurance_risk_assessment" in matched_factor_ids,
        "law_enforcement"             : "law_enforcement" in matched_factor_ids,
        "border_control"              : "border_control" in matched_factor_ids,
        "justice_system"              : "justice_system" in matched_factor_ids,
        "interacts_with_humans"       : "interacts_with_humans" in matched_factor_ids,
        "generates_synthetic_content" : "generates_synthetic_content" in matched_factor_ids,
        "emotion_recognition"         : "emotion_recognition" in matched_factor_ids,
        "biometric_categorization"    : "biometric_categorization" in matched_factor_ids,
    }
    return RiskClassificationRequest(**kwargs)


def _compute_confidence(
    matched_factors: List[Tuple[str, List[str]]],
    risk_level: RiskLevel,
) -> float:
    """
    Compute confidence score based on number of matched factors
    and keyword match strength.
    """
    if not matched_factors:
        return 0.75  # minimal risk with no matches = moderate confidence

    total_keywords = sum(len(kws) for _, kws in matched_factors)

    # More keyword matches = higher confidence
    if total_keywords >= 5:
        base = 0.92
    elif total_keywords >= 3:
        base = 0.85
    elif total_keywords >= 2:
        base = 0.78
    else:
        base = 0.70

    # Multiple factors triggered = higher confidence
    if len(matched_factors) >= 3:
        base = min(base + 0.05, 0.97)

    return round(base, 2)


def explain_risk(request: ExplainRequest) -> ExplainResponse:
    """
    Main explainer function.

    Takes a plain-text AI system description and returns a full
    explainability report including risk level, triggered factors,
    relevant EU AI Act articles, and actionable recommendations.
    """
    description = request.description

    # Step 1: Match description against risk factor keywords
    matched = _match_factors(description)
    matched_factor_ids = [fid for fid, _ in matched]

    # Step 2: Build questionnaire and classify using existing logic
    from app.api.v1.classification import classify_risk
    questionnaire = _build_questionnaire(matched_factor_ids)
    classification = classify_risk(questionnaire)

    # Step 3: Build triggered factors list
    triggered_factors = []
    from app.api.v1.classification import QUESTIONNAIRE_RISK_FACTORS
    factor_map = {f.id: f for f in QUESTIONNAIRE_RISK_FACTORS}

    for factor_id, keywords in matched:
        factor = factor_map.get(factor_id)
        if factor:
            triggered_factors.append(
                TriggeredFactor(
                    factor_id=factor_id,
                    question=factor.question,
                    article=factor.article,
                    triggered_by=keywords,
                )
            )

    # Step 4: Collect relevant articles
    relevant_articles = []
    seen_articles = set()
    for factor_id in matched_factor_ids:
        article = ARTICLE_LIBRARY.get(factor_id)
        if article and article.article not in seen_articles:
            relevant_articles.append(article)
            seen_articles.add(article.article)

    # Step 5: Extract surface keywords
    triggered_keywords = list({
        kw for _, kws in matched for kw in kws
    })

    # Step 6: Compute confidence
    confidence = _compute_confidence(matched, classification.risk_level)

    # Step 7: Get recommendations
    recommendations = RECOMMENDATIONS.get(
        classification.risk_level,
        RECOMMENDATIONS[RiskLevel.MINIMAL]
    )

    return ExplainResponse(
        risk_level=classification.risk_level,
        confidence=confidence,
        triggered_factors=triggered_factors,
        triggered_keywords=triggered_keywords,
        relevant_articles=relevant_articles,
        reasons=classification.reasons,
        requirements=classification.requirements,
        recommendations=recommendations,
        description_analyzed=description,
    )
