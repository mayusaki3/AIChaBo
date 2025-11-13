[テストユーティリティ](../../README_TEST.md) > M02: common/chatモジュール単体テスト

# M02: ccommon/chatモジュール単体テスト

## テスト番号と検証内容（Index）

| Suite | 目的（スコープ） | 機能 | モジュール |
|---|---|---|---|
| **T01-01** | Provider 正規化                           | known→canonical / unknown→lower / display labels                                            | `common/chat/provider.py`     |
| **T02-01** | Auth 解決（opt-in）                       | policy・sessions からの解決（user>server優先, keys 不足時 {}）                              | `common/chat/auth.py`         |
| **T03-01** | ChatCore モック LLM                        | provider echo・最低限の往復                                                                 | `common/chat/chat_core.py`    |
| **T04-01** | ChatLoop MOCK                             | empty 固定応答 / invalid-provider 応答 / 最小ハッピーパス                                   | `common/chat/chat_loop.py`    |
| **T04-02** | ChatLoop Edges                            | 明示 model 優先 / policy の追加パラメータ透過 / provider 例外→既定メッセージ                | `common/chat/chat_loop.py`    |
| **T04-03** | ChatLoop 更なるエッジ                      | api_key 不足ガイダンス / messages 全空 / policy=None / provider 返り値 None/空              | `common/chat/chat_loop.py`    |
| **T04-04** | ChatLoop 入力正規化（provider/model）      | provider trim/upper / policy{} + 明示 model / provider 返り値 None の文字列化               | `common/chat/chat_loop.py`    |
| **T04-05** | ChatLoop セッション経由の方針・上書き       | sessions→policy 抽出 / 明示 model 優先 / 追加引数の透過                                     | `common/chat/chat_loop.py`    |
| **T04-06** | ChatLoop パス網羅（追加カバレッジ）        | 明示 model 優先 / policy から model / 非文字列→`str()` / 空応答固定文 / provider 例外処理   | `common/chat/chat_loop.py`    |
| **T04-07** | ChatLoop Helpers                          | 方針解決（user overrides server）/ APIキー解決 / provider 関数解決（`ai.{prov}.*` 参照）    | `common/chat/chat_loop.py`    |

---

## テスト詳細

### T01-01 : Provider 正規化

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-01-01** | エイリアス正規化 | known エイリアス → canonical 名へ変換      | `common/chat/provider.py`   |
| **T01-01-02** | 未知入力処理     | unknown 入力 → lower-case 化              | `common/chat/provider.py`   |
| **T01-01-03** | 表示統一         | display label 一致（canonical 名 → 表示名）| `common/chat/provider.py`   |
| **T01-01-04** | 表示空入力       | 空入力時の display 名ハンドリング          | `common/chat/provider.py`   |

#### 実行

```bash
python -m tests.common.chat.T01_Provider_01_provider_test
```

---

### T02-01 : Auth 解決（opt-in）

> 実行前に `AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1` を設定してください（安全のため既定は SKIP ）。

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-01-01** | 無認証解決 | USM/SSM 空、keys 無 → `{}` | `common/chat/auth.py` |
| **T02-01-02** | USMのみ非機密 | USMに provider/model、keys 無 → `{}` | `common/chat/auth.py` |
| **T02-01-03** | ユーザー鍵優先 | USM( provider/model ) + user_key → 解決（`max_tokens` 既定付与） | `common/chat/auth.py` |
| **T02-01-04** | サーバ鍵フォールバック | user_key 無、server_keys に `openai` → 解決 | `common/chat/auth.py` |
| **T02-01-05** | provider正規化 | USM provider が `OPENAI` でも normalize → `openai` キーに一致 | `common/chat/auth.py` |
| **T02-01-06** | model欠落 | providerのみ → `{}` | `common/chat/auth.py` |
| **T02-01-07** | SSM優先（USM無） | USM 無・SSM に provider/model、server_keys で解決 | `common/chat/auth.py` |

#### 実行

```bash
# bash/zsh
export AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
python -m tests.common.chat.T03_Auth_01_auth_resolve_test
unset AIChaBo_TEST_ENABLE_AUTH_RESOLVE

# PowerShell
$env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
python -m tests.common.chat.T03_Auth_01_auth_resolve_test
Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE
```

---

### T03-01 : ChatCore モック LLM

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T03-01-01** | 入力ガード | text="   " を例外またはガードで弾く | `common/chat/chat_core.py` |
| **T03-01-02** | 必須項目 | context.chat.provider / context.chat.model 欠落で ValueError | `common/chat/chat_core.py` |
| **T03-01-03** | 最小往復 | chat_fn 未指定なら echo、chat_fn 指定時は委譲 | `common/chat/chat_core.py` |
| **T03-01-04** | 入力ガード（型） | text=None で ValueError（非文字列分岐の到達） | `common/chat/chat_core.py` |
| **T03-01-05** | echo 分岐 | chat_fn 無し → trim 後にそのまま返す | `common/chat/chat_core.py` |
| **T03-01-06** | chat_fn 注入 | `send_once(..., chat_fn=...)` で注入関数が呼ばれ、`provider/model/text` が正しく引数で渡ることを検証 | `common/chat/chat_core.py` |

```bash
python -m tests.common.chat.T03_ChatCore_01_chat_core_test
```

---

### T04-01 : ChatLoop 基本

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-01-01** | 空入力の固定化 | context_list=["   "] → （入力が空です）を返す | `common/chat/chat_loop.py` |
| **T04-01-02** | model 未解決ガイド | model=None かつ policy={} → （モデル設定が見つかりません…）を返す | `common/chat/chat_loop.py` |
| **T04-01-03** | 正常系（依存スタブ） | policy で model 補完、_resolve_api_key を "KEY" にパッチ、_get_provider_chat_fn をモックして "pong" を返す | `common/chat/chat_loop.py` |
| **T04-01-04** | provider ガード | provider="   " → （プロバイダが不正です）を返す | `common/chat/chat_loop.py` |

```bash
python -m tests.common.chat.T04_ChatLoop_01_chat_loop_test
```

---

### T04-02 : ChatLoop Edges

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-02-01** | 明示 model の優先 | policy の model より引数 model を優先（fake_call に渡る model を検証） | `common/chat/chat_loop.py` |
| **T04-02-02** | 追加パラメータ透過 | policy の temperature/top_p などがプロバイダ関数に **extra** として渡る | `common/chat/chat_loop.py` |
| **T04-02-03** | 例外ハンドリング | プロバイダ関数が例外を投げたら `"（チャット実行でエラーが発生しました）"` を返す | `common/chat/chat_loop.py` |

```bash
python -m tests.common.chat.T04_ChatLoop_02_chat_loop_edges_test
```

---

### T04-03 : ChatLoop More Edges

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-03-01** | APIキー未設定 | `_resolve_api_key` が None/空 → 既定メッセージ | `common/chat/chat_loop.py` |
| **T04-03-02** | 全メッセージ空白化 | `context_list=["  ","\t"," \n "]` → 空入力メッセージ | `common/chat/chat_loop.py` |
| **T04-03-03** | policy=None | policy=None は現行実装上エラー → 既定メッセージ応答 | `common/chat/chat_loop.py` |
| **T04-03-04** | 空文字返却 | provider 関数が `""` を返す枝（戻り値型の許容確認） | `common/chat/chat_loop.py` |
| **T04-03-05** | 関数取得失敗 | `_get_provider_chat_fn` が `None` → 例外ハンドリング文言 | `common/chat/chat_loop.py` |

```bash
python -m tests.common.chat.T04_ChatLoop_03_chat_loop_more_edges_test
```

---

### T04-04 : ChatLoop Cover Rest

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-04-01** | provider 前処理 | `provider="  OPENAI  "` を許容（前後空白/大文字） | `common/chat/chat_loop.py` |
| **T04-04-02** | policy 空辞書 | `policy={}` かつ `model="explicit"` で正常完了 | `common/chat/chat_loop.py` |
| **T04-04-03** | ChatLoop cover rest | provider returns None → `"None"`（stringify 挙動を検証） | `common/chat/chat_loop.py` |

```bash
python -m tests.common.chat.T04_ChatLoop_04_chat_loop_cover_rest_test
```

---

### T04-05 : ChatLoop Helper Paths

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-05-01** | policy→key→provider 呼出 | policy(model)採用・_resolve_api_key・_get_provider_chat_fn を通る／extra受渡 | `common/chat/chat_loop.py` |
| **T04-05-02** | 明示model優先＋extra透過 | 明示 model が policy を上書き／extra(top_p等) が provider関数へ渡る | `common/chat/chat_loop.py` |


```bash
python -m tests.common.chat.T04_ChatLoop_05_chat_loop_helper_paths_test
```

---

### T04-06 : ChatLoop メッセージ正規化 & 直呼びパス網羅

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-06-01** | ChatLoop paths cover | policyに明示モデルがある場合、そのモデルが優先される | `common/chat/chat_loop.py` |
| **T04-06-02** | ChatLoop paths cover | policyにモデルが無い場合、デフォルトモデルが適用される | `common/chat/chat_loop.py` |
| **T04-06-03** | ChatLoop paths cover | providerから非文字列が返る場合は `str()` 変換される | `common/chat/chat_loop.py` |
| **T04-06-04** | ChatLoop paths cover | 空文字や空応答のとき `（応答が空でした）` と返す | `common/chat/chat_loop.py` |
| **T04-06-05** | ChatLoop paths cover | providerが例外を投げた場合にエラーメッセージを返す | `common/chat/chat_loop.py` |

```bash
python -m tests.common.chat.T04_ChatLoop_06_chat_loop_paths_cover_test
```

---

### T04-07 : ChatLoop Helper

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-07-01** | セッション方針マージ | `_extract_chat_policy_from_sessions` が server+user をマージし、ユーザー設定で上書きする | `common/chat/chat_loop.py` |
| **T04-07-02** | APIキー解決優先度 | `_resolve_api_key` が user → server → None の優先度でキーを解決する | `common/chat/chat_loop.py` |
| **T04-07-03** | provider関数解決(成功) | `_get_provider_chat_fn` が `ai.{provider}.{provider}_api.call_{provider}_chat` を取得して返す | `common/chat/chat_loop.py` |
| **T04-07-04** | provider関数解決(失敗) | `_get_provider_chat_fn` がエントリ不在時に `RuntimeError` を送出する | `common/chat/chat_loop.py` |
| **T04-07-05** | guild-only方針 | `_extract_chat_policy_from_sessions` が guild のみ指定時に SSM のみ参照する | `common/chat/chat_loop.py` |
| **T04-07-06** | ID未指定ガード | `_extract_chat_policy_from_sessions` が user/guild 未指定時に USM/SSM を呼ばず `{}` を返す | `common/chat/chat_loop.py` |
| **T04-07-07** | APIキー解決(guildのみ) | `_resolve_api_key` が user_id=None, guild_idあり時に server_key のみ問い合わせる | `common/chat/chat_loop.py` |
| **T04-07-08** | APIキー解決(userのみ/鍵無し) | `_resolve_api_key` が user_idあり, guild_id=None 時に user_key のみ問い合わせ、未取得なら None を返す | `common/chat/chat_loop.py` |
| **T04-07-09** | APIキー解決(guildのみ/鍵無し) | `_resolve_api_key` が guild_idありで server_key=None の場合に None を返す | `common/chat/chat_loop.py` |

```bash
python -m tests.common.chat.T04_ChatLoop_07_chat_loop_helpers_test
```

---
[テストユーティリティ](../../README_TEST.md) > M02: common/chatモジュール単体テスト
