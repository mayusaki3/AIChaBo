# common/secret/store.py
# ------------------------------------------------------------
# あいちゃぼ用 SecretStore（APIキー等の機密のみを“永続”保管する層）
# - 責務：暗号化した上でディスク保存し、必要時に復号して返す
# - 非責務：一時セッション/オプション管理（それは common/session 側の責務）
#
# 暗号化方式
#   * Windows: DPAPI（ユーザー/マシンに紐づく） → 追加鍵不要
#   * 非Windows: Fernet（対称鍵） → 環境変数 AC_MASTER_KEY が必須
#
# 保存場所
#   ~/.aichabo/secretstore/{users.json, servers.json}
#   - users.json   : ユーザー単位の鍵（user_id -> {provider: enc_key}）
#   - servers.json : サーバー（Guild）単位の共有鍵（guild_id -> {provider: enc_key}）
#
# 重要方針
#   - APIキーは必ずここだけに保存（SessionManagerには保存しない）
#   - 例外は上位で扱う想定。ただし初期化時の致命的条件は明確に raise する
#   - ログに鍵を出さない（この層では一切 print しない）
# ------------------------------------------------------------

from __future__ import annotations
import os
import sys
import json
import base64
import pathlib
from typing import Optional, Dict, Any


# 保存ディレクトリを作成（ユーザーごとに分かれるホーム直下）
STORE_DIR = pathlib.Path.home() / ".aichabo" / "secretstore"
STORE_DIR.mkdir(parents=True, exist_ok=True)


class SecretStore:
    """APIキーなどの“機密”を暗号化して永続化するストア。"""

    def __init__(self) -> None:
        # ファイルパスの初期化
        self._path_user = STORE_DIR / "users.json"
        self._path_srv = STORE_DIR / "servers.json"
        for p in (self._path_user, self._path_srv):
            if not p.exists():
                p.write_text("{}", encoding="utf-8")

        # ---- 方式選択: dpapi(Windows専用) / fernet(両用) ----
        self._is_windows = sys.platform.startswith("win")
        self._backend = None          # "dpapi" or "fernet"
        self._fernet = None           # fernet時のみ設定

        # 環境変数で強制: AC_SECRET_BACKEND=dpapi|fernet
        forced = (os.getenv("AC_SECRET_BACKEND") or "").strip().lower()
        if forced in ("dpapi", "fernet"):
            prefer_dpapi = forced == "dpapi"
        else:
            # 既定: Windowsはdpapi、非Windowsはfernet
            prefer_dpapi = self._is_windows

        # dpapiが使えるか（pywin32依存）
        dpapi_ok = False
        if self._is_windows:
            try:
                import win32crypt  # type: ignore  # noqa
                dpapi_ok = True
            except Exception:
                dpapi_ok = False

        use_dpapi = prefer_dpapi and dpapi_ok
        if use_dpapi:
            self._backend = "dpapi"
            # DPAPIは追加キー不要
        else:
            # Fernet（両用）: AC_MASTER_KEY を優先。無ければ ~/.aichabo/master.key を自動生成
            self._backend = "fernet"
            key = os.getenv("AC_MASTER_KEY")
            if not key:
                from cryptography.fernet import Fernet  # 遅延import
                mk_path = (STORE_DIR.parent / "master.key")
                if mk_path.exists():
                    key = mk_path.read_text(encoding="utf-8").strip()
                else:
                    key = Fernet.generate_key().decode()
                    mk_path.write_text(key, encoding="utf-8")
                    try:
                        os.chmod(mk_path, 0o600)
                    except Exception:
                        pass
            from cryptography.fernet import Fernet
            self._fernet = Fernet(key.encode())

    # 公開: 現在のバックエンド名を返す（UI表示用）
    def backend_name(self) -> str:
        return "Windows DPAPI" if self._backend == "dpapi" else "Fernet (portable)"

    # --------------------------
    # 内部ユーティリティ
    # --------------------------
    @staticmethod
    def _load_json(path: pathlib.Path) -> Dict[str, Any]:
        """JSONファイルを読み込む（壊れていたら空で復旧）。"""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # 壊れた場合は空オブジェクトで復旧し、上書き保存
            data: Dict[str, Any] = {}
            path.write_text("{}", encoding="utf-8")
            return data

    @staticmethod
    def _save_json(path: pathlib.Path, obj: Dict[str, Any]) -> None:
        """JSONファイルを書き出す。"""
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    # --------------------------
    # 暗号化/復号
    # --------------------------
    def _encrypt(self, raw: bytes) -> str:
        """平文bytesを暗号化し、JSONに入れやすい文字列として返す。"""
        if self._backend == "dpapi":
            # DPAPIで暗号化 → base64文字列化して保存
            import win32crypt  # type: ignore
            enc = win32crypt.CryptProtectData(raw, None, None, None, None, 0)
            return base64.b64encode(enc).decode("utf-8")
        else:
            # Fernetで暗号化（すでにUTF-8→bytes想定）
            assert self._fernet is not None
            return self._fernet.encrypt(raw).decode("utf-8")

    def _decrypt(self, enc_text: str) -> bytes:
        """暗号文字列を復号し、平文bytesを返す。"""
        if self._backend == "dpapi":
            # base64 → DPAPI復号
            import win32crypt  # type: ignore
            raw = base64.b64decode(enc_text.encode("utf-8"))
            return win32crypt.CryptUnprotectData(raw, None, None, None, 0)[1]
        else:
            assert self._fernet is not None
            return self._fernet.decrypt(enc_text.encode("utf-8"))

    # --------------------------
    # 公開API（ユーザー鍵）
    # --------------------------
    def put_user_key(self, user_id: int, provider: str, key: bytes) -> None:
        """ユーザー単位の鍵を保存（上書き）。"""
        data = self._load_json(self._path_user)
        bucket = data.setdefault(str(user_id), {})
        bucket[provider] = self._encrypt(key)
        self._save_json(self._path_user, data)

    def get_user_key(self, user_id: int, provider: str) -> Optional[bytes]:
        """ユーザー単位の鍵を取得（なければNone）。"""
        data = self._load_json(self._path_user)
        enc = data.get(str(user_id), {}).get(provider)
        if not enc:
            return None
        try:
            return self._decrypt(enc)
        except Exception:
            # 復号失敗（キー違い/破損）は None を返す
            return None

    def delete_user_keys(self, user_id: int) -> None:
        """ユーザー単位の鍵を全削除。"""
        data = self._load_json(self._path_user)
        data.pop(str(user_id), None)
        self._save_json(self._path_user, data)

    # --------------------------
    # 公開API（サーバー共有鍵：サーバー単位）
    # --------------------------
    def put_server_key(self, guild_id: int, provider: str, key: bytes) -> None:
        """サーバー（Guild）単位の共有鍵を保存（上書き）。"""
        data = self._load_json(self._path_srv)
        bucket = data.setdefault(str(guild_id), {})
        bucket[provider] = self._encrypt(key)
        self._save_json(self._path_srv, data)

    def get_server_key(self, guild_id: int, provider: str) -> Optional[bytes]:
        """サーバー（Guild）単位の共有鍵を取得（なければNone）。"""
        data = self._load_json(self._path_srv)
        enc = data.get(str(guild_id), {}).get(provider)
        if not enc:
            return None
        try:
            return self._decrypt(enc)
        except Exception:
            return None

    def delete_server_keys(self, guild_id: int) -> None:
        """サーバー（Guild）単位の共有鍵を全削除。"""
        data = self._load_json(self._path_srv)
        data.pop(str(guild_id), None)
        self._save_json(self._path_srv, data)


# 使い方例：
#   from common.secret.store import store
#   store.put_user_key(user_id, "openai", b"sk-xxxx")
#   key = store.get_user_key(user_id, "openai")   # → bytes or None
#   store.delete_user_keys(user_id)
#
#   # サーバー（共有）鍵
#   store.put_server_key(guild_id, "openai", b"sk-xxxx")
#   key = store.get_server_key(guild_id, "openai")
#   store.delete_server_keys(guild_id)

store = SecretStore()
