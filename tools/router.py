from typing import List, Dict


class ToolRouter:
    """Select relevant tool groups based on the user's request."""

    def __init__(self, all_tools: List[Dict], mcp_tool_servers=None):
        self.all_tools = all_tools
        self.mcp_tool_servers = mcp_tool_servers or {}

        self.groups = {
            # Onprem Local
            "filesystem": {
                "list_files",
                "read_file",
                "create_folder",
                "create_file",
                "update_file",
                "search_files",
                "extract_and_classify_document",
                "extract_and_classify_folder",
            },

            #Memo
            "memory": {
                "save_memory",
                "get_memories",
                "delete_memory",
            },

            #Scheduler
            "scheduler": {
                "schedule_followup",
            },

            # MCP (Local & Beyond) server categories
            "web": {
                "exa",
            },

            "notion": {
                "notion",
            },

            "email": {
                "email",
            },

            "calendar": {
                "google_calendar",
            },
            #Delegation
            "delegation": {
                "delegate_to_subagent",
            },
        }

    def select_tools(self, user_task: str) -> List[Dict]:
        """Return only the tools relevant to the user's request."""

        task = user_task.lower()

        selected_groups = set()

        # Local filesystem tools
        if any(word in task for word in [
            "file", "files",
            "folder", "folders",
            "document", "documents",
            "workspace",
        ]):
            selected_groups.add("filesystem")

         
        # Memory tools
         
        if any(word in task for word in [
            "memory", "memories",
            "remember", "forgot", "forget",
            "stored", "saved",
        ]):
            selected_groups.add("memory")

         
        # Web / Tavily
         
        if any(word in task for word in [
            "search",
            "searched",
            "research",
            "paper",
            "papers",
            "fetch",
            "retrieve",
            "read",
            "extract",
            "source",
            "sources",
            "abstract",
            "content",
            "find",
            "google",
            "internet",
            "online",
            "website",
            "web",
            "url",
            "arxiv",
            "look up",
            "find online",
        ]):
            selected_groups.add("web")

         
        # Notion
         
        if any(word in task for word in [
            "notion",
            "page",
            "pages",
            "database",
            "databases",
        ]):
            selected_groups.add("notion")

         
        # Email
         
        if any(word in task for word in [
            "email",
            "emails",
            "mail",
            "send an email",
            "write an email",
        ]):
            selected_groups.add("email")

         
        # Google Calendar
         
        if any(word in task for word in [
            "calendar",
            "event",
            "events",
            "meeting",
            "meetings",
            "appointment",
            "appointments",
            "schedule a meeting",
        ]):
            selected_groups.add("calendar")

         
        # Scheduler
         
        if any(word in task for word in [
            "remind me",
            "reminder",
            "remind",
            "schedule",
            "follow up",
            "follow-up",
            "later",
        ]):
            selected_groups.add("scheduler")

         
        # Select tools
         
        selected_tools = []

        for tool in self.all_tools:
            tool_name = tool.get("function", {}).get("name")

            if not tool_name:
                continue

            # Local tool groups
            for group_name in [
                "filesystem",
                "memory",
                "scheduler",
            ]:
                if tool_name in self.groups[group_name]:
                    if group_name in selected_groups:
                        selected_tools.append(tool)
                    break

            else:
                # MCP tool
                server_name = self.mcp_tool_servers.get(tool_name)

                if server_name == "exa" and "web" in selected_groups:
                    selected_tools.append(tool)

                elif server_name == "notion" and "notion" in selected_groups:
                    selected_tools.append(tool)

                elif server_name == "email" and "email" in selected_groups:
                    selected_tools.append(tool)

                elif server_name == "google_calendar" and "calendar" in selected_groups:
                    selected_tools.append(tool)

        return selected_tools