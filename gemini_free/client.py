"""Thin wrapper around gemini-webapi that loads cookies from disk."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model

COOKIES_FILE = Path(os.getenv("COOKIES_FILE", "cookies.json"))


class GeminiFree:
    """Singleton-ish wrapper. Call `await GeminiFree.get()` to grab a ready client."""

    _instance: Optional["GeminiFree"] = None

    def __init__(self, client: GeminiClient) -> None:
        self.client = client

    @classmethod
    async def get(cls) -> "GeminiFree":
        if cls._instance is not None:
            return cls._instance

        if not COOKIES_FILE.exists():
            raise RuntimeError(
                f"Cookies file not found at {COOKIES_FILE.resolve()}. "
                "Run `python -m gemini_free.auth` first."
            )

        cookies = json.loads(COOKIES_FILE.read_text())
        psid = cookies.get("__Secure-1PSID")
        psidts = cookies.get("__Secure-1PSIDTS")
        if not psid or not psidts:
            raise RuntimeError(
                "cookies.json is missing __Secure-1PSID or __Secure-1PSIDTS. "
                "Re-run `python -m gemini_free.auth`."
            )

        client = GeminiClient(psid, psidts)
        # auto_refresh keeps cookies alive in the background
        await client.init(timeout=30, auto_close=False, close_delay=300, auto_refresh=True)

        cls._instance = cls(client)
        return cls._instance

    async def ask(
        self,
        prompt: str,
        model: str | None = None,
        files: list[str] | None = None,
    ) -> dict:
        """Send a prompt, return a dict with text + raw payload."""
        chosen_model = _resolve_model(model)

        chat = self.client.start_chat(model=chosen_model)
        response = await chat.send_message(prompt, files=files or [])

        return {
            "model": chosen_model.model_name if hasattr(chosen_model, "model_name") else str(chosen_model),
            "text": response.text,
            "thoughts": getattr(response, "thoughts", None),
            "images": [img.url for img in (response.images or [])],
            "web_images": [img.url for img in (response.web_images or [])],
        }


def _resolve_model(name: str | None) -> Model:
    """Map friendly names to gemini-webapi Model enum. Defaults to UNSPECIFIED (whatever google gives free)."""
    if not name:
        return Model.UNSPECIFIED

    name = name.upper().replace("-", "_").replace(".", "_")
    # gemini-webapi enum names look like G_2_5_FLASH, G_2_5_PRO, etc.
    for member in Model:
        if member.name == name or member.name.endswith(name):
            return member

    # try common aliases
    aliases = {
        "FLASH": "G_2_5_FLASH",
        "PRO": "G_2_5_PRO",
        "2_5_FLASH": "G_2_5_FLASH",
        "2_5_PRO": "G_2_5_PRO",
    }
    if name in aliases:
        for member in Model:
            if member.name == aliases[name]:
                return member

    return Model.UNSPECIFIED
