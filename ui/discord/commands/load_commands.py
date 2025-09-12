# ui/discord/commands/load_commands.py
import importlib
import pkgutil
from pathlib import Path

# /コマンド読み込み
def load_commands(tree, client, guild):
    command_dir = Path(__file__).parent
    package_name = __name__.rpartition('.')[0]  # "ui.discord.commands"

    for _, module_name, _ in pkgutil.iter_modules([str(command_dir)]):
        if module_name.startswith("ac_"):
            module_path = f"{package_name}.{module_name}"
            module = importlib.import_module(module_path)
            if hasattr(module, "register"):
                module.register(tree, client, guild)
                if guild:
                    print(f"🔎 検出: /{module_name} コマンド")
