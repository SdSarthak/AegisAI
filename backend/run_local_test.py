import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.api.v1.classification import classify_risk
from app.schemas.ai_system import RiskClassificationRequest

# Create request with the new factor enabled
req = RiskClassificationRequest(
    use_case_category="education",
    education_vocational_training=True
)

res = classify_risk(req)
print("\n--- TEST RESULTS ---")
print("Risk Level:", res.risk_level.value)
print("Reasons:", res.reasons)
print("--------------------\n")
