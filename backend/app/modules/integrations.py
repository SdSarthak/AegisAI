"""Integration helpers for Jira and Linear."""

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import json


class JiraClient:
    """Client for Jira REST API."""

    def __init__(self, base_url: str, api_key: str, username: str):
        """
        Initialize Jira client.
        
        Args:
            base_url: Base URL of Jira instance (e.g., https://jira.company.com)
            api_key: API token or personal access token
            username: Email or username for Basic auth
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.session = requests.Session()
        self.session.auth = (username, api_key)
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Jira."""
        try:
            response = self.session.get(f"{self.base_url}/rest/api/3/myself")
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "message": f"Connected as {data.get('displayName', 'User')}", "details": data}
            else:
                return {"success": False, "message": f"Failed: {response.status_code}", "details": response.text}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def create_issue(
        self,
        project_key: str,
        issue_type: str,
        summary: str,
        description: str,
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create an issue in Jira.
        
        Args:
            project_key: Project key (e.g., "PROJ")
            issue_type: Issue type (e.g., "Task", "Bug", "Story")
            summary: Issue summary
            description: Issue description
            labels: Optional labels
            custom_fields: Optional custom field mappings
            
        Returns:
            Dict with issue_key and URL
        """
        try:
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "issuetype": {"name": issue_type},
                    "summary": summary,
                    "description": description,
                }
            }
            if labels:
                payload["fields"]["labels"] = labels
            if custom_fields:
                payload["fields"].update(custom_fields)

            response = self.session.post(f"{self.base_url}/rest/api/3/issue", json=payload)
            if response.status_code in [200, 201]:
                data = response.json()
                issue_key = data.get("key")
                return {
                    "success": True,
                    "external_ticket_id": issue_key,
                    "external_url": f"{self.base_url}/browse/{issue_key}",
                    "details": data,
                }
            else:
                return {"success": False, "message": response.text}
        except Exception as e:
            return {"success": False, "message": str(e)}


class LinearClient:
    """Client for Linear API (GraphQL)."""

    def __init__(self, api_key: str):
        """
        Initialize Linear client.
        
        Args:
            api_key: Personal API key from Linear
        """
        self.api_key = api_key
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Linear."""
        try:
            query = """
            query {
              viewer {
                id
                email
                name
              }
            }
            """
            response = requests.post(self.base_url, json={"query": query}, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    return {"success": False, "message": data["errors"][0].get("message", "Unknown error")}
                viewer = data.get("data", {}).get("viewer", {})
                return {"success": True, "message": f"Connected as {viewer.get('name', 'User')}", "details": viewer}
            else:
                return {"success": False, "message": f"Failed: {response.status_code}", "details": response.text}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def create_issue(
        self,
        team_id: str,
        title: str,
        description: str,
        priority: int = 2,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create an issue in Linear.
        
        Args:
            team_id: Team ID
            title: Issue title
            description: Issue description
            priority: Priority (0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low)
            labels: Optional label names
            
        Returns:
            Dict with issue_id and URL
        """
        try:
            mutation = """
            mutation CreateIssue($input: IssueCreateInput!) {
              issueCreate(input: $input) {
                success
                issue {
                  id
                  identifier
                  url
                }
              }
            }
            """
            input_data = {
                "teamId": team_id,
                "title": title,
                "description": description,
                "priority": priority,
            }
            if labels:
                input_data["labelIds"] = labels

            response = requests.post(
                self.base_url,
                json={"query": mutation, "variables": {"input": input_data}},
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    return {"success": False, "message": data["errors"][0].get("message", "Unknown error")}
                issue_data = data.get("data", {}).get("issueCreate", {}).get("issue", {})
                if issue_data:
                    return {
                        "success": True,
                        "external_ticket_id": issue_data.get("identifier"),
                        "external_url": issue_data.get("url"),
                        "details": issue_data,
                    }
                else:
                    return {"success": False, "message": "No issue returned"}
            else:
                return {"success": False, "message": f"Failed: {response.status_code}", "details": response.text}
        except Exception as e:
            return {"success": False, "message": str(e)}
