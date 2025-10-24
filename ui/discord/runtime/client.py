# Discordクライアントの“唯一の定義場所”
# - 他所で client/tree/BACKGROUND_TASKS を直生成しない：循環・多重起動を防止
import discord, asyncio
from discord import app_commands

intents = discord.Intents.all()
intents.members = True  # メンバー情報を利用する機能があるため明示
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
BACKGROUND_TASKS: set[asyncio.Task] = set()  # 背景タスクを束ねてShutdownで止める
