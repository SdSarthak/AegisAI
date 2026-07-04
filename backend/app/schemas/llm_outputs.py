from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictLLMOutput(BaseModel):
    """Base model for LLM outputs that must not accept undeclared fields."""

    model_config = ConfigDict(extra="forbid")


class RiskControl(StrictLLMOutput):
    risk: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    likelihood: str = Field(..., min_length=1)
    mitigation: str = Field(..., min_length=1)
    residual_risk: str = Field(..., min_length=1)


class ComplianceRequirement(StrictLLMOutput):
    requirement: str = Field(..., min_length=1)
    evidence: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)


class TechnicalDocumentationOutput(StrictLLMOutput):
    document_type: Literal["technical_documentation"]
    system_name: str = Field(..., min_length=1)
    provider_name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    intended_purpose: str = Field(..., min_length=1)
    system_description: str = Field(..., min_length=1)
    system_architecture: str = Field(..., min_length=1)
    input_data: str = Field(..., min_length=1)
    output_specification: str = Field(..., min_length=1)
    training_data: str = Field(..., min_length=1)
    validation_testing: str = Field(..., min_length=1)
    performance_metrics: str = Field(..., min_length=1)
    risk_management: list[RiskControl] = Field(..., min_length=1)
    human_oversight: str = Field(..., min_length=1)
    logging_monitoring: str = Field(..., min_length=1)
    cybersecurity: str = Field(..., min_length=1)
    lifecycle_management: str = Field(..., min_length=1)


class RiskAssessmentOutput(StrictLLMOutput):
    document_type: Literal["risk_assessment"]
    system_name: str = Field(..., min_length=1)
    provider_name: str = Field(..., min_length=1)
    intended_purpose: str = Field(..., min_length=1)
    risk_classification: str = Field(..., min_length=1)
    classification_rationale: str = Field(..., min_length=1)
    foreseeable_misuse: list[str] = Field(..., min_length=1)
    identified_risks: list[RiskControl] = Field(..., min_length=1)
    data_governance_risks: list[str] = Field(..., min_length=1)
    transparency_risks: list[str] = Field(..., min_length=1)
    human_oversight_risks: list[str] = Field(..., min_length=1)
    robustness_cybersecurity_risks: list[str] = Field(..., min_length=1)
    overall_residual_risk: str = Field(..., min_length=1)
    monitoring_plan: str = Field(..., min_length=1)


class ConformityDeclarationOutput(StrictLLMOutput):
    document_type: Literal["conformity_declaration"]
    system_name: str = Field(..., min_length=1)
    provider_name: str = Field(..., min_length=1)
    provider_address: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    intended_purpose: str = Field(..., min_length=1)
    risk_classification: str = Field(..., min_length=1)
    applicable_regulation: Literal["Regulation (EU) 2024/1689"]
    harmonised_standards: list[str] = Field(..., min_length=1)
    conformity_assessment_procedure: str = Field(..., min_length=1)
    requirements: list[ComplianceRequirement] = Field(..., min_length=1)
    declaration_statement: str = Field(..., min_length=1)
    signatory_name: str = Field(..., min_length=1)
    signatory_title: str = Field(..., min_length=1)
    place_and_date: str = Field(..., min_length=1)
