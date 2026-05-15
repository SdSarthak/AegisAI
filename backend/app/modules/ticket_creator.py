"""Ticket creation utilities for integration workflows."""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.user import User
from app.models.ai_system import AISystem, RiskLevel
from app.models.integration import IntegrationSettings, IntegrationTicket, IntegrationType
from app.modules.integrations import JiraClient, LinearClient
from app.modules.gap_analysis import analyze_gaps


def create_tickets_for_classification(
    db: Session,
    ai_system: AISystem,
    user: User,
    risk_level: RiskLevel,
    questionnaire_responses: Dict[str, Any],
):
    """
    Create tickets in configured integrations when classification HIGH or UNACCEPTABLE.
    
    Args:
        db: Database session
        ai_system: AI system being classified
        user: System owner
        risk_level: Classification result
        questionnaire_responses: Questionnaire data
    """
    if risk_level not in [RiskLevel.HIGH, RiskLevel.UNACCEPTABLE]:
        return  # Only create tickets for HIGH and UNACCEPTABLE

    # Get all active integrations for the user
    integrations = db.query(IntegrationSettings).filter(
        IntegrationSettings.user_id == user.id,
        IntegrationSettings.is_active == True,
    ).all()

    # Analyze compliance gaps
    gaps = analyze_gaps(risk_level, questionnaire_responses)

    for integration in integrations:
        # Check if we should create tickets for this risk level
        should_create = False
        if risk_level == RiskLevel.HIGH and integration.create_on_high:
            should_create = True
        elif risk_level == RiskLevel.UNACCEPTABLE and integration.create_on_unacceptable:
            should_create = True

        if not should_create:
            continue

        try:
            if integration.integration_type == IntegrationType.JIRA:
                _create_jira_tickets(
                    db, integration, ai_system, risk_level, gaps, integration.create_gap_tickets
                )
            elif integration.integration_type == IntegrationType.LINEAR:
                _create_linear_tickets(
                    db, integration, ai_system, risk_level, gaps, integration.create_gap_tickets
                )
        except Exception as e:
            # Log error but don't fail the classification
            print(f"Error creating tickets for integration {integration.id}: {e}")


def _create_jira_tickets(
    db: Session,
    integration: IntegrationSettings,
    ai_system: AISystem,
    risk_level: RiskLevel,
    gaps: List[Dict[str, Any]],
    create_gap_tickets: bool,
):
    """Create Jira tickets for classification result."""
    client = JiraClient(integration.base_url, integration.api_key, integration.username or "")

    # Create main classification ticket
    summary = f"[{risk_level.value.upper()}] {ai_system.name} - EU AI Act Compliance"
    description = f"""
AI System: {ai_system.name}
Risk Level: {risk_level.value.upper()}
ID: {ai_system.id}

This AI system has been classified as {risk_level.value.upper()} risk under the EU AI Act.

Compliance Gaps Identified:
"""
    for gap in gaps:
        description += f"\n- {gap['gap_type']}: {gap['description']}"

    result = client.create_issue(
        project_key=integration.project_key,
        issue_type="Task",
        summary=summary,
        description=description,
        labels=["aegisai", "compliance", f"risk-{risk_level.value}"],
    )

    if result.get("success"):
        ticket = IntegrationTicket(
            integration_id=integration.id,
            ai_system_id=ai_system.id,
            external_ticket_id=result.get("external_ticket_id"),
            external_url=result.get("external_url"),
            ticket_type="Task",
            link_reason=f"classification_{risk_level.value}",
        )
        db.add(ticket)
        db.commit()

    # Create gap tickets if enabled
    if create_gap_tickets:
        for gap in gaps:
            gap_type = gap.get("gap_type", "unknown")
            issue_type = integration.gap_ticket_template.get(gap_type, "Task")

            gap_summary = f"[Gap] {gap_type}: {ai_system.name}"
            gap_description = f"""
System: {ai_system.name} (ID: {ai_system.id})
Gap Type: {gap_type}
Severity: {gap.get('severity', 'unknown')}

{gap.get('description', '')}

Recommendation:
{gap.get('recommendation', '')}

Affected Articles: {', '.join(gap.get('affected_articles', []))}
"""

            result = client.create_issue(
                project_key=integration.project_key,
                issue_type=issue_type,
                summary=gap_summary,
                description=gap_description,
                labels=["aegisai", f"gap-{gap_type}", f"risk-{gap.get('severity')}"],
            )

            if result.get("success"):
                ticket = IntegrationTicket(
                    integration_id=integration.id,
                    ai_system_id=ai_system.id,
                    external_ticket_id=result.get("external_ticket_id"),
                    external_url=result.get("external_url"),
                    ticket_type=issue_type,
                    link_reason=f"gap_{gap_type}",
                    gap_type=gap_type,
                )
                db.add(ticket)
        db.commit()


def _create_linear_tickets(
    db: Session,
    integration: IntegrationSettings,
    ai_system: AISystem,
    risk_level: RiskLevel,
    gaps: List[Dict[str, Any]],
    create_gap_tickets: bool,
):
    """Create Linear tickets for classification result."""
    client = LinearClient(integration.api_key)

    # Create main classification ticket
    title = f"[{risk_level.value.upper()}] {ai_system.name} - EU AI Act Compliance"
    description = f"""
AI System: {ai_system.name}
Risk Level: {risk_level.value.upper()}
ID: {ai_system.id}

This AI system has been classified as {risk_level.value.upper()} risk under the EU AI Act.

Compliance Gaps Identified:
"""
    for gap in gaps:
        description += f"\n- {gap['gap_type']}: {gap['description']}"

    # Map severity to Linear priority
    priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
    priority = priority_map.get(gaps[0].get("severity", "medium") if gaps else "medium", 3)

    result = client.create_issue(
        team_id=integration.team_id,
        title=title,
        description=description,
        priority=priority,
        labels=["aegisai", "compliance", f"risk-{risk_level.value}"],
    )

    if result.get("success"):
        ticket = IntegrationTicket(
            integration_id=integration.id,
            ai_system_id=ai_system.id,
            external_ticket_id=result.get("external_ticket_id"),
            external_url=result.get("external_url"),
            ticket_type="Issue",
            link_reason=f"classification_{risk_level.value}",
        )
        db.add(ticket)
        db.commit()

    # Create gap tickets if enabled
    if create_gap_tickets:
        for gap in gaps:
            gap_type = gap.get("gap_type", "unknown")

            gap_title = f"[Gap] {gap_type}: {ai_system.name}"
            gap_description = f"""
System: {ai_system.name} (ID: {ai_system.id})
Gap Type: {gap_type}
Severity: {gap.get('severity', 'unknown')}

{gap.get('description', '')}

Recommendation:
{gap.get('recommendation', '')}

Affected Articles: {', '.join(gap.get('affected_articles', []))}
"""

            gap_priority = priority_map.get(gap.get("severity", "medium"), 3)

            result = client.create_issue(
                team_id=integration.team_id,
                title=gap_title,
                description=gap_description,
                priority=gap_priority,
                labels=["aegisai", f"gap-{gap_type}", f"risk-{gap.get('severity')}"],
            )

            if result.get("success"):
                ticket = IntegrationTicket(
                    integration_id=integration.id,
                    ai_system_id=ai_system.id,
                    external_ticket_id=result.get("external_ticket_id"),
                    external_url=result.get("external_url"),
                    ticket_type="Issue",
                    link_reason=f"gap_{gap_type}",
                    gap_type=gap_type,
                )
                db.add(ticket)
        db.commit()
