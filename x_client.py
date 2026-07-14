import logging
from pathlib import Path
from typing import Optional

from twikit import Client, Tweet
from twikit import user as twikit_user

logger = logging.getLogger(__name__)

COOKIES_FILE = Path(__file__).resolve().parent / "cookies.json"

# Xのレスポンスはユーザーによって一部フィールド(ピン留めツイートが無い場合の
# pinned_tweet_ids_str、プロフィールにリンクが無い場合のentities.description.urls等)が
# 省略されることがあり、twikitのUser.__init__が直接dictアクセスしているためKeyErrorで
# 落ちることがある。欠落しがちなキーにデフォルト値を補ってから初期化する防御パッチ。
_original_user_init = twikit_user.User.__init__

_LEGACY_STR_DEFAULTS = (
    "created_at", "name", "screen_name", "profile_image_url_https",
    "location", "description", "translator_type",
)
_LEGACY_BOOL_DEFAULTS = (
    "verified", "possibly_sensitive", "can_dm", "can_media_tag",
    "want_retweets", "default_profile", "default_profile_image",
    "has_custom_timelines", "is_translator",
)
_LEGACY_INT_DEFAULTS = (
    "followers_count", "fast_followers_count", "normal_followers_count",
    "friends_count", "favourites_count", "listed_count", "media_count",
    "statuses_count",
)
_LEGACY_LIST_DEFAULTS = ("pinned_tweet_ids_str", "withheld_in_countries")


def _patched_user_init(self, client, data: dict) -> None:
    legacy = data.get("legacy")
    if isinstance(legacy, dict):
        entities = legacy.setdefault("entities", {})
        entities.setdefault("description", {}).setdefault("urls", [])
        for key in _LEGACY_STR_DEFAULTS:
            legacy.setdefault(key, "")
        for key in _LEGACY_BOOL_DEFAULTS:
            legacy.setdefault(key, False)
        for key in _LEGACY_INT_DEFAULTS:
            legacy.setdefault(key, 0)
        for key in _LEGACY_LIST_DEFAULTS:
            legacy.setdefault(key, [])
    data.setdefault("is_blue_verified", False)
    _original_user_init(self, client, data)


twikit_user.User.__init__ = _patched_user_init


class XTweetFetcher:
    """twikitを使ってX(Twitter)の特定ユーザーの新規ツイート(リツイート除く)を取得する"""

    def __init__(self, username: str, email: str, password: str):
        self._username = username
        self._email = email
        self._password = password
        self._client = Client(language="ja-JP")

    async def login(self) -> None:
        # cookies_fileが既に存在すればそれを使ってログイン処理をスキップし、
        # 無ければID/PWでログインしてcookieを保存する
        await self._client.login(
            auth_info_1=self._username,
            auth_info_2=self._email,
            password=self._password,
            cookies_file=str(COOKIES_FILE),
        )
        logger.info("Xへのログインに成功しました。")

    async def fetch_new_original_tweets(
        self, target_username: str, since_tweet_id: Optional[str]
    ) -> list[Tweet]:
        """target_usernameの新規ツイート(リツイート除く)を古い順に返す。

        since_tweet_id が None (初回実行) の場合は、過去ツイートを大量通知しないよう
        直近1件のみを返す。
        """
        user = await self._client.get_user_by_screen_name(target_username)
        tweets = await self._client.get_user_tweets(user.id, "Tweets", count=20)

        # retweeted_tweet が None でないものはリツイートなので除外する
        originals = [t for t in tweets if t.retweeted_tweet is None]

        if since_tweet_id is None:
            return originals[:1]

        since_id = int(since_tweet_id)
        new_tweets = [t for t in originals if int(t.id) > since_id]
        new_tweets.sort(key=lambda t: int(t.id))
        return new_tweets
