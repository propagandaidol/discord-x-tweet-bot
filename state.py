import json
from pathlib import Path
from typing import Optional


class StateStore:
    """最後に投稿したツイートIDをユーザーごとに永続化し、再起動時の重複投稿を防ぐ"""

    def __init__(self, path: Path):
        self._path = path
        self._data: dict[str, str] = {}
        if self._path.exists():
            self._data = json.loads(self._path.read_text(encoding="utf-8"))

    def get_last_tweet_id(self, username: str) -> Optional[str]:
        return self._data.get(username)

    def set_last_tweet_id(self, username: str, tweet_id: str) -> None:
        self._data[username] = tweet_id
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
