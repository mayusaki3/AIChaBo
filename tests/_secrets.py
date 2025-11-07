# tests/_secrets.py
# コメント: .envtest を読み込み、見つかった鍵だけシード。無い場合はモック実行へフォールバック。
import os
from pathlib import Path
from dotenv import dotenv_values
from common.secret.store import store

TEST_STORE_DEFAULT = str(Path("common/secret/test").resolve())

# 既定のストア切替（必要なら環境変数で上書き可）
os.environ.setdefault("AIChaBo_STORE_DIR", TEST_STORE_DEFAULT)

ENVTEST_PATH = Path("utiltests/.envtest")
ENV = dotenv_values(str(ENVTEST_PATH)) if ENVTEST_PATH.exists() else {}

TEST_USER_ID = 111
TEST_GUILD_ID = 222

OPENAI_KEY = ENV.get("AIChaBo_TEST_OPENAI_KEY")
CLAUDE_KEY = ENV.get("AIChaBo_TEST_CLAUDE_KEY")
GEMINI_KEY = ENV.get("AIChaBo_TEST_GEMINI_KEY")

# .envtest が無ければモックに自動切替
if not ENV:
    os.environ["AIChaBo_TEST_MOCK"] = "1"

def seed():
    # 必要なものだけ登録（ユーザー鍵/サーバー鍵はどちらでも可。ここではユーザー鍵のみ）
    if OPENAI_KEY:
        store.put_user_key(TEST_USER_ID, "openai", OPENAI_KEY.encode("utf-8"))
    if CLAUDE_KEY:
        store.put_user_key(TEST_USER_ID, "anthropic", CLAUDE_KEY.encode("utf-8"))
    if GEMINI_KEY:
        store.put_user_key(TEST_USER_ID, "google", GEMINI_KEY.encode("utf-8"))

def cleanup():
    # 投入した鍵を削除（他プロバイダに影響しない形）
    store.delete_user_keys(TEST_USER_ID)
    store.delete_server_keys(TEST_GUILD_ID)
