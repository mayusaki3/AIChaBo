[テストユーティリティ](../../README_TEST.md) > common/sessionモジュール単体テスト

# common/sessionモジュール単体テスト

## テスト番号と検証内容（Index）

| Suite | 目的（スコープ） | 機能 | モジュール |
|---|---|---|---|
| **T01-01** | UserSession 管理（USM） | get/set/has + api_key 非保持（深い階層も除去） | `common/session/user_session_manager.py` |
| **T02-01** | ServerSession 管理（SSM） | shared auth config（set/get/clear）+ options（set/get/clear/all） | `common/session/server_session_manager.py` |
| **T02-02** | ServerSession 分岐網羅（SSM） | 起動時ロード分岐（exists/例外復旧）+ strip 再帰 + clear_option 空削除 | `common/session/server_session_manager.py` |

---

## テスト詳細

### T01-01 : UserSession 管理（USM）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-01-01** | guard(None) | `get_session(None)` は `None` を返す | `common/session/user_session_manager.py` |
| **T01-01-02** | 未登録 | 未登録 user_id の `get_session()` は `None` を返す | `common/session/user_session_manager.py` |
| **T01-01-03** | set/get + api_key 非保持 | `set_session()` 後 `get_session()` が provider/model を保持し、`api_key` を深い階層まで除去する | `common/session/user_session_manager.py` |
| **T01-01-04** | provider/model 必須 | provider/model が不足すると `ValueError` | `common/session/user_session_manager.py` |
| **T01-01-05** | 必須不足は ValueError | `chat.provider/chat.model` が不足すると `ValueError` | `common/session/user_session_manager.py` |
| **T01-01-06** | chat 型不正は ValueError | `chat` が dict でない場合 `ValueError("chat must be a dict")` | `common/session/user_session_manager.py` |
| **T01-01-07** | 空白のみは ValueError | `chat.provider` または `chat.model` が空白のみの場合 `ValueError` | `common/session/user_session_manager.py` |
| **T01-01-08** | 起動時ロード例外復旧 | 起動時ロードで例外が出ても `sessions={}` にし、`usersessions.json` を `{}` で復旧する | `common/session/user_session_manager.py` |
| **T01-01-09** | 起動時ロード（未作成） | 起動時に `usersessions.json` が存在しない場合は読み込みを行わず、空の `sessions` で起動する | `common/session/user_session_manager.py` |

#### 実行

```bash
python -m tests.common.session.T01_UserSession_01_user_session_test
```

---

### T02-01 : ServerSession 管理（SSM）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-01-01** | guard(None) | `get_shared_auth_config(None)` は `{}` を返す | `common/session/server_session_manager.py` |
| **T02-01-02** | 未登録 | 未登録 guild_id の `get_shared_auth_config()` は `{}` を返す | `common/session/server_session_manager.py` |
| **T02-01-03** | shared auth set/get | `set_shared_auth_config()` → `get_shared_auth_config()`（`chat.provider/chat.model` 必須、`api_key` は保持しない） | `common/session/server_session_manager.py` |
| **T02-01-04** | shared auth clear | `clear_shared_auth_config()` 後は `{}` に戻る | `common/session/server_session_manager.py` |
| **T02-01-05** | 必須不足は ValueError | `chat.provider/chat.model` が不足すると `ValueError` | `common/session/server_session_manager.py` |
| **T02-01-06** | options set/get/clear/all | option の set/get/clear と `all_options()` の整合 | `common/session/server_session_manager.py` |

#### 実行

```bash
python -m tests.common.session.T02_ServerSession_01_server_session_test
```

---

### T02-02 : ServerSession 管理（SSM）分岐（Branch）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-02-01** | 起動時ロード（exists False） | shared/opts の保存ファイルが存在しない場合に空で起動する | `common/session/server_session_manager.py` |
| **T02-02-02** | 起動時ロード（shared 読み込み例外） | shared の read_text が例外でも復旧して空で起動する | `common/session/server_session_manager.py` |
| **T02-02-03** | 起動時ロード（opts 読み込み例外） | opts の read_text が例外でも復旧して空で起動する | `common/session/server_session_manager.py` |
| **T02-02-04** | _strip_api_keys 再帰除去 | dict/list/other の混在でも api_key を再帰的に除去する | `common/session/server_session_manager.py` |
| **T02-02-05** | chat 型不正 | chat が dict 以外の場合は ValueError | `common/session/server_session_manager.py` |
| **T02-02-06** | provider/model trim | provider/model の前後空白を除去して保存される | `common/session/server_session_manager.py` |
| **T02-02-07** | clear_option: sid 空なら削除 | sid の dict が空になった場合に sid 自体を削除する | `common/session/server_session_manager.py` |
| **T02-02-08** | clear_option: sid 未登録 no-op | 未登録 sid を clear しても例外なく no-op で終了する | `common/session/server_session_manager.py` |
| **T02-02-09** | clear_option: key 未登録 no-op | 登録済 sid でも未登録 key を clear して例外なく no-op で終了する | `common/session/server_session_manager.py` |

#### 実行

```bash
python -m tests.common.session.T02_ServerSession_02_server_session_branch_test
```

---
[テストユーティリティ](../../README_TEST.md) > common/sessionモジュール単体テスト
