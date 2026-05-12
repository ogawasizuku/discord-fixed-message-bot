# 運用メモ

このドキュメントでは、VPS上でDiscord定型文Botを運用する時によく使うコマンドをまとめます。

## 状態確認

```bash
sudo systemctl status discord-fixed-message-bot --no-pager
```

`Active: active (running)` と表示されていれば稼働中です。

## ログ確認

```bash
journalctl -u discord-fixed-message-bot -f
```

ログ監視を止める時は `Ctrl + C` です。

## 起動

```bash
sudo systemctl start discord-fixed-message-bot
```

## 停止

```bash
sudo systemctl stop discord-fixed-message-bot
```

## 再起動

```bash
sudo systemctl restart discord-fixed-message-bot
```

## 自動起動を有効化

```bash
sudo systemctl enable discord-fixed-message-bot
```

## 自動起動を無効化

```bash
sudo systemctl disable discord-fixed-message-bot
```

## GitHubの更新をVPSへ反映

```bash
cd /opt/discord-fixed-message-bot
git pull origin main
sudo systemctl restart discord-fixed-message-bot
sudo systemctl status discord-fixed-message-bot --no-pager
```

## 現在動いているBotサービスを確認

```bash
systemctl list-units --type=service --state=running | grep -i bot
```

複数Botを同じVPSで動かしている場合の確認に使えます。

## `.env` を編集する

```bash
cd /opt/discord-fixed-message-bot
nano .env
```

nanoの保存方法：

```text
Ctrl + O
Enter
Ctrl + X
```

編集後はBotを再起動します。

```bash
sudo systemctl restart discord-fixed-message-bot
```

## 設定ファイルの場所

本番運用では、設定ファイルは以下に保存されます。

```text
/opt/discord-fixed-message-bot/data/bot_config.json
```

このファイルには実サーバーの設定が入るため、GitHubには上げないでください。

## バックアップ例

```bash
cd /opt/discord-fixed-message-bot
cp data/bot_config.json data/bot_config.backup.$(date +%Y%m%d_%H%M%S).json
```

## サーバー時刻を確認

```bash
timedatectl
```

日本時間にする場合：

```bash
sudo timedatectl set-timezone Asia/Tokyo
```

## よくあるトラブル

### BotがDiscord上でオフライン

まず状態を確認します。

```bash
sudo systemctl status discord-fixed-message-bot --no-pager
```

ログも確認します。

```bash
journalctl -u discord-fixed-message-bot -f
```

### Tokenエラー

`.env` の `DISCORD_TOKEN` を確認します。

```bash
cd /opt/discord-fixed-message-bot
nano .env
```

Tokenを貼り直したら再起動します。

```bash
sudo systemctl restart discord-fixed-message-bot
```

### GitHubからpullできない

リポジトリがPrivateの場合、認証が必要です。

Publicリポジトリとして運用するか、Personal Access Token / Deploy Keyを使ってください。

### スラッシュコマンドがすぐ反映されない

グローバルコマンドはDiscord側で反映に時間がかかる場合があります。

しばらく待ってから確認してください。
