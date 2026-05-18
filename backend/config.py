"""
Configuration — loads all environment variables for the 6 MCP servers.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Azure OpenAI ──
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# ── Tavily Search ──
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# ── Notion ──
NOTION_API_KEY = os.getenv("NOTION_API_KEY")

# ── Slack ──
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "medical-alerts")

# ── Google Calendar ──
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", 
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
)

# ── MCP Server commands ──
# These define how each MCP server is launched as a subprocess
MCP_SERVERS = {
    "triage": {
        "command": "python",
        "args": ["mcp_servers/triage/server.py"],
        "env": {},
        "description": "Custom medical triage — severity classification and specialty recommendation"
    },
    "tavily": {
        "command": "npx",
        "args": ["-y", "tavily-mcp@latest"],
        "env": {
            "TAVILY_API_KEY": TAVILY_API_KEY or ""
        },
        "description": "Web search — validates triage against real medical sources"
    },
    "notion": {
        "command": "npx",
        "args": ["-y", "@notionhq/notion-mcp-server"],
        "env": {
            "OPENAPI_MCP_HEADERS": f'{{"Authorization": "Bearer {NOTION_API_KEY}", "Notion-Version": "2022-06-28"}}'
        },
        "description": "Hospital database — doctor directory, patient records"
    },
    "google_calendar": {
        "command": "npx",
        "args": ["-y", "mcp-google-calendar"],
        "env": {
            "GOOGLE_CREDENTIALS_PATH": os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json"))
        },
        "description": "Doctor scheduling — check availability and book appointments"
    },
    "slack": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"],
        "env": {
            "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN or "",
            "SLACK_TEAM_ID": os.getenv("SLACK_TEAM_ID", "")
        },
        "description": "Staff notifications — alert medical team for priority cases"
    },
    "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "description": "Patient memory — remembers patient history across conversations"
    }
}
