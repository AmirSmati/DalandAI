import os
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pydantic import AnyUrl

from mcp import StdioServerParameters
from mcp.client.auth import (
    AuthorizationCodeResult,
    OAuthClientProvider,
)
from mcp.shared.auth import OAuthClientMetadata

from config.settings import TAVILY_API_KEY
from mcp_client.storage import FileTokenStorage


NOTION_MCP_URL = "https://mcp.notion.com/mcp"

TAVILY_MCP_URL = (
    f"https://mcp.tavily.com/mcp/"
    f"?tavilyApiKey={TAVILY_API_KEY}"
)
EMAIL_MCP_URL = "http://127.0.0.1:8000/mcp"

#EXA 
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
EXA_MCP_URL = "https://mcp.exa.ai/mcp"
async def open_browser(authorization_url: str):

    print("\nOpening browser for MCP authorization...")
    print(authorization_url)

    webbrowser.open(authorization_url)


async def wait_for_callback() -> AuthorizationCodeResult:

    print("\nAfter authorizing, paste the callback URL here:")

    redirect_url = input("> ")

    params = parse_qs(
        urlparse(redirect_url).query
    )

    return AuthorizationCodeResult(
        code=params["code"][0],
        state=params["state"][0],
        iss=params["iss"][0] if "iss" in params else None,
    )


def create_notion_oauth():

    return OAuthClientProvider(

        server_url=NOTION_MCP_URL,

        client_metadata=OAuthClientMetadata(
            client_name="My Agent",

            redirect_uris=[
                AnyUrl(
                    "http://localhost:3030/callback"
                )
            ],

            token_endpoint_auth_method="none",

            grant_types=[
                "authorization_code",
                "refresh_token",
            ],

            response_types=["code"],
        ),

        storage=FileTokenStorage(
            "mcp_client/notion_oauth.json"
        ),

        redirect_handler=open_browser,
        callback_handler=wait_for_callback,
    )


def create_google_calendar_params():
    token_env = os.getenv("TOKEN_FILE_PATH", ".gcp-saved-tokens.json")
    token_path = Path(token_env)
    if not token_path.is_absolute():
        token_path = (Path(__file__).resolve().parent.parent / token_path).resolve()

    return StdioServerParameters(
        command="uvx",
        args=["calendar-mcp-server"],
        env={
            "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", ""),
            "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "TOKEN_FILE_PATH": str(token_path),
        },
    )

