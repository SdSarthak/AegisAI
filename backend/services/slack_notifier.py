"""
Slack notifier service for SLA breach alerts.

Builds a Slack Block Kit payload for a given helpdesk ticket and
sends it to a configured Slack webhook URL.
"""

from __future__ import annotations

import os
from typing import Any


def build_slack_payload(ticket: dict[str, Any]) -> dict[str, Any]:
    """Build a Slack Block Kit attachment payload for an SLA breach alert.

    Args:
        ticket: A dict representing the helpdesk ticket. Expected keys
            (all optional except 'id'):
            - id: ticket identifier (str)
            - subject: ticket subject line (str)
            - priority: ticket priority (str)
            - company / company_id: company name (str)
            - assigned_team: team responsible (str)
            - sla_breach_at: ISO-8601 breach timestamp (str)

    Returns:
        A Slack-compatible payload dict with an ``attachments`` list.
    """
    ticket_id = ticket.get("id", "N/A")
    subject = ticket.get("subject") or "Untitled ticket"
    priority = str(ticket.get("priority") or "unknown").upper()
    company = (
        ticket.get("company")
        or ticket.get("company_id")
        or "UNKNOWN"
    )
    assigned_team = ticket.get("assigned_team") or "Unassigned"
    breach_time = ticket.get("sla_breach_at") or "N/A"

    base_url = os.getenv("HELPDESK_BASE_URL", "https://helpdesk.app")
    ticket_url = f"{base_url}/tickets/{ticket_id}"

    return {
        "attachments": [
            {
                "color": "#FFA500",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🚨 SLA Breach: #{ticket_id}",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Ticket:*\n<{ticket_url}|#{ticket_id}>",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Priority:*\n{priority}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Subject:*\n{subject}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Assigned Team:*\n{assigned_team}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Company:*\n{company}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Breach Time:*\n{breach_time}",
                            },
                        ],
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "🔔 *Action required* — This ticket has breached its SLA deadline and requires immediate attention.",
                            }
                        ],
                    },
                    {"type": "divider"},
                ],
            }
        ]
    }
