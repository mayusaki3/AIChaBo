# コメント: 各 ac_*.py は get_command() を1つ返すだけ。
# ここで DEV_GUILD_ID が設定されていれば、そのギルドにだけ登録する（開発高速化）。
import os, pkgutil, importlib, sys, pathlib, traceback
from discord import app_commands, Object as DiscordObject
from common.utils.webread_utils import redact

def _iter_ac_modules():
    base = pathlib.Path(__file__).resolve().parents[1] / "commands"
    pkg_name = "ui.discord.commands"
    if str(base.parents[2]) not in sys.path:
        sys.path.insert(0, str(base.parents[2]))
    mods = [m.name for m in pkgutil.iter_modules([str(base)]) if m.name.startswith("ac_")]
    for name in sorted(mods):  # 安定化のためソート
        yield f"{pkg_name}.{name}"

def register_all(tree: app_commands.CommandTree):
    # 開発用ギルド（.env の DISCORD_GUILD_ID があればギルド登録、なければグローバル）
    # 要件: 数値チェックに失敗したら「即終了」する
    gid_raw = os.getenv("DISCORD_GUILD_ID")
    dev_guild = None
    if gid_raw:
        try:
            gid_int = int(gid_raw)
            if gid_int <= 0:
                raise ValueError("must be positive")
            dev_guild = DiscordObject(id=gid_int)
        except Exception:
            # 数値化できない/不正値 → 明確にメッセージを出してプロセス終了
            print(f"❌ 無効な DISCORD_GUILD_ID: {gid_raw}（整数のDiscordギルドIDを設定してください）")
            import sys as _sys
            _sys.exit(1)

    # 既存名（このプロセス内で既に載っているもの）を集合で管理
    used_names = {c.name for c in tree.get_commands()}

    # 管理情報: 登録済みコマンドのメタ（ヘルプ生成で使用）
    # 形式: {"name": str, "description": str, "usage": str, "module": str}
    global _COMMAND_REGISTRY
    _COMMAND_REGISTRY = []

    for mod_name in _iter_ac_modules():
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"❌ コマンド登録: モジュール読込エラー\t{mod_name}\n{redact(traceback.format_exc())}")
            continue

        get_command = getattr(mod, "get_command", None)
        if not callable(get_command):
            print(f"❌ コマンド登録: get_command未登録エラー\t{mod_name}")
            continue

        try:
            cmd = get_command()
        except Exception:
            print(f"❌ コマンド登録: get_command実行エラー\t{mod_name}\n{redact(traceback.format_exc())}")
            continue

        if not isinstance(cmd, app_commands.Command):
            print(f"❌ コマンド登録: 登録情報の形式が不正\t\t{mod_name}")
            continue

        # 既存の同名回避（global/guild で別スコープだが、二重登録は避ける）
        if cmd.name in used_names:
            print(f"❌ コマンド登録: /{cmd.name} コマンド重複エラー\t{mod_name}")
            continue

        # 登録前に同名を掃除（global / guild 両方を念のため除去）
        try:
            tree.remove_command(cmd.name)  # global
        except Exception:
            pass
        try:
            if dev_guild:
                tree.remove_command(cmd.name, guild=dev_guild)  # guild
        except Exception:
            pass

        # 開発中はギルドスコープに登録／本番はグローバル
        try:
            if dev_guild:
                tree.add_command(cmd, guild=dev_guild)   # ギルド登録
            else:
                tree.add_command(cmd)                    # グローバル登録
        except Exception as e:
            print(f"❌ コマンド登録: {redact(str(e))}\t{mod_name}")
            continue

        print(f"🔍 コマンド登録: /{cmd.name}")
        used_names.add(cmd.name)  # この実行で利用済みに

        # ヘルプ用メタを登録（モジュール側の HELP_TEXT があれば優先）
        help_text = getattr(mod, "HELP_TEXT", None)
        usage = f"/{cmd.name}"
        desc = (cmd.description or "") if isinstance(getattr(cmd, "description", None), str) else ""
        if isinstance(help_text, dict):
            usage = help_text.get("usage", usage)
            desc = help_text.get("description", desc)
        _COMMAND_REGISTRY.append({
            "name": cmd.name,
            "description": desc,
            "usage": usage,
            "module": mod_name,
        })

def list_registered_commands() -> list[dict]:
    """ヘルプ生成などで使う登録済みコマンドの管理情報を返す。"""
    try:
        return list(_COMMAND_REGISTRY)
    except NameError:
        return []
