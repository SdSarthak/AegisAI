import httpx

LINEAR_API_URL = "https://api.linear.app/graphql"


class LinearClient:
    def __init__(self, api_key: str, team_id: str):
        self.team_id = team_id
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }

    async def create_issue(self, title: str, description: str) -> dict:
        query = """
        mutation CreateIssue($title: String!, $description: String, $teamId: String!) {
          issueCreate(input: {title: $title, description: $description, teamId: $teamId}) {
            success
            issue { id title url }
          }
        }
        """
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                LINEAR_API_URL,
                json={"query": query, "variables": {
                    "title": title,
                    "description": description,
                    "teamId": self.team_id,
                }},
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()
            issue = data.get("data", {}).get("issueCreate", {}).get("issue", {})
            return {
                "ticket_id": issue.get("id"),
                "ticket_url": issue.get("url"),
            }