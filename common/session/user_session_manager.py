# common/session/user_session_manager.py
# ------------------------------------------------------------
# UserSessionManager: ユーザー別の“非機密”設定を管理（api_keyは保持しない）
# - set_session() 時に深い階層まで api_key を除去
# - 簡易永続化 ~/.aichabo/usersessions.json
# ------------------------------------------------------------
import json, pathlib, threading
from copy import deepcopy

STORE = pathlib.Path.home()/".aichabo"; STORE.mkdir(parents=True, exist_ok=True)
PATH  = STORE/"usersessions.json"

class UserSessionManager:
    def __init__(self):
        self._lock = threading.RLock()
        self.sessions = {}
        # 起動時ロード（壊れていれば空）
        try:
            if PATH.exists():
                self.sessions = json.loads(PATH.read_text(encoding="utf-8"))
        except Exception:
            self.sessions = {}
            PATH.write_text("{}", encoding="utf-8")

    def _save(self):
        PATH.write_text(json.dumps(self.sessions, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _strip_api_keys(obj):
        # dict/list を再帰して api_key を除去
        if isinstance(obj, dict):
            return {k: UserSessionManager._strip_api_keys(v)
                    for k, v in obj.items() if k != "api_key"}
        if isinstance(obj, list):
            return [UserSessionManager._strip_api_keys(v) for v in obj]
        return obj

    # 指定ユーザーIDのセッション情報を登録。
    def set_session(self, user_id: int, auth_data: dict):
        uid = str(user_id)
        clean = self._strip_api_keys(auth_data)
        # 必須: chat.provider / chat.model（空白のみは不可）
        chat = clean.get("chat") or {}
        if not isinstance(chat, dict):
            raise ValueError("chat must be a dict")
        prov = (chat.get("provider") or "").strip()
        model = (chat.get("model") or "").strip()
        if not prov or not model:
            raise ValueError("chat.provider and chat.model are required")
        # 正規化（空白除去のみ。display/別正規化は上位で実施）
        chat["provider"] = prov
        chat["model"] = model
        clean["chat"] = chat
        with self._lock:
            clean["user_id"] = uid
            self.sessions[uid] = clean
            self._save()

    # 指定ユーザーIDのセッション情報を削除。
    def clear_session(self, user_id: int):
        uid = str(user_id)
        with self._lock:
            self.sessions.pop(uid, None)
            self._save()

    # 指定ユーザーのセッション情報を取得。
    def get_session(self, user_id: int):
        uid = str(user_id)
        with self._lock:
            v = self.sessions.get(uid)
            return deepcopy(v) if v else None

    # 指定ユーザーのセッションが存在するか確認。
    def has_session(self, user_id: int) -> bool:
        uid = str(user_id)
        with self._lock:
            return uid in self.sessions

# シングルトンとして使うインスタンス
user_session_manager = UserSessionManager()
