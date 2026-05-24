import base64
import httpx


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str, project_key: str):
        self.base_url = base_url.rstrip("/")
        self.project_key = project_key
        token = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_issue(self, summary: str, description: str) -> dict:
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
                },
                "issuetype": {"name": "Task"},
            }
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.base_url}/rest/api/3/issue",
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "ticket_id": data.get("key"),
                "ticket_url": f"{self.base_url}/browse/{data.get('key')}",
            }