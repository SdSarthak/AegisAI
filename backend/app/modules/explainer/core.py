import re
from typing import Dict, Any, List

RULES = {
    "UNACCEPTABLE": {
        "keywords": [
            "social scoring",
            "manipulat",
            "subliminal",
            "exploits vulnerable",
            "remote biometric",
            "real-time biometric",
            "behavioral manipulation"
        ],
        "reasons": [
            "Automated evaluation or social scoring by public authorities (Article 5)",
            "Use of subliminal or manipulative techniques impairing free decisions",
            "Exploits vulnerabilities of specific groups causing harm",
            "Real-time remote biometric identification in publicly accessible spaces"
        ],
        "articles": [
            {
                "article": "EU AI Act Article 5(1)(c)",
                "title": "Prohibited Social Scoring",
                "summary": "AI systems used by public authorities for social scoring are prohibited outright."
            },
            {
                "article": "EU AI Act Article 5(1)(a)",
                "title": "Subliminal Manipulation",
                "summary": "AI systems placing subliminal or manipulative techniques that distort human behavior are prohibited."
            },
            {
                "article": "EU AI Act Article 5(1)(b)",
                "title": "Vulnerable Groups Exploitation",
                "summary": "AI systems exploiting vulnerabilities of specific groups (e.g., children, elderly) are prohibited."
            },
            {
                "article": "EU AI Act Article 5(1)(h)",
                "title": "Real-time Biometrics",
                "summary": "Real-time remote biometric identification in public spaces for law enforcement is prohibited, subject to narrow exceptions."
            }
        ],
        "recommendations": [
            "Immediately cease development or deployment of this system.",
            "Consult legal counsel regarding Article 5 compliance obligations.",
            "Review whether any Article 5 narrow exceptions apply to your use case."
        ],
        "similar_systems": [
            "Government citizen ranking systems",
            "Manipulative commercial audio/video generators",
            "Public space surveillance face-matchers"
        ]
    },
    "HIGH": {
        "categories": [
            {
                "name": "Employment & HR",
                "keywords": [
                    "recruitment", "screening", "ranking", "candidates", "cv screening", "job application", "candidate ranking",
                    "employee evaluation", "performance evaluation", "hiring", "hiring decision"
                ],
                "reasons": [
                    "Automated decision-making affecting employment opportunities",
                    "System makes decisions about natural persons without human oversight",
                    "Impacts fundamental rights — right to work"
                ],
                "articles": [
                    {
                        "article": "EU AI Act Annex III, Point 4",
                        "title": "High-risk AI in Employment",
                        "summary": "AI systems used for recruitment or selection of natural persons are classified as high-risk"
                    }
                ],
                "similar_systems": ["CV screening tools", "Applicant tracking systems", "Employee performance monitoring tools"]
            },
            {
                "name": "Credit & Essential Services",
                "keywords": [
                    "credit scoring", "creditworthiness", "loan evaluation",
                    "insurance pricing", "financial resource access"
                ],
                "reasons": [
                    "AI system evaluates creditworthiness or access to financial resources",
                    "Determines essential services and access to financial opportunities"
                ],
                "articles": [
                    {
                        "article": "EU AI Act Annex III, Point 5",
                        "title": "High-risk AI in Essential Services",
                        "summary": "AI systems used to evaluate the creditworthiness of natural persons or establish their credit score are classified as high-risk"
                    }
                ],
                "similar_systems": ["Credit scoring algorithms", "Automated underwriting platforms"]
            },
            {
                "name": "Biometrics",
                "keywords": [
                    "biometric verification", "biometric categorization",
                    "facial recognition", "fingerprint identification"
                ],
                "reasons": [
                    "Uses biometric data for identification or categorization of natural persons"
                ],
                "articles": [
                    {
                        "article": "EU AI Act Annex III, Point 1",
                        "title": "High-risk Biometric Systems",
                        "summary": "AI systems intended to be used for biometric identification or categorization of natural persons are high-risk"
                    }
                ],
                "similar_systems": ["Facial recognition platforms", "Biometric access control systems"]
            },
            {
                "name": "Critical Infrastructure",
                "keywords": [
                    "critical infrastructure", "traffic management", "water supply", "power grid"
                ],
                "reasons": [
                    "AI system used as safety components in critical infrastructure management"
                ],
                "articles": [
                    {
                        "article": "EU AI Act Annex III, Point 2",
                        "title": "High-risk Critical Infrastructure",
                        "summary": "AI systems intended to be used as safety components in the management and operation of critical digital infrastructure, road traffic, and water, gas, heating or electricity supply are high-risk"
                    }
                ],
                "similar_systems": ["Industrial control safety agents", "Smart grid load balancers"]
            },
            {
                "name": "Education",
                "keywords": [
                    "grading", "exam proctoring", "admissions decision", "student evaluation"
                ],
                "reasons": [
                    "AI system determines access to education or evaluates student performance"
                ],
                "articles": [
                    {
                        "article": "EU AI Act Annex III, Point 3",
                        "title": "High-risk Education Systems",
                        "summary": "AI systems used to determine access or admission, or to evaluate learning outcomes of natural persons in education and vocational training are high-risk"
                    }
                ],
                "similar_systems": ["Automated essay graders", "Proctoring algorithms"]
            },
            {
                "name": "Law Enforcement & Justice",
                "keywords": [
                    "law enforcement", "border control", "migration", "asylum", "court assisting", "judicial decision"
                ],
                "reasons": [
                    "AI system assisting law enforcement, border control, or judicial authorities"
                ],
                "articles": [
                    {
                        "article": "EU AI Act Annex III, Point 6",
                        "title": "High-risk Law Enforcement Tools",
                        "summary": "AI systems used by law enforcement authorities for assessing risks, profiling, or predicting crimes are high-risk"
                    }
                ],
                "similar_systems": ["Recidivism risk calculators", "Border control facial matchers"]
            }
        ],
        "general_articles": [
            {
                "article": "EU AI Act Article 9",
                "title": "Risk Management System",
                "summary": "High-risk AI systems shall be subject to a risk management system throughout their lifecycle"
            }
        ],
        "recommendations": [
            "Implement human oversight mechanism before final decisions",
            "Generate Technical Documentation (required under Article 11)",
            "Conduct conformity assessment before deployment",
            "Register system in EU database under Article 71",
            "Establish data governance and quality practices for training data (Article 10)"
        ]
    },
    "LIMITED": {
        "keywords": [
            "chatbot", "virtual assistant", "conversational ai", "deepfake",
            "emotion recognition", "generative text", "synthetic content"
        ],
        "reasons": [
            "System directly interacts with natural persons or generates synthetic content"
        ],
        "articles": [
            {
                "article": "EU AI Act Article 52",
                "title": "Transparency Obligations",
                "summary": "Providers shall ensure that AI systems intended to interact with natural persons are designed and developed in such a way that natural persons are informed that they are interacting with an AI system."
            }
        ],
        "recommendations": [
            "Implement transparency notices to inform users they are interacting with AI (Article 52)",
            "Label all AI-generated or manipulated (synthetic) text, audio, and visual content clearly.",
            "Document the mechanism used to disclose AI presence to users."
        ],
        "similar_systems": [
            "Conversational agents",
            "Generative image editors",
            "Synthetic voice synthesizers"
        ]
    },
    "MINIMAL": {
        "keywords": [
            "spam filter", "video game", "recommendation engine", "search queries", "chess"
        ],
        "reasons": [
            "System does not present significant threats to fundamental rights or safety"
        ],
        "articles": [
            {
                "article": "EU AI Act Article 95",
                "title": "Voluntary Codes of Conduct",
                "summary": "Commission and Member States shall encourage providers of non-high-risk AI systems to draw up and implement voluntary codes of conduct."
            }
        ],
        "recommendations": [
            "Establish voluntary codes of ethical conduct for your AI system.",
            "Monitor local and global regulatory framework updates.",
            "Maintain standard AI governance and security documentation."
        ],
        "similar_systems": [
            "Email spam filters",
            "Product recommendation engines",
            "In-game AI players"
        ]
    }
}

def explain_system_risk(description: str) -> Dict[str, Any]:
    desc_lower = description.lower()
    
    # 1. Check Unacceptable practices
    unacceptable_matches = []
    for kw in RULES["UNACCEPTABLE"]["keywords"]:
        if kw in desc_lower:
            unacceptable_matches.append(kw)
            
    if unacceptable_matches:
        matched_articles = []
        # Find which articles correspond to unacceptable keywords
        for idx, kw in enumerate(RULES["UNACCEPTABLE"]["keywords"]):
            if kw in unacceptable_matches and idx < len(RULES["UNACCEPTABLE"]["articles"]):
                matched_articles.append(RULES["UNACCEPTABLE"]["articles"][idx])
        # Fallback to ensure we always have at least one matched article
        if not matched_articles:
            matched_articles = [RULES["UNACCEPTABLE"]["articles"][0]]
            
        confidence = 0.99
        return {
            "risk_level": "UNACCEPTABLE",
            "confidence": confidence,
            "reasons": RULES["UNACCEPTABLE"]["reasons"],
            "relevant_articles": matched_articles,
            "recommendations": RULES["UNACCEPTABLE"]["recommendations"],
            "triggered_keywords": unacceptable_matches,
            "similar_systems": RULES["UNACCEPTABLE"]["similar_systems"]
        }
        
    # 2. Check High Risk
    high_matches = []
    matched_categories = []
    for cat in RULES["HIGH"]["categories"]:
        cat_matches = []
        for kw in cat["keywords"]:
            if kw in desc_lower:
                cat_matches.append(kw)
        if cat_matches:
            high_matches.extend(cat_matches)
            matched_categories.append(cat)
            
    if high_matches:
        reasons = []
        relevant_articles = []
        similar_systems = []
        
        for cat in matched_categories:
            reasons.extend(cat["reasons"])
            relevant_articles.extend(cat["articles"])
            similar_systems.extend(cat["similar_systems"])
            
        # Add general high-risk articles and recommendations
        relevant_articles.extend(RULES["HIGH"]["general_articles"])
        
        # Calculate confidence
        confidence = min(0.98, 0.90 + 0.01 * len(high_matches))
        
        return {
            "risk_level": "HIGH",
            "confidence": round(confidence, 2),
            "reasons": list(set(reasons)),
            "relevant_articles": relevant_articles,
            "recommendations": RULES["HIGH"]["recommendations"],
            "triggered_keywords": list(set(high_matches)),
            "similar_systems": list(set(similar_systems))
        }
        
    # 3. Check Limited Risk
    limited_matches = []
    for kw in RULES["LIMITED"]["keywords"]:
        if kw in desc_lower:
            limited_matches.append(kw)
            
    if limited_matches:
        confidence = min(0.92, 0.80 + 0.02 * len(limited_matches))
        return {
            "risk_level": "LIMITED",
            "confidence": round(confidence, 2),
            "reasons": RULES["LIMITED"]["reasons"],
            "relevant_articles": RULES["LIMITED"]["articles"],
            "recommendations": RULES["LIMITED"]["recommendations"],
            "triggered_keywords": limited_matches,
            "similar_systems": RULES["LIMITED"]["similar_systems"]
        }
        
    # 4. Check Minimal Risk (by keyword or fallback)
    minimal_matches = []
    for kw in RULES["MINIMAL"]["keywords"]:
        if kw in desc_lower:
            minimal_matches.append(kw)
            
    confidence = 0.75
    return {
        "risk_level": "MINIMAL",
        "confidence": confidence,
        "reasons": RULES["MINIMAL"]["reasons"],
        "relevant_articles": RULES["MINIMAL"]["articles"],
        "recommendations": RULES["MINIMAL"]["recommendations"],
        "triggered_keywords": minimal_matches,
        "similar_systems": RULES["MINIMAL"]["similar_systems"]
    }
