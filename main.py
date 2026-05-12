import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
from datetime import datetime, timedelta
import os
import copy
from dotenv import load_dotenv
import os
from pathlib import Path

# .env はプロジェクト直下から読み込みます。
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN が読み込めていません（.envを確認）")


print("✅ DISCORD_TOKEN 読み込み成功")


# intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True


bot = commands.Bot(command_prefix='!', intents=intents)
# サーバーごとの定型文を保存する辞書 {guild_id: {message_name: data}}
scheduled_messages = {}
# 設定ファイル名
DATA_DIR = Path(os.getenv('DATA_DIR', '.'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / 'bot_config.json'

def load_config():
    """設定ファイルから定型文を読み込む"""
    global scheduled_messages
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            scheduled_messages = json.load(f)
            # キーを文字列から整数に変換
            scheduled_messages = {int(k): v for k, v in scheduled_messages.items()}

def save_config():
    """設定ファイルに定型文を保存する"""
    # キーを文字列に変換してJSON保存
    save_data = {str(k): v for k, v in scheduled_messages.items()}
    with CONFIG_FILE.open('w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

def get_guild_messages(guild_id: int):
    """指定サーバーの定型文を取得"""
    if guild_id not in scheduled_messages:
        scheduled_messages[guild_id] = {}
    return scheduled_messages[guild_id]

@bot.event
async def on_ready():
    """Bot起動時の処理"""
    print(f'{bot.user} としてログインしました')
    print(f'接続中のサーバー数: {len(bot.guilds)}')
    for guild in bot.guilds:
        print(f'  - {guild.name} (ID: {guild.id})')
    
    load_config()
    
    # グローバルコマンドとして同期（重複を防ぐ）
    try:
        synced = await bot.tree.sync()
        print(f'✅ {len(synced)}個のコマンドをグローバルに同期しました')
    except Exception as e:
        print(f'❌ コマンド同期エラー: {e}')
    
    check_scheduled_messages.start()
    print('定期チェックを開始しました')

@bot.event
async def on_guild_join(guild):
    """新しいサーバーに追加された時"""
    print(f'新しいサーバーに追加されました: {guild.name} (ID: {guild.id})')
    # グローバルコマンドを使用するため、個別の同期は不要

@bot.tree.command(name="定型文追加", description="定型文を追加します")
@app_commands.describe(
    名前="定型文の名前(識別用)",
    質問="アンケートの質問内容",
    時刻="送信時刻(HH:MM形式、例: 14:30)",
    制限時間="回答制限時間(時間単位、最大168時間)",
    選択肢1="選択肢1",
    選択肢2="選択肢2",
    選択肢3="選択肢3(オプション)",
    選択肢4="選択肢4(オプション)",
    複数回答="複数選択を許可する場合はTrue",
    everyoneメンション="@everyoneメンションを付ける場合はTrue(デフォルト: True)"
)
async def add_message(
    interaction: discord.Interaction,
    名前: str,
    質問: str,
    時刻: str,
    制限時間: int,
    選択肢1: str,
    選択肢2: str,
    選択肢3: str = None,
    選択肢4: str = None,
    複数回答: bool = False,
    everyoneメンション: bool = True
):
    """定型文を追加"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    try:
        # 時刻の検証
        hour, minute = map(int, 時刻.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
        
        # 制限時間の検証(1-168時間)
        if not (1 <= 制限時間 <= 168):
            await interaction.response.send_message(
                '❌ 制限時間は1〜168時間の範囲で設定してください',
                ephemeral=True
            )
            return
        
        # 選択肢のリストを作成
        choices = [選択肢1, 選択肢2]
        if 選択肢3:
            choices.append(選択肢3)
        if 選択肢4:
            choices.append(選択肢4)
        
        guild_msgs[名前] = {
            'question': 質問,
            'time': 時刻,
            'duration': 制限時間,
            'channel_id': interaction.channel_id,
            'choices': choices,
            'multiple': 複数回答,
            'mention_everyone': everyoneメンション,
            'last_sent': None
        }
        
        save_config()
        choices_text = '\n'.join([f'・{c}' for c in choices])
        await interaction.response.send_message(
            f'✅ このサーバーに定型文「{名前}」を追加しました\n'
            f'質問: {質問}\n'
            f'送信時刻: {時刻}\n'
            f'制限時間: {制限時間}時間\n'
            f'選択肢:\n{choices_text}\n'
            f'複数回答: {"可" if 複数回答 else "不可"}\n'
            f'@everyoneメンション: {"あり" if everyoneメンション else "なし"}',
            ephemeral=True
        )
    except ValueError:
        await interaction.response.send_message(
            '❌ 時刻の形式が正しくありません(HH:MM形式で入力してください)',
            ephemeral=True
        )

@bot.tree.command(name="定型文削除", description="定型文を削除します")
@app_commands.describe(名前="削除する定型文の名前")
async def remove_message(interaction: discord.Interaction, 名前: str):
    """定型文を削除"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 in guild_msgs:
        del guild_msgs[名前]
        save_config()
        await interaction.response.send_message(
            f'✅ 定型文「{名前}」を削除しました\n次回から送信されません',
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )

@bot.tree.command(name="定型文時刻変更", description="定型文の送信時刻を変更します")
@app_commands.describe(
    名前="変更する定型文の名前",
    新しい時刻="新しい送信時刻(HH:MM形式、例: 14:30)"
)
async def change_time(interaction: discord.Interaction, 名前: str, 新しい時刻: str):
    """定型文の送信時刻を変更"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.response.send_message(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    try:
        # 時刻の検証
        hour, minute = map(int, 新しい時刻.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
        
        old_time = guild_msgs[名前]['time']
        guild_msgs[名前]['time'] = 新しい時刻
        guild_msgs[名前]['last_sent'] = None  # 今日も送信できるようにリセット
        save_config()
        
        await interaction.response.send_message(
            f'✅ 定型文「{名前}」の送信時刻を変更しました\n'
            f'変更前: {old_time}\n'
            f'変更後: {新しい時刻}',
            ephemeral=True
        )
    except ValueError:
        await interaction.response.send_message(
            '❌ 時刻の形式が正しくありません(HH:MM形式で入力してください)',
            ephemeral=True
        )

@bot.tree.command(name="定型文制限時間変更", description="定型文の制限時間を変更します")
@app_commands.describe(
    名前="変更する定型文の名前",
    新しい制限時間="新しい制限時間(時間単位、1-168)"
)
async def change_duration(interaction: discord.Interaction, 名前: str, 新しい制限時間: int):
    """定型文の制限時間を変更"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.response.send_message(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    if not (1 <= 新しい制限時間 <= 168):
        await interaction.response.send_message(
            '❌ 制限時間は1〜168時間の範囲で設定してください',
            ephemeral=True
        )
        return
    
    old_duration = guild_msgs[名前]['duration']
    guild_msgs[名前]['duration'] = 新しい制限時間
    save_config()
    
    await interaction.response.send_message(
        f'✅ 定型文「{名前}」の制限時間を変更しました\n'
        f'変更前: {old_duration}時間\n'
        f'変更後: {新しい制限時間}時間',
        ephemeral=True
    )

@bot.tree.command(name="定型文質問変更", description="定型文の質問内容を変更します")
@app_commands.describe(
    名前="変更する定型文の名前",
    新しい質問="新しい質問内容"
)
async def change_question(interaction: discord.Interaction, 名前: str, 新しい質問: str):
    """定型文の質問を変更"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.followup.send(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    old_question = guild_msgs[名前]['question']
    guild_msgs[名前]['question'] = 新しい質問
    save_config()
    
    await interaction.followup.send(
        f'✅ 定型文「{名前}」の質問内容を変更しました\n'
        f'変更前: {old_question}\n'
        f'変更後: {新しい質問}',
        ephemeral=True
    )

@bot.tree.command(name="定型文選択肢変更", description="定型文の選択肢を変更します")
@app_commands.describe(
    名前="変更する定型文の名前",
    選択肢1="選択肢1",
    選択肢2="選択肢2",
    選択肢3="選択肢3(オプション)",
    選択肢4="選択肢4(オプション)"
)
async def change_choices(
    interaction: discord.Interaction,
    名前: str,
    選択肢1: str,
    選択肢2: str,
    選択肢3: str = None,
    選択肢4: str = None
):
    """定型文の選択肢を変更"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.followup.send(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    # 選択肢のリストを作成
    new_choices = [選択肢1, 選択肢2]
    if 選択肢3:
        new_choices.append(選択肢3)
    if 選択肢4:
        new_choices.append(選択肢4)
    
    old_choices = guild_msgs[名前]['choices']
    guild_msgs[名前]['choices'] = new_choices
    save_config()
    
    old_choices_text = '\n'.join([f'・{c}' for c in old_choices])
    new_choices_text = '\n'.join([f'・{c}' for c in new_choices])
    
    await interaction.followup.send(
        f'✅ 定型文「{名前}」の選択肢を変更しました\n'
        f'変更前:\n{old_choices_text}\n\n'
        f'変更後:\n{new_choices_text}',
        ephemeral=True
    )

@bot.tree.command(name="定型文複数回答変更", description="定型文の複数回答設定を変更します")
@app_commands.describe(
    名前="変更する定型文の名前",
    複数回答="複数選択を許可する場合はTrue"
)
async def change_multiple(interaction: discord.Interaction, 名前: str, 複数回答: bool):
    """定型文の複数回答設定を変更"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.response.send_message(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    old_multiple = guild_msgs[名前]['multiple']
    guild_msgs[名前]['multiple'] = 複数回答
    save_config()
    
    await interaction.response.send_message(
        f'✅ 定型文「{名前}」の複数回答設定を変更しました\n'
        f'変更前: {"可" if old_multiple else "不可"}\n'
        f'変更後: {"可" if 複数回答 else "不可"}',
        ephemeral=True
    )

@bot.tree.command(name="定型文メンション変更", description="定型文の@everyoneメンションを変更します")
@app_commands.describe(
    名前="変更する定型文の名前",
    メンション="@everyoneメンションを付ける場合はTrue"
)
async def change_mention(interaction: discord.Interaction, 名前: str, メンション: bool):
    """定型文のメンション設定を変更"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.followup.send(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    old_mention = guild_msgs[名前].get('mention_everyone', True)
    guild_msgs[名前]['mention_everyone'] = メンション
    save_config()
    
    await interaction.followup.send(
        f'✅ 定型文「{名前}」のメンション設定を変更しました\n'
        f'変更前: {"あり" if old_mention else "なし"}\n'
        f'変更後: {"あり" if メンション else "なし"}',
        ephemeral=True
    )

@bot.tree.command(name="定型文チャンネル変更", description="定型文の送信先チャンネルを変更します")
@app_commands.describe(
    名前="変更する定型文の名前",
    チャンネル="新しい送信先チャンネル"
)
async def change_channel(interaction: discord.Interaction, 名前: str, チャンネル: discord.TextChannel):
    """定型文の送信チャンネルを変更"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.response.send_message(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    old_channel = bot.get_channel(guild_msgs[名前]['channel_id'])
    old_channel_name = old_channel.name if old_channel else '不明'
    
    guild_msgs[名前]['channel_id'] = チャンネル.id
    save_config()
    
    await interaction.response.send_message(
        f'✅ 定型文「{名前}」の送信先チャンネルを変更しました\n'
        f'変更前: #{old_channel_name}\n'
        f'変更後: {チャンネル.mention}',
        ephemeral=True
    )

@bot.tree.command(name="定型文コピー", description="既存の定型文をコピーして新しい定型文を作成します")
@app_commands.describe(
    元の名前="コピー元の定型文の名前",
    新しい名前="新しい定型文の名前"
)
async def copy_message(interaction: discord.Interaction, 元の名前: str, 新しい名前: str):
    """定型文をコピー"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 元の名前 not in guild_msgs:
        await interaction.response.send_message(
            f'❌ このサーバーに定型文「{元の名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    if 新しい名前 in guild_msgs:
        await interaction.response.send_message(
            f'❌ 定型文「{新しい名前}」は既に存在します',
            ephemeral=True
        )
        return
    
    # 元の定型文をコピー
    guild_msgs[新しい名前] = copy.deepcopy(guild_msgs[元の名前])
    guild_msgs[新しい名前]['last_sent'] = None  # 送信履歴はリセット
    save_config()
    
    data = guild_msgs[新しい名前]
    choices_text = '\n'.join([f'・{c}' for c in data['choices']])
    
    await interaction.response.send_message(
        f'✅ 定型文「{元の名前}」を「{新しい名前}」としてコピーしました\n'
        f'質問: {data["question"]}\n'
        f'送信時刻: {data["time"]}\n'
        f'制限時間: {data["duration"]}時間\n'
        f'選択肢:\n{choices_text}\n'
        f'複数回答: {"可" if data["multiple"] else "不可"}\n'
        f'@everyoneメンション: {"あり" if data.get("mention_everyone", True) else "なし"}',
        ephemeral=True
    )

@bot.tree.command(name="定型文一時停止", description="定型文の自動送信を一時停止します")
@app_commands.describe(名前="一時停止する定型文の名前")
async def pause_message(interaction: discord.Interaction, 名前: str):
    """定型文を一時停止"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.response.send_message(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    guild_msgs[名前]['paused'] = True
    save_config()
    
    await interaction.response.send_message(
        f'⏸️ 定型文「{名前}」を一時停止しました\n'
        f'再開するには `/定型文再開` コマンドを使用してください',
        ephemeral=True
    )

@bot.tree.command(name="定型文再開", description="一時停止中の定型文を再開します")
@app_commands.describe(名前="再開する定型文の名前")
async def resume_message(interaction: discord.Interaction, 名前: str):
    """定型文を再開"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.response.send_message(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    if not guild_msgs[名前].get('paused', False):
        await interaction.response.send_message(
            f'ℹ️ 定型文「{名前}」は停止されていません',
            ephemeral=True
        )
        return
    
    guild_msgs[名前]['paused'] = False
    save_config()
    
    await interaction.response.send_message(
        f'▶️ 定型文「{名前}」を再開しました\n'
        f'次回の送信時刻: {guild_msgs[名前]["time"]}',
        ephemeral=True
    )

@bot.tree.command(name="定型文全停止", description="このサーバーの全ての定型文を一時停止します")
async def pause_all(interaction: discord.Interaction):
    """全定型文を一時停止"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if not guild_msgs:
        await interaction.response.send_message(
            'このサーバーには定型文が登録されていません',
            ephemeral=True
        )
        return
    
    count = 0
    for name, data in guild_msgs.items():
        if not data.get('paused', False):
            data['paused'] = True
            count += 1
    
    save_config()
    
    await interaction.response.send_message(
        f'⏸️ {count}個の定型文を一時停止しました\n'
        f'再開するには `/定型文全再開` または個別に `/定型文再開` を使用してください',
        ephemeral=True
    )

@bot.tree.command(name="定型文全再開", description="このサーバーの全ての定型文を再開します")
async def resume_all(interaction: discord.Interaction):
    """全定型文を再開"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if not guild_msgs:
        await interaction.response.send_message(
            'このサーバーには定型文が登録されていません',
            ephemeral=True
        )
        return
    
    count = 0
    for name, data in guild_msgs.items():
        if data.get('paused', False):
            data['paused'] = False
            count += 1
    
    save_config()
    
    await interaction.response.send_message(
        f'▶️ {count}個の定型文を再開しました',
        ephemeral=True
    )

@bot.tree.command(name="定型文一覧", description="このサーバーに登録されている定型文の一覧を表示します")
async def list_messages(interaction: discord.Interaction):
    """定型文の一覧を表示(サーバーごと)"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if not guild_msgs:
        await interaction.followup.send(
            'このサーバーには定型文が登録されていません',
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=f"📋 {interaction.guild.name} の定型文一覧",
        color=discord.Color.blue()
    )
    
    for name, data in guild_msgs.items():
        choices_text = '、'.join(data['choices'])
        status = '⏸️ 停止中' if data.get('paused', False) else '▶️ 稼働中'
        mention_status = '🔔あり' if data.get('mention_everyone', True) else '🔕なし'
        embed.add_field(
            name=f"{name} ({status})",
            value=f"質問: {data['question']}\n"
                  f"時刻: {data['time']}\n"
                  f"制限: {data['duration']}時間\n"
                  f"選択肢: {choices_text}\n"
                  f"複数回答: {'可' if data['multiple'] else '不可'}\n"
                  f"@everyoneメンション: {mention_status}",
            inline=False
        )
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="定型文送信履歴", description="定型文の送信履歴を確認します")
@app_commands.describe(名前="確認する定型文の名前(省略すると全ての定型文)")
async def check_history(interaction: discord.Interaction, 名前: str = None):
    """定型文の送信履歴を確認"""
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if not guild_msgs:
        await interaction.response.send_message(
            'このサーバーには定型文が登録されていません',
            ephemeral=True
        )
        return
    
    if 名前:
        # 特定の定型文の履歴
        if 名前 not in guild_msgs:
            await interaction.response.send_message(
                f'❌ このサーバーに定型文「{名前}」が見つかりません',
                ephemeral=True
            )
            return
        
        data = guild_msgs[名前]
        last_sent = data.get('last_sent', 'まだ送信されていません')
        status = '⏸️ 停止中' if data.get('paused', False) else '▶️ 稼働中'
        
        await interaction.response.send_message(
            f'📊 定型文「{名前}」の送信履歴\n'
            f'ステータス: {status}\n'
            f'最終送信日: {last_sent}\n'
            f'次回送信時刻: {data["time"]}',
            ephemeral=True
        )
    else:
        # 全ての定型文の履歴
        embed = discord.Embed(
            title=f"📊 {interaction.guild.name} の送信履歴",
            color=discord.Color.green()
        )
        
        for name, data in guild_msgs.items():
            last_sent = data.get('last_sent', 'まだ送信されていません')
            status = '⏸️ 停止中' if data.get('paused', False) else '▶️ 稼働中'
            embed.add_field(
                name=f"{name} ({status})",
                value=f"最終送信: {last_sent}\n次回: {data['time']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="定型文テスト送信", description="定型文を自分だけに見える形でテスト送信します")
@app_commands.describe(名前="テスト送信する定型文の名前")
async def test_send(interaction: discord.Interaction, 名前: str):
    """定型文をテスト送信（ephemeral）"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.followup.send(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    data = guild_msgs[名前]
    choices_text = '\n'.join([f'{i+1}. {c}' for i, c in enumerate(data['choices'])])
    mention_text = '@everyone\n' if data.get('mention_everyone', True) else ''
    
    embed = discord.Embed(
        title=f"🧪 テスト送信: {名前}",
        description=f"{mention_text}**{data['question']}**\n\n"
                   f"**選択肢:**\n{choices_text}\n\n"
                   f"**制限時間:** {data['duration']}時間\n"
                   f"**複数回答:** {'可' if data['multiple'] else '不可'}",
        color=discord.Color.orange()
    )
    embed.set_footer(text="これはテスト送信です（他の人には見えません）")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="定型文即送信", description="定型文を即座に送信します")
@app_commands.describe(名前="送信する定型文の名前")
async def send_now(interaction: discord.Interaction, 名前: str):
    """定型文を即座に送信"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = interaction.guild_id
    guild_msgs = get_guild_messages(guild_id)
    
    if 名前 not in guild_msgs:
        await interaction.followup.send(
            f'❌ このサーバーに定型文「{名前}」が見つかりません',
            ephemeral=True
        )
        return
    
    await interaction.followup.send('送信しました', ephemeral=True)
    await send_scheduled_message(名前, guild_msgs[名前], interaction.channel)

async def send_scheduled_message(name: str, data: dict, channel):
    """定型文を送信(Discord Poll機能を使用)"""
    try:
        # チャンネルの権限をチェック
        permissions = channel.permissions_for(channel.guild.me)
        
        if not permissions.send_messages:
            print(f'❌ {channel.guild.name} の {channel.name} への送信権限がありません')
            return
        
        # メンション設定をチェック（デフォルトはTrue）
        mention_everyone = data.get('mention_everyone', True)
        
        if mention_everyone and not permissions.mention_everyone:
            print(f'⚠️ {channel.guild.name} で @everyone メンション権限がありません')
        
        # Pollオブジェクトを作成
        # durationを時間からtimedeltaに変換
        poll = discord.Poll(
            question=data['question'],
            duration=timedelta(hours=data['duration']),
            multiple=data['multiple']
        )
        
        # 選択肢を追加
        for choice in data['choices']:
            poll.add_answer(text=choice)
        
        # メンション設定に応じてメッセージ内容を変更
        if mention_everyone:
            content = f"@everyone\n📊 **{name}**"
        else:
            content = f"📊 **{name}**"
        
        # Pollを送信
        await channel.send(
            content=content,
            poll=poll
        )
        print(f'✅ {channel.guild.name} の {channel.name} に「{name}」を送信成功')
        
    except discord.Forbidden as e:
        print(f'❌ 権限エラー: {channel.guild.name} - {e}')
    except discord.HTTPException as e:
        print(f'❌ HTTP エラー: {channel.guild.name} - {e}')
    except Exception as e:
        print(f'❌ 予期しないエラー: {channel.guild.name} - {e}')

@tasks.loop(minutes=1)
async def check_scheduled_messages():
    """定期的に送信時刻をチェック"""
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    today = now.strftime('%Y-%m-%d')
    
    # 全サーバーの定型文をチェック
    for guild_id, guild_msgs in scheduled_messages.items():
        for name, data in guild_msgs.items():
            # 一時停止中はスキップ
            if data.get('paused', False):
                continue
                
            if data['time'] == current_time and data['last_sent'] != today:
                guild = bot.get_guild(guild_id)
                if not guild:
                    print(f'❌ サーバー {guild_id} が見つかりません')
                    continue
                
                channel = guild.get_channel(data['channel_id'])
                if not channel:
                    print(f'❌ {guild.name} のチャンネル {data["channel_id"]} が見つかりません')
                    continue
                
                print(f'📤 {guild.name} の {channel.name} に「{name}」を送信中...')
                
                try:
                    await send_scheduled_message(name, data, channel)
                    data['last_sent'] = today
                    save_config()
                    print(f'✅ {guild.name} に「{name}」を送信しました')
                except Exception as e:
                    print(f'❌ {guild.name} への送信エラー: {e}')

@check_scheduled_messages.before_loop
async def before_check():
    """タスク開始前にBotの準備を待つ"""
    await bot.wait_until_ready()

# Botを起動
# 環境変数からトークンを取得
bot.run(TOKEN)