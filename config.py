import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"環境変数 {name} が設定されていません。.envを確認してください。")
    return value


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    discord_channel_ids: list[int]
    target_x_username: str
    x_username: str
    x_email: str
    x_password: str
    poll_interval_seconds: int


def load_config() -> Config:
    channel_ids = [
        int(part.strip())
        for part in _require("DISCORD_CHANNEL_ID").split(",")
        if part.strip()
    ]
    return Config(
        discord_bot_token=_require("DISCORD_BOT_TOKEN"),
        discord_channel_ids=channel_ids,
        target_x_username=_require("TARGET_X_USERNAME").lstrip("@"),
        x_username=_require("X_USERNAME"),
        x_email=_require("X_EMAIL"),
        x_password=_require("X_PASSWORD"),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "300")),
    )
