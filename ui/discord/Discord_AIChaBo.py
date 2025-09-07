import sys
import os

# プロジェクトルートをモジュール探索パスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from ui.discord.discord_handler import start_discord_bot
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    start_discord_bot()
