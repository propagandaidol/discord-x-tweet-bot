import asyncio
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from state import StateStore
from x_client import XTweetFetcher

URL_PATTERN = re.compile(r"https?://\S+")
DISCORD_MESSAGE_LIMIT = 2000
DISCORD_API = "https://discord.com/api/v10"


def build_message(tweet, target_username: str) -> str:
    tweet_url = f"https://x.com/{target_username}/status/{tweet.id}"
    text = getattr(tweet, "full_text", None) or tweet.text or ""

    footer = f"\n{tweet_url}"
    max_text_len = DISCORD_MESSAGE_LIMIT - len(footer) - 1
    if len(text) > max_text_len:
        text = text[: max_text_len - 1].rstrip() + "…"

    # ツイート本文中のURLは埋め込みプレビューを個別に抑制し、末尾のツイート
    # リンクだけX本体のカード埋め込みが表示されるようにする
    text = URL_PATTERN.sub(lambda m: f"<{m.group(0)}>", text)

    return f"{text}{footer}"


async def post_to_discord(
    client: httpx.AsyncClient, token: str, channel_id: int, content: str, max_retries: int = 5
) -> None:
    for attempt in range(max_retries + 1):
        resp = await client.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {token}"},
            json={"content": content},
            timeout=15,
        )
        if resp.status_code == 429 and attempt < max_retries:
            retry_after = resp.json().get("retry_after", 1)
            await asyncio.sleep(float(retry_after) + 0.5)
            continue
        resp.raise_for_status()
        return


async def main() -> None:
    token = os.environ["DISCORD_BOT_TOKEN"]
    channel_ids = [int(p.strip()) for p in os.environ["DISCORD_CHANNEL_ID"].split(",") if p.strip()]
    target_username = os.environ["TARGET_X_USERNAME"].lstrip("@")

    # GitHub Actions ではSecretsからCookieのJSON文字列を受け取り、
    # ファイルへ書き出してから使う(ファイル自体はコミットしない)
    cookies_json = os.environ.get("TWIKIT_COOKIES_JSON")
    cookies_path = BASE_DIR / "cookies.json"
    if cookies_json:
        cookies_path.write_text(cookies_json, encoding="utf-8")

    fetcher = XTweetFetcher(os.environ["X_USERNAME"], os.environ["X_EMAIL"], os.environ["X_PASSWORD"])
    fetcher._client.load_cookies(str(cookies_path))

    state = StateStore(BASE_DIR / "state.json")
    last_id = state.get_last_tweet_id(target_username)
    new_tweets = await fetcher.fetch_new_original_tweets(target_username, last_id)

    if not new_tweets:
        print("新しいツイートはありません")
        return

    async with httpx.AsyncClient() as client:
        for tweet in new_tweets:
            message = build_message(tweet, target_username)
            for channel_id in channel_ids:
                try:
                    await post_to_discord(client, token, channel_id, message)
                    print(f"posted to channel {channel_id}: tweet {tweet.id}")
                except Exception as e:
                    print(f"failed to post to channel {channel_id}: {e}")
                # Discordのレート制限(だいたい5リクエスト/5秒/チャンネル)に
                # 引っかからないよう、連投の間に少し間隔を空ける
                await asyncio.sleep(1)
            state.set_last_tweet_id(target_username, tweet.id)


if __name__ == "__main__":
    asyncio.run(main())
