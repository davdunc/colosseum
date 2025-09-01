# ...existing imports...
import requests
from .base import MCPServer

class FetchMCPServer(MCPServer):
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.api_key = api_key

    def get_resource(self, resource_type, **kwargs):
        # Example: fetch resource from the fetch MCP server
        url = f"{self.base_url}/resource/{resource_type}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.get(url, params=kwargs, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
