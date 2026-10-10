import json
from pathlib import Path

from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthToken,
)


class FileTokenStorage:

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None

        self._load()

    def _load(self):
        if not self.path.exists():
            return

        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if data.get("tokens"):
            self.tokens = OAuthToken.model_validate(
                data["tokens"]
            )

        if data.get("client_info"):
            self.client_info = OAuthClientInformationFull.model_validate(
                data["client_info"]
            )

    def _save(self):
        data = {
            "tokens": (
                self.tokens.model_dump(mode="json")
                if self.tokens
                else None
            ),
            "client_info": (
                self.client_info.model_dump(mode="json")
                if self.client_info
                else None
            ),
        }

        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    async def get_tokens(self):
        return self.tokens

    async def set_tokens(self, tokens):
        self.tokens = tokens
        self._save()

    async def get_client_info(self):
        return self.client_info

    async def set_client_info(self, client_info):
        self.client_info = client_info