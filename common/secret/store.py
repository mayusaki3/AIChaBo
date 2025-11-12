# common/secret/store.py
# ------------------------------------------------------------
# あいちゃぼ 機密ストア（Fernet固定）
#  - APIキー等の“機密”を暗号化して永続化
#  - バックエンド：Fernetのみ
#  - 保存場所：~/.aichabo/secretstore/{users.json, servers.json}
#  - 鍵：AC_MASTER_KEY（優先）／無ければ ~/.aichabo/master.key を自動生成
#  - 競合対策：プロセス内RLock＋アトミック書き込み（tmp→os.replace）
#  - “鍵の存在判定”は復号できるかで判断（文字列有無ではない）
# ------------------------------------------------------------

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import threading
from typing import Dict, Optional
from cryptography.fernet import Fernet

# ~/.aichabo/secretstore 配下に JSON を作る
HOME_DIR = pathlib.Path.home()
AICHABO_DIR = HOME_DIR / ".aichabo"
STORE_DIR = AICHABO_DIR / "secretstore"
USERS_JSON = STORE_DIR / "users.json"
SERVERS_JSON = STORE_DIR / "servers.json"
MASTER_KEY_PATH = AICHABO_DIR / "master.key"


def _ensure_dir(p: pathlib.Path) -> None:
    """親ディレクトリを作成（存在すれば何もしない）"""
    p.parent.mkdir(parents=True, exist_ok=True)


class SecretStore:
    """
    役割：
      - ユーザー鍵（user_id×provider）
      - サーバー鍵（guild_id×provider）
    を **暗号化**して JSON に保存/復号して取得する。

    設計ポリシー：
      - バックエンドは Fernet 固定（共通・テスト/移行容易）
      - 競合対策：プロセス内RLock＋アトミック書き込み（tmp→os.replace）
      - “鍵があるか”の判定は JSON 上の存在ではなく「復号できるか」で決める
    """

    def __init__(self) -> None:
        # プロセス内直列化用ロック
        self._lock = threading.RLock()

        # Fernet キーの準備
        key = os.getenv("AC_MASTER_KEY")
        if not key:
            _ensure_dir(MASTER_KEY_PATH)
            if MASTER_KEY_PATH.exists():
                key = MASTER_KEY_PATH.read_text(encoding="utf-8").strip()
            else:
                key = Fernet.generate_key().decode()
                MASTER_KEY_PATH.write_text(key, encoding="utf-8")
                try:
                    os.chmod(MASTER_KEY_PATH, 0o600)
                except Exception:
                    pass
        self._fernet = Fernet(key.encode())

        # JSONファイルの初期化（存在しなければ空で作成）
        for path in (USERS_JSON, SERVERS_JSON):
            if not path.exists():
                self._save_json(path, {})

    # ---- 公開情報 ----------------------------------------------------------

    def backend_name(self) -> str:
        """起動時のログ表示などに使用（固定文言）。"""
        return "Fernet (portable)"

    # ---- ユーザー鍵 API ----------------------------------------------------

    def put_user_key(self, user_id: int, provider: str, key_bytes: bytes) -> None:
        """指定ユーザー×プロバイダの鍵を保存（上書き）。"""
        provider = (provider or "").strip().lower()
        if not provider:
            raise ValueError("provider is required")

        with self._lock:
            data = self._load_json(USERS_JSON)
            node = data.setdefault(str(user_id), {}).setdefault("providers", {})
            node[provider] = self._enc(key_bytes)
            self._save_json(USERS_JSON, data)

    def get_user_key(self, user_id: int, provider: str) -> Optional[bytes]:
        """指定ユーザー×プロバイダの鍵を取得（復号成功時のみ bytes を返す）。"""
        provider = (provider or "").strip().lower()
        if not provider:
            return None
        with self._lock:
            data = self._load_json(USERS_JSON)
            enc = data.get(str(user_id), {}).get("providers", {}).get(provider)
            if not enc:
                return None
            try:
                return self._dec(enc)
            except Exception:
                return None

    def get_user_keys(self, user_id: int) -> Dict[str, bytes]:
        """指定ユーザーの全プロバイダ鍵を返す（復号できたものだけ）。"""
        with self._lock:
            data = self._load_json(USERS_JSON)
            d = data.get(str(user_id), {}).get("providers", {}) or {}
            out: Dict[str, bytes] = {}
            for prov, enc in d.items():
                try:
                    out[prov] = self._dec(enc)
                except Exception:
                    continue
            return out

    def delete_user_keys(self, user_id: int) -> bool:
        """指定ユーザーの全プロバイダ鍵を削除し、削除が発生したら True。未存在や変更なしは False。"""
        with self._lock:
            data = self._load_json(USERS_JSON)
            uid = str(user_id)
            node = data.get(uid)
            if not node:
                return False
            providers = node.get("providers") or {}
            if not providers:
                return False
            try:
                node["providers"] = {}
                self._save_json(USERS_JSON, data)
                return True
            except Exception:
                return False

    # ---- サーバー鍵 API ----------------------------------------------------

    def put_server_key(self, guild_id: int, provider: str, key_bytes: bytes) -> None:
        """指定サーバー×プロバイダの鍵を保存（上書き）。"""
        provider = (provider or "").strip().lower()
        if not provider:
            raise ValueError("provider is required")

        with self._lock:
            data = self._load_json(SERVERS_JSON)
            node = data.setdefault(str(guild_id), {}).setdefault("providers", {})
            node[provider] = self._enc(key_bytes)
            self._save_json(SERVERS_JSON, data)

    def get_server_key(self, guild_id: int, provider: str) -> Optional[bytes]:
        """指定サーバー×プロバイダの鍵を1件だけ返す（無ければ None）。"""
        prov = (provider or "").strip().lower()
        if not prov:
            return None
        all_keys = self.get_server_keys(guild_id)
        return all_keys.get(prov)

    def get_server_keys(self, guild_id: int) -> Dict[str, bytes]:
        """指定サーバーの全プロバイダ鍵を返す（復号できたものだけ）。"""
        with self._lock:
            data = self._load_json(SERVERS_JSON)
            d = data.get(str(guild_id), {}).get("providers", {}) or {}
            out: Dict[str, bytes] = {}
            for prov, enc in d.items():
                try:
                    out[prov] = self._dec(enc)
                except Exception:
                    continue
            return out

    def has_server_any_key(self, guild_id: int) -> bool:
        """指定サーバーに“復号できる鍵”が1つでもあれば True。"""
        return bool(self.get_server_keys(guild_id))

    def delete_server_keys(self, guild_id: int) -> bool:
        """指定サーバーの全プロバイダ鍵を削除し、削除が発生したら True。未存在や変更なしは False。"""
        with self._lock:
            data = self._load_json(SERVERS_JSON)
            gid = str(guild_id)
            node = data.get(gid)
            if not node:
                return False
            providers = node.get("providers") or {}
            if not providers:
                return False
            try:
                node["providers"] = {}
                self._save_json(SERVERS_JSON, data)
                return True
            except Exception:
                return False

    # ---- 内部：暗号化/復号 -------------------------------------------------

    def _enc(self, b: bytes) -> str:
        """bytes → Fernet → 文字列（判別用に 'fernet:' を付ける）"""
        token = self._fernet.encrypt(b).decode("utf-8")
        return "fernet:" + token

    def _dec(self, s: str) -> bytes:
        """文字列 → Fernet 復号 → bytes（'fernet:' 無しも後方互換として許可）"""
        if not s:
            raise ValueError("empty secret")
        if s.startswith("fernet:"):
            s = s[len("fernet:") :]
        return self._fernet.decrypt(s.encode("utf-8"))

    # ---- 内部：JSON I/O（アトミック書き込み＋RLock） ----------------------

    def _load_json(self, path: pathlib.Path) -> dict:
        """JSON の読み込み（壊れていたら空辞書で復旧）。"""
        _ensure_dir(path)
        if not path.exists():
            return {}
        with self._lock:
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                # 壊れていたら復旧（空辞書で上書き）
                try:
                    self._save_json(path, {})
                except Exception:
                    pass
                return {}

    def _save_json(self, path: pathlib.Path, data: dict) -> None:
        """
        JSON のアトミック書き込み：tmp に書いて os.replace で置き換え。
        クラッシュ/電断でも中途半端なファイルを残さない。
        """
        _ensure_dir(path)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        with self._lock:
            fd, tmpname = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(payload)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmpname, path)
            finally:
                try:
                    if os.path.exists(tmpname):
                        os.remove(tmpname)
                except Exception:
                    pass


# シングルトンとして公開
store = SecretStore()
