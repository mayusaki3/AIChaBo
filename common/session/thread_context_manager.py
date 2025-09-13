import os
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

# コンテキスト情報として、以下の内容を保持する。
# - 収集範囲 : スレッド内の開始位置以降のすべてのメッセージ
# - 開始位置 : 以下の条件のうち、一番後の位置（ui毎のthread_context内で判定）
#              1. 先頭メッセージ
#              2. /ac_summary の結果メッセージ
#              3. /ac_newtopic の次のメッセージ
# - 保持内容 : { "message": 発言者: メッセージ内容,
#                ※ 以下で始まるメッセージは無視
#                  ⚠️ 認証情報を
#                  💬/ac_newchat:
#                  💬/ac_invite:
#                  💬/ac_leave:
#                "msgid": メッセージID,
#                "refid": 返信元メッセージID,
#                "attachments": メッセージの添付（UI依存の構造を許容）,
#                "state": "OK"=完了 / ""=未処理・処理中（値はUI依存で拡張可） }
class ThreadContextManager:
    def __init__(self):
        # スレッドIDごとに [コンテキスト要素(dict)] を保持
        self.contexts: dict[str, list[dict]] = {}

        # スレッドIDごとに [メタ情報(dict)] を保持
        self.meta: dict[str, dict[str, Any]] = {}

        # 初期化済みスレッドID
        self.initialized_threads: set[str] = set()

    # スレッドIDごとにコンテキストを取得
    def get_context(self, thread_id: str) -> list[dict]:
        thread_id = str(thread_id)
        return self.contexts.get(thread_id, [])

    # スレッドIDごとにメッセージを追加
    def append_context(
        self,
        thread_id: str,
        message: str,
        msgid: str,
        refid: str | None,
        attachments: list | None
    ) -> Dict[str, Any]:
        thread_id = str(thread_id)
        if thread_id not in self.contexts:
            self.contexts[thread_id] = []

        attachments = attachments or []
        state = "OK" if len(attachments) == 0 else ""  # 添付なしは即"OK", 添付ありは未処理扱い

        entry: Dict[str, Any] = {
            "message": message,
            "msgid": str(msgid) if msgid is not None else "",
            "refid": str(refid) if refid is not None else "",
            "attachments": attachments or [],
            "state": state,
        }
        self.contexts[thread_id].append(entry)
        return entry

    # 追加情報注入用メッセージを生成（JST時刻差し込み）
    def get_injection_message(self, auth_data: dict) -> str:
        # auth_data["chat"]["injection_prompt"] / ["tone_prompt"] を想定
        injection = auth_data.get("chat", {}).get("injection_prompt", "") or ""
        jst = timezone(timedelta(hours=9))
        injection = injection.replace("{now_jst}", datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S (JST)"))
        tone = auth_data.get("chat", {}).get("tone_prompt", "") or ""
        if tone:
            injection += tone
        return injection

    # スレッドIDごとにコンテキストをクリア
    def clear_context(self, thread_id: str) -> None:
        thread_id = str(thread_id)
        self.contexts[thread_id] = []

    # スレッドIDが存在するか確認
    def has_context(self, thread_id: str) -> bool:
        thread_id = str(thread_id)
        return thread_id in self.contexts

    # JSON形式整形補助関数
    def _jsonable(self, obj):
        # UI依存のオブジェクトが混ざっていても JSON に落とせるように整形
        # プリミティブ系
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        # dict
        if isinstance(obj, dict):
            return {str(k): self._jsonable(v) for k, v in obj.items()}
        # list / tuple / set
        if isinstance(obj, (list, tuple, set)):
            return [self._jsonable(v) for v in obj]
        # その他（DiscordのAttachmentやMessage等）は文字列化で逃がす
        return str(obj)

    # 指定スレッドのコンテキストをファイルへエクスポート。
    # - 出力先: common/session/dump（固定）
    # - ファイル名: YYYYMMDD_スレッドID.json（JST）
    # - 常に全件を出力
    # - attachments がどんな構造でも JSON 化（非対応型は文字列化）
    # 戻り値: 出力したファイルの絶対パス
    def export_context(self, thread_id: str) -> str:
        thread_id = str(thread_id)
        data = self.get_context(thread_id)

        # 出力先ディレクトリ（固定）
        base_dir = os.path.join(os.path.dirname(__file__), "dump")
        os.makedirs(base_dir, exist_ok=True)

        # JST の日時でファイル名
        jst = timezone(timedelta(hours=9))
        date_str = datetime.now(jst).strftime("%Y%m%d%H%M%S")
        filename = f"{date_str}_{thread_id}.json"
        path = os.path.join(base_dir, filename)

        # JSON 化（UI依存構造も _jsonable で吸収）
        payload = {
            "thread_id": thread_id,
            "exported_at_jst": datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(data),
            "items": self._jsonable(data),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return os.path.abspath(path)

    # 全スレッドをエクスポート
    # すべてのスレッドについて export_context を実行。
    # 戻り値: 出力したファイルパスのリスト
    def export_all(self) -> list[str]:
        paths = []
        for thread_id in list(self.contexts.keys()):
            try:
                paths.append(self.export_context(thread_id))
            except Exception as e:
                # ここは必要に応じてログ出力に置き換え
                print(f"[export_all] export failed for {thread_id}: {e}")
        return paths

    # スレッドIDごとにメタ情報を取得
    def get_meta(self, thread_id: str, key: str, default=None):
        thread_id = str(thread_id)
        return self.meta.get(thread_id, {}).get(key, default)

    # スレッドIDごとにメタ情報を設定
    def set_meta(self, thread_id: str, key: str, value):
        thread_id = str(thread_id)
        self.meta.setdefault(thread_id, {})[key] = value

    # スレッドIDごとにメタ情報を1件取り出して削除
    def pop_meta(self, thread_id: str, key: str, default=None):
        thread_id = str(thread_id)
        d = self.meta.get(thread_id, {})
        return d.pop(key, default) if d else default

    # スレッドIDごとにメタ情報をクリア
    def clear_meta(self, thread_id: str, key: str | None = None):
        thread_id = str(thread_id)
        if key is None:
            self.meta.pop(thread_id, None)
        else:
            d = self.meta.get(thread_id)
            if d and key in d:
                del d[key]
                if not d:
                    self.meta.pop(thread_id, None)
