# Discord定型文Bot

Discordのスラッシュコマンドで、サーバーごとに定型文・Poll送信を管理するBotです。

## 主な機能

- `/定型文追加`
- `/定型文削除`
- `/定型文一覧`
- `/定型文即送信`
- `/定型文一時停止`
- `/定型文再開`
- `/定型文全停止`
- `/定型文全再開`
- `/定型文時刻変更`
- `/定型文制限時間変更`
- `/定型文質問変更`
- `/定型文選択肢変更`
- `/定型文複数回答変更`
- `/定型文メンション変更`
- `/定型文チャンネル変更`
- `/定型文コピー`
- `/定型文送信履歴`
- `/定型文テスト送信`

## ローカル起動

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env に DISCORD_TOKEN を設定
python main.py
```

Windows PowerShellの場合:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python main.py
```

## 常時稼働の推奨構成

GitHubはコード置き場として使い、Botの常時稼働はVPSで行います。
無料・低コスト運用なら Oracle Cloud Always Free などのLinux VPS + systemd が安定です。

## 注意

- `.env` はGitHubへ上げないでください。
- `bot_config.json` は実データなので、原則GitHubへ上げないでください。
- サーバー移行時だけ、必要に応じて `bot_config.json` を安全な方法でコピーしてください。
