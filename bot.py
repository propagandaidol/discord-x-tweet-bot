import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

import discord
from discord.ext import tasks

from config import load_config
from state import StateStore
from x_client import XTweetFetcher

URL_PATTERN = re.compile(r"https?://\S+")

BASE_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            BASE_DIR / "bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("x-tweet-bot")

config = load_config()
state = StateStore(BASE_DIR / "state.json")
fetcher = XTweetFetcher(config.x_username, config.x_email, config.x_password)

intents = discord.Intents.default()
client = discord.Client(intents=intents)


DISCORD_MESSAGE_LIMIT = 2000


def build_message(tweet) -> str:
    tweet_url = f"https://x.com/{config.target_x_username}/status/{tweet.id}"
    text = getattr(tweet, "full_text", None) or tweet.text or ""

    footer = f"\n{tweet_url}"

    max_text_len = DISCORD_MESSAGE_LIMIT - len(footer) - 1
    if len(text) > max_text_len:
        text = text[: max_text_len - 1].rstrip() + "…"

    # ツイート本文中のURL(YouTubeリンク等)は <...> で囲んでDiscordの埋め込み
    # プレビューを個別に抑制する。末尾のツイートリンクは囲まないので、
    # X本体のカード(埋め込み)はそのまま表示される。
    text = URL_PATTERN.sub(lambda m: f"<{m.group(0)}>", text)

    return f"{text}{footer}"


@tasks.loop(seconds=config.poll_interval_seconds)
async def poll_tweets() -> None:
    try:
        last_id = state.get_last_tweet_id(config.target_x_username)
        new_tweets = await fetcher.fetch_new_original_tweets(
            config.target_x_username, last_id
        )
    except Exception:
        logger.exception("ツイート取得中にエラーが発生しました。次回のポーリングまで待機します。")
        return

    if not new_tweets:
        return

    for tweet in new_tweets:
        message = build_message(tweet)
        for channel_id in config.discord_channel_ids:
            channel = client.get_channel(channel_id)
            if channel is None:
                logger.error(
                    "チャンネルID %s が見つかりません。Botがそのチャンネルにアクセスできるか確認してください。",
                    channel_id,
                )
                continue
            try:
                await channel.send(message)
            except Exception:
                logger.exception(
                    "Discordへの投稿に失敗しました。channel_id=%s tweet_id=%s", channel_id, tweet.id
                )
        # 一部のチャンネルへの投稿に失敗しても、そのチャンネルの不調で他の新規ツイートの
        # 通知まで止まらないよう、状態は進める
        state.set_last_tweet_id(config.target_x_username, tweet.id)


@poll_tweets.before_loop
async def before_poll_tweets() -> None:
    await client.wait_until_ready()
    await fetcher.login()


@client.event
async def on_ready() -> None:
    logger.info("Discord Botとしてログインしました: %s", client.user)
    if not poll_tweets.is_running():
        poll_tweets.start()


def main() -> None:
    client.run(config.discord_bot_token, log_handler=None)


if __name__ == "__main__":
    main()
