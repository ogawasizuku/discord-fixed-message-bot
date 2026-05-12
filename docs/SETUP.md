# セットアップ手順

このドキュメントでは、Discord定型文Botをローカル環境またはVPSで起動するまでの手順をまとめます。

## 1. Discord Developer PortalでBotを作成

Discord Developer Portalで新しいアプリケーションを作成し、Botを追加します。

作成後、Bot Tokenを取得します。

取得したTokenは `.env` に設定します。  
GitHubには絶対に公開しないでください。

## 2. Privileged Gateway Intentsを確認

Discord Developer PortalのBot設定で、必要に応じて以下を有効にします。

- Message Content Intent

このBotでは `message_content` intent を使う構成になっています。

## 3. Botをサーバーに招待

OAuth2 URL Generatorなどを使って、BotをDiscordサーバーへ招待します。

必要な権限の例：

- Send Messages
- Use Slash Commands
- Read Message History
- Mention Everyone
- Manage Messages（必要に応じて）

運用するサーバーに合わせて、必要最低限の権限に調整してください。

## 4. リポジトリを取得

```bash
git clone https://github.com/ogawasizuku/discord-fixed-message-bot.git
cd discord-fixed-message-bot
```

## 5. Python仮想環境を作成

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 6. 依存関係をインストール

```bash
pip install -r requirements.txt
```

## 7. `.env` を作成

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
copy .env.example .env
```

`.env` にDiscord Bot Tokenを設定します。

```env
DISCORD_TOKEN=ここにDiscord Bot Token
DATA_DIR=/opt/discord-fixed-message-bot/data
```

ローカルで試すだけなら `DATA_DIR` は省略しても構いません。

## 8. ローカルで起動確認

```bash
python main.py
```

以下のようなログが出れば起動成功です。

```text
DISCORD_TOKEN 読み込み成功
logging in using static token
connected to Gateway
グローバルコマンドを同期しました
定期チェックを開始しました
```

停止する場合は `Ctrl + C` です。

## 9. VPSで常時稼働する場合

Oracle Cloud Always FreeなどのLinux VPSで使う場合は、以下のような配置がおすすめです。

```text
/opt/discord-fixed-message-bot
```

例：

```bash
cd /opt
sudo git clone https://github.com/ogawasizuku/discord-fixed-message-bot.git
sudo chown -R ubuntu:ubuntu /opt/discord-fixed-message-bot

cd /opt/discord-fixed-message-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env
```

`.env` にTokenを入れたら、まず手動で起動確認します。

```bash
python main.py
```

## 10. systemdで常時起動化

手動起動が成功したら、systemdに登録します。

```bash
sudo cp deploy/discord-fixed-message-bot.service /etc/systemd/system/discord-fixed-message-bot.service
sudo systemctl daemon-reload
sudo systemctl enable discord-fixed-message-bot
sudo systemctl restart discord-fixed-message-bot
sudo systemctl status discord-fixed-message-bot --no-pager
```

`Active: active (running)` と表示されれば成功です。

## 11. 日本時間で運用する場合

送信時刻はサーバーのタイムゾーンに依存します。

日本時間で運用する場合は、VPS側で以下を実行します。

```bash
sudo timedatectl set-timezone Asia/Tokyo
timedatectl
```

## 12. よくある確認ポイント

### Tokenが読み込めない

`.env` に以下があるか確認してください。

```env
DISCORD_TOKEN=xxxxx
```

### スラッシュコマンドが出ない

グローバルコマンドは反映に時間がかかる場合があります。

少し待ってからDiscord側で確認してください。

### Botが止まる

systemdの状態とログを確認します。

```bash
sudo systemctl status discord-fixed-message-bot --no-pager
journalctl -u discord-fixed-message-bot -f
```
