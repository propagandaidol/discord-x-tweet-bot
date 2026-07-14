# Discord X(Twitter) 新規ツイート通知Bot

特定のXアカウントの新規ツイート(リツイートを除く)を取得し、指定したDiscordチャンネルに投稿するBotです。

## 注意事項

- ツイート取得には[twikit](https://github.com/d60/twikit)(非公式ライブラリ)を使用しています。X社の利用規約に抵触する可能性があり、ログインに使用するアカウントが凍結されるリスクがあります。**メインアカウントではなく、監視専用のサブアカウントの使用を強く推奨します。**
- X側の仕様変更により、予告なく動作しなくなる可能性があります。
- ポーリング間隔(`POLL_INTERVAL_SECONDS`)は短くしすぎないでください(300秒=5分以上を推奨)。頻繁すぎるとアカウント制限のリスクが高まります。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Discord Botの作成

1. [Discord Developer Portal](https://discord.com/developers/applications) で新規Applicationを作成
2. Bot タブでBotを作成し、トークンを取得
3. OAuth2 > URL Generator で `bot` スコープと `Send Messages` 権限を選択し、生成されたURLでサーバーに招待
4. 投稿先チャンネルの「チャンネルID」を取得(Discordの開発者モードを有効にして、チャンネルを右クリック→IDをコピー)

### 3. 環境変数の設定

`.env.example` を `.env` にコピーして値を入力してください。

```bash
cp .env.example .env
```

| 変数名 | 説明 |
|---|---|
| `DISCORD_BOT_TOKEN` | Discord Botのトークン |
| `DISCORD_CHANNEL_ID` | ツイートを投稿するチャンネルのID。複数指定する場合はカンマ区切り |
| `TARGET_X_USERNAME` | 監視対象のXアカウントのスクリーンネーム(@なし) |
| `X_USERNAME` / `X_EMAIL` / `X_PASSWORD` | ツイート取得用にログインするXアカウントの認証情報 |
| `POLL_INTERVAL_SECONDS` | ポーリング間隔(秒)。デフォルト300秒 |

### 4. 起動

```bash
python bot.py
```

初回ログイン時に `cookies.json` が生成され、以降はこのcookieを使ってログインするため毎回パスワード認証は行われません。

## 動作仕様

- 起動後、`POLL_INTERVAL_SECONDS` ごとに対象アカウントの最新ツイートを取得します。
- リツイート(`retweeted_tweet` が設定されているツイート)は除外され、通常の新規ツイート・引用ツイートのみが対象です。
- 初回起動時は過去ツイートを大量通知しないよう、直近1件のみを基準として記録し、それ以降の新規ツイートから通知します。
- 投稿済みの最終ツイートIDは `state.json` に保存され、Bot再起動後も重複投稿しません。

## ファイル構成

- `bot.py` — Discord Bot本体、ポーリングループ
- `x_client.py` — twikitによるX認証・ツイート取得(リツイート除外含む)
- `state.py` — 最終投稿ツイートIDの永続化
- `config.py` — 環境変数読み込み
