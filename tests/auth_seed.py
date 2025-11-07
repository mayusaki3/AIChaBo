# -*- coding: utf-8 -*-
"""
auth_seed.py
- テスト用: Discord を経由せずに USM/SSM/SecretStore に “種まき” するユーティリティ
- 既定は dry-run。--confirm 指定で実際に書き込み。
- 例:
  python -m utiltests.auth_seed --user 111 --provider openai --model gpt-4o \
      --key %TEST_OPENAI_KEY% --target user --confirm

  python -m utiltests.auth_seed --guild 222 --provider openai --model gpt-4o \
      --key %TEST_OPENAI_KEY% --target server --confirm
"""
import argparse
import sys

from common.chat.provider import normalize_provider
from common.session.user_session_manager import user_session_manager as USM
from common.session.server_session_manager import server_session_manager as SSM
from common.secret.store import store


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--user", type=int, help="対象ユーザーID")
    p.add_argument("--guild", type=int, help="対象ギルドID")
    p.add_argument("--provider", required=True, help="openai/claude/gemini など（大文字可）")
    p.add_argument("--model", required=True, help="モデル名（例: gpt-4o）")
    p.add_argument("--key", required=True, help="APIキー（実キー）")
    p.add_argument("--target", choices=["user", "server"], required=True, help="書込先: user or server")
    p.add_argument("--confirm", action="store_true", help="実際に書き込む（指定が無いとdry-run）")
    args = p.parse_args()

    provider = normalize_provider(args.provider)

    if args.target == "user":
        if not args.user:
            print("ERROR: --user is required for target=user", file=sys.stderr)
            sys.exit(2)
        # 非機密（USM）
        session = USM.get_session(args.user) or {}
        chat = session.get("chat") or {}
        chat.update({"provider": provider, "model": args.model})
        session["chat"] = chat
        print(f"[USM] user={args.user} chat={chat}")
        # 機密（SecretStore）
        print(f"[Store] user={args.user} provider={provider} key=****")
        if args.confirm:
            USM.set_session(args.user, session)
            store.put_user_key(args.user, provider, args.key.encode("utf-8"))
            print("APPLIED.")
        else:
            print("DRY-RUN (use --confirm to apply)")

    else:
        if not args.guild:
            print("ERROR: --guild is required for target=server", file=sys.stderr)
            sys.exit(2)
        # 非機密（SSM）
        shared = SSM.get_shared_auth_config(args.guild) or {}
        chat = (shared.get("chat") or {})
        chat.update({"provider": provider, "model": args.model})
        shared["chat"] = chat
        print(f"[SSM] guild={args.guild} chat={chat}")
        # 機密（SecretStore）
        print(f"[Store] guild={args.guild} provider={provider} key=****")
        if args.confirm:
            SSM.set_shared_auth_config(args.guild, shared)
            store.put_server_key(args.guild, provider, args.key.encode("utf-8"))
            print("APPLIED.")
        else:
            print("DRY-RUN (use --confirm to apply)")


if __name__ == "__main__":
    main()
