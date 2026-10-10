from dataclasses import dataclass, field
from typing import List


@dataclass
class CapabilityProfile:
    name: str
    description: str
    preferred_servers: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


CAPABILITY_PROFILES = {
    "web_research": CapabilityProfile(
        name="Web Research Specialist",
        description=(
            "Researches topics using online sources "
            "and summarizes reliable findings."
        ),
        preferred_servers=["tavily"],
        keywords=[
            "search",
            "research",
            "news",
            "online",
            "sources",
            "look up",
            "find"
        ],
    ),

    "productivity": CapabilityProfile(
        name="Productivity Specialist",
        description=(
            "Manages Notion content and calendar workflows."
        ),
        preferred_servers=[
            "notion",
            "google_calendar",
        ],
        keywords=[
            "notion",
            "calendar",
            "meeting",
            "schedule",
            "event",
        ],
    ),

    "email": CapabilityProfile(
        name="Email Specialist",
        description=(
            "Manages email-related workflows."
        ),
        preferred_servers=["email"],
        keywords=[
            "email",
            "mail",
            "inbox",
            "reply",
        ],
    ),
}