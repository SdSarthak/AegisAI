from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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

    def get_risk_factor(self, id: str) -> RiskFactor | None:
        for risk_factor in self.risk_factors:
            if risk_factor.id == id:
                return risk_factor
        return None


class RegulationFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regulation: RegulationBody
