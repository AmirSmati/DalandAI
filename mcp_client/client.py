from contextlib import AsyncExitStack

import httpx2
from mcp import Client, ClientSession, StdioServerParameters
from mcp.client.auth import OAuthClientProvider
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


class MCPClient:

    def __init__(
        self,
        name: str,
        url: str | None = None,
        oauth: OAuthClientProvider | None = None,
        server_params: StdioServerParameters | None = None,
    ):

        self.name = name
        self.url = url
        self.oauth = oauth
        self.server_params = server_params
        if self.name == "exa" :
            self.max_results = 3

        self.http_client = None
        self.transport = None
        self.client = None
        self.session = None
        self.exit_stack = AsyncExitStack()

    async def connect(self):

        if self.server_params is not None:
            read, write = await self.exit_stack.enter_async_context(
                stdio_client(self.server_params)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self.session.initialize()
            print(f"\n[MCP] Connected to {self.name}")

        elif self.url is not None:
            self.http_client = httpx2.AsyncClient(
                auth=self.oauth,
                follow_redirects=True,
            )
            await self.exit_stack.enter_async_context(self.http_client)

            self.transport = streamable_http_client(
                self.url,
                http_client=self.http_client,
            )

            self.client = Client(self.transport)
            await self.exit_stack.enter_async_context(self.client)

            print(f"\n[MCP] Connected to {self.name}")
        else:
            raise ValueError(
                f"MCPClient '{self.name}' must have either url or server_params."
            )

    async def disconnect(self):

        try:
            await self.exit_stack.aclose()
            print(f"\n[MCP] Disconnected from {self.name}")
        except RuntimeError as e:
            print(f"\n[MCP] Disconnected from {self.name}")
        finally:
            self.client = None
            self.session = None
            self.transport = None
            self.http_client = None

    def _get_target(self):
        target = self.session if self.server_params is not None else self.client
        if not target:
            raise RuntimeError(
                f"MCP client '{self.name}' is not connected"
            )
        return target

    async def list_tools(self):

        target = self._get_target()
        return await target.list_tools()

    async def get_tool_definitions(self):

        tools_result = await self.list_tools()

        tool_definitions = []

        for tool in tools_result.tools:

            tool_definitions.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                }
            )

        return tool_definitions

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ):

        target = self._get_target()
        return await target.call_tool(
            tool_name,
            arguments=arguments,
        )


  
