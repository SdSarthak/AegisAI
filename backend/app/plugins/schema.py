from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SeverityEnum = Literal["prohibited", "high", "limited", "minimal"]


class RiskFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    severity: SeverityEnum


class ComplianceQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    maps_to: str


class RegulationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    risk_factors: list[RiskFactor] = Field(min_length=1)
    prohibited_uses: list[str] = Field(min_length=1)
    required_documents: list[str] = Field(min_length=1)
    compliance_questions: list[ComplianceQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_question_mappings(self) -> "RegulationBody":
        risk_factor_ids = {risk_factor.id for risk_factor in self.risk_factors}
        invalid_mappings = sorted(
            {
                question.maps_to
                for question in self.compliance_questions
                if question.maps_to not in risk_factor_ids
            }
        )
        if invalid_mappings:
            raise ValueError(
                "Invalid maps_to references: " + ", ".join(invalid_mappings)
            )
        return self

    def get_risk_factor(self, id: str) -> RiskFactor | None:
        for risk_factor in self.risk_factors:
            if risk_factor.id == id:
                return risk_factor
        return None


class RegulationFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regulation: RegulationBody
