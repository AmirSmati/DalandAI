from mcp_client.client import MCPClient
from mcp_client.config import (
    EMAIL_MCP_URL,
    NOTION_MCP_URL,
    TAVILY_MCP_URL,
    EXA_MCP_URL,
    create_google_calendar_params,
    create_notion_oauth,
)

import asyncio

import json
class MCPManager:

    def __init__(self):

        self.clients = {}
        self.tool_servers = {}
    async def connect_all(self):

        # ----------------------------------------------------
        # Tavily MCP Client (Web Search)
        # ----------------------------------------------------
        try:
            #tavily_client = MCPClient(
             #   name="tavily",
              #  url=TAVILY_MCP_URL,
            #)
            #await tavily_client.connect()
            #self.clients["tavily"] = tavily_client
            exa_client = MCPClient(
                name ="exa",
                url= EXA_MCP_URL
            )
            await exa_client.connect()
            self.clients["exa"] = exa_client
        except Exception as e:
            #print(f"[MCP] Could not connect to Tavily: {e}")
            print(f"[MCP] Could not connect to Exa: {e}")
        # ----------------------------------------------------
        # Notion MCP Client
        # ----------------------------------------------------
        try:
            notion_oauth = create_notion_oauth()

            notion_client = MCPClient(
                name="notion",
                url=NOTION_MCP_URL,
                oauth=notion_oauth,
            )

            await notion_client.connect()
            self.clients["notion"] = notion_client
        except Exception as e:
            print(f"[MCP] Could not connect to Notion: {e}")

        # ----------------------------------------------------
        # Email MCP Client
        # ----------------------------------------------------
        try:
            email_client = MCPClient(
                name="email",
                url=EMAIL_MCP_URL,
            )

            await email_client.connect()
            self.clients["email"] = email_client
        except Exception as e:
            print(f"[MCP] Could not connect to Email MCP: {e}")

        # ----------------------------------------------------
        # Google Calendar MCP Client
        # ----------------------------------------------------
        try:
            calendar_params = create_google_calendar_params()

            calendar_client = MCPClient(
                name="google_calendar",
                server_params=calendar_params,
            )

            await calendar_client.connect()
            self.clients["google_calendar"] = calendar_client
        except Exception as e:
            print(f"[MCP] Could not connect to Google Calendar: {e}")

    async def disconnect_all(self):
        clients = list(self.clients.values())

        self.clients.clear()
        self.tool_servers.clear()

        for client in clients:
            try:
                await client.disconnect()
            except Exception as e:
                print(f"[MCP] Error disconnecting client: {e}")

    async def get_tool_definitions(self):

        tool_definitions = []

        for server_name, client in self.clients.items():

            tools = await client.get_tool_definitions()

            for tool in tools:
                tool_name = tool.get("function", {}).get("name")

                if tool_name:
                    self.tool_servers[tool_name] = server_name

                tool_definitions.append(tool)

        return tool_definitions

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ):

        for client in self.clients.values():

            tools = await client.list_tools()

            for tool in tools.tools:

                if tool.name == tool_name:

                    return await asyncio.wait_for(
                        client.call_tool(tool_name, arguments),
                        timeout=120,
                    )

        raise RuntimeError(
            f"Unknown MCP tool: {tool_name}"
        )

    async def get_exa_tool_definitions(self):
        """
        Retrieve and print Exa's tool definitions
        in OpenAI-compatible format.
        """

        exa_client = MCPClient(
            name="exa",
            url=EXA_MCP_URL,
        )

        try:
            await exa_client.connect()

            tool_definitions = (
                await exa_client.get_tool_definitions()
            )

            print("\n========== EXA TOOL DEFINITIONS ==========\n")

            print(
                json.dumps(
                    tool_definitions,
                    indent=4,
                    ensure_ascii=False,
                )
            )

            return tool_definitions

        finally:
            await exa_client.disconnect()

    
