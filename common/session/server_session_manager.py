# common/session/server_session_manager.py
# ------------------------------------------------------------
# ServerSessionManager:
# - 共有用“非機密”設定（サーバー単位）を保持（api_key は保持しない）
# - システムオプション(printmsg等)を保持
# ------------------------------------------------------------
import json, pathlib, threading
from copy import deepcopy

STORE = pathlib.Path.home()/".aichabo"; STORE.mkdir(parents=True, exist_ok=True)
PATH_SHARED = STORE/"servershared.json"
PATH_OPTS   = STORE/"serveropts.json"

class ServerSessionManager:
    def __init__(self):
        self._lock = threading.RLock()
        self.sessions = {}         # 旧: auth_data（非推奨）
        self.system_options = {}
        self._shared_auth_config = {}  # サーバー共有“非機密”設定

        # 起動時ロード
        try:
            if PATH_SHARED.exists():
                self._shared_auth_config = json.loads(PATH_SHARED.read_text(encoding="utf-8"))
        except Exception:
            self._shared_auth_config = {}
            PATH_SHARED.write_text("{}", encoding="utf-8")
        try:
            if PATH_OPTS.exists():
                self.system_options = json.loads(PATH_OPTS.read_text(encoding="utf-8"))
        except Exception:
            self.system_options = {}
            PATH_OPTS.write_text("{}", encoding="utf-8")

    def _save_shared(self):
        PATH_SHARED.write_text(json.dumps(self._shared_auth_config, ensure_ascii=False), encoding="utf-8")

    def _save_opts(self):
        PATH_OPTS.write_text(json.dumps(self.system_options, ensure_ascii=False), encoding="utf-8")

    # ---------- 共有用“非機密”設定 ----------
    @staticmethod
    def _strip_api_keys(obj):
        if isinstance(obj, dict):
            return {k: ServerSessionManager._strip_api_keys(v)
                    for k, v in obj.items() if k != "api_key"}
        if isinstance(obj, list):
            return [ServerSessionManager._strip_api_keys(v) for v in obj]
        return obj

    # 指定サーバーのサーバー共有“非機密”情報を設定。
    def set_shared_auth_config(self, server_id: int, config: dict) -> None:
        sid = str(server_id)
        clean = self._strip_api_keys(config)
        with self._lock:
            self._shared_auth_config[sid] = clean
            self._save_shared()

    # 指定サーバーのサーバー共有“非機密”情報を取得。
    def get_shared_auth_config(self, server_id: int) -> dict:
        sid = str(server_id)
        with self._lock:
            return deepcopy(self._shared_auth_config.get(sid, {}))

    # 指定サーバーのサーバー共有“非機密”情報を削除。
    def clear_shared_auth_config(self, server_id: int) -> None:
        sid = str(server_id)
        with self._lock:
            self._shared_auth_config.pop(sid, None)
            self._save_shared()

    # システムオプション設定
    def set_option(self, server_id: int, key: str, value: bool) -> None:
        sid = str(server_id); key = key.lower()
        with self._lock:
            opts = self.system_options.setdefault(sid, {})
            opts[key] = bool(value)
            self._save_opts()

    # システムオプション取得
    def get_option(self, server_id: int, key: str, default: bool | None = None) -> bool | None:
        sid = str(server_id); key = key.lower()
        with self._lock:
            return self.system_options.get(sid, {}).get(key, default)

    # システムオプション削除
    def clear_option(self, server_id: int, key: str) -> None:
        sid = str(server_id); key = key.lower()
        with self._lock:
            if sid in self.system_options:
                self.system_options[sid].pop(key, None)
                if not self.system_options[sid]:
                    self.system_options.pop(sid, None)
                self._save_opts()

    # 全システムオプション取得
    def all_options(self, server_id: int) -> dict[str, bool]:
        with self._lock:
            return dict(self.system_options.get(str(server_id), {}))

# シングルトンとして使うインスタンス
server_session_manager = ServerSessionManager()
