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
| **T05-01** | Message Utility | メッセージ正規化・role補完・結合ユーティリティ（正常／異常／境界値） | `common/chat/message.py` |
| **T06-01** | TextSplit Utility | 長文分割処理（最大長・文単位・多言語・特殊ケース） | `common/chat/textsplit.py` |
| **T06-02** | TextSplit Utility (Edges) | 境界・例外・多改行・英文 ". " 境界・非 int 許容などの端部挙動を網羅       | `common/chat/textsplit.py`          |
| **T06-03** | TextSplit Utility (More Cases) | 文区切り混在・Unicode/絵文字・改行保持の厳密性・決定性・優先順位・型境界の補完 | `common/chat/textsplit.py` |
| **T06-04** | TextSplit Arg/Compat | 互換レイヤ（self バインド/省略/既定値）と JA append 分岐の網羅 | `common/chat/textsplit.py` |
| **T07-01** | Continuation Flow | 会話継続（履歴＋入力→応答生成）・textsplit連携・例外処理・分岐網羅 | `common/chat/continuation.py` |
| **T07-02** | Continuation (Edges)      | `max_steps=0`/空チャンク/例外時フォールバック/非文字列応答/辞書入力を網羅 | `common/chat/continuation.py`       |
| **T07-03** | 継続チャット内部ガード | policy 正規化 / 分割結果の変則型 / 補助関数のガード経路 | `common/chat/continuation.py` |
| **T07-04** | 継続チャット内部ガード2  | 末尾テキスト抽出の例外ガード / `split_text` 戻り値のフォールバック（str・未知型・空文字）/ `continue_chat` の `str()` 例外と応答空ガード | `common/chat/continuation.py`       |
| **T07-05** | 継続チャット詳細ガード | 末尾テキスト抽出とステップ用メッセージ構築のガード（想定外型・空リスト・split_text 空文字列結果） | `common/chat/continuation.py` |
| **T07-06** | 継続チャット top-level ガード | `tail_text` 空時と `_split_into_chunks` が `None` を返す場合の早期リターン／`chat_fn` 未呼び出しを確認 | `common/chat/continuation.py` |
| **T08-01** | Sharing Session | セッション共有（export/import/guild共有/互換）・冪等性・サニタイズ | `common/chat/sharing.py` |
| **T08-02** | Sharing Migration | 旧フォーマットから現行セッション形式への移行（version/フィールド補完・安全なフォールバック） | `common/chat/sharing.py` |

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

### T05-01 : Message Utility

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T05-01-01** | 文字列の正規化 | `"hello"` → `[{'role':'user','content':'hello'}]` | `common/chat/message.py` |
| **T05-01-02** | 既存配列の透過 | 既に `[{role,content}]` 配列は構造維持で返却 | `common/chat/message.py` |
| **T05-01-03** | 不正型ガード | `None` / 数値 / dict を渡すと `ValueError` | `common/chat/message.py` |
| **T05-01-04** | 空文字の扱い | `""` は空要素として許容または明示エラー（実装に追従） | `common/chat/message.py` |
| **T05-01-05** | role 既定値 | role 未指定要素に `'user'` を補完 | `common/chat/message.py` |
| **T05-01-06** | トリム規則 | content 前後空白の扱い（保持/除去は実装に追従） | `common/chat/message.py` |
| **T05-01-07** | 結合ユーティリティ | 複数要素の結合（区切り文字・改行含む） | `common/chat/message.py` |
| **T05-01-08** | 破損要素スキップ | 欠落 `content` 要素をスキップ | `common/chat/message.py` |
| **T05-01-09** | dict入力（正常） | `{"role":"assistant","content":"hi"}` を 1件のメッセージに正規化 | `common/chat/message.py` |
| **T05-01-10** | dict入力（content欠落） | `content` を持たない dict 入力はメッセージ化せず空リストとする | `common/chat/message.py` |
| **T05-01-11** | 全要素不正配列の扱い | すべて不正要素の配列入力は全スキップし空リストを返す | `common/chat/message.py` |
| **T05-01-12** | role補完ユーティリティ | `ensure_role` で非dict要素を無視し、dict要素に `default_role` を補完 | `common/chat/message.py` |
| **T05-01-13** | 結合ユーティリティ（スキップ条件） | `join_messages` で非dict・欠落`content`・非文字列・空文字をスキップして結合 | `common/chat/message.py` |
| **T05-01-14** | 結合ユーティリティ（空入力） | `None` / 空配列入力時は空文字を返す | `common/chat/message.py` |
| **T05-01-15** | 結合ユーティリティ（文字列透過） | 文字列入力時はそのまま返す（後方互換） | `common/chat/message.py` |
| **T05-01-16** | 結合ユーティリティ（非イテラブルガード） | 非イテラブル入力時に例外を出さず空文字を返す | `common/chat/message.py` |

```bash
python -m tests.common.chat.T05_Message_01_message_test
```

---
### T06-01 : TextSplit Utility

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T06-01-01** | 基本分割 | `max_chars=50` で適切にチャンク化 | `common/chat/textsplit.py` |
| **T06-01-02** | 文単位分割（和文） | `split_sentences=True` で「。！？…」区切り | `common/chat/textsplit.py` |
| **T06-01-03** | 文単位分割（英文） | `split_sentences=True` で「.!?」区切り | `common/chat/textsplit.py` |
| **T06-01-04** | 改行混在 | 改行・空行を保ったまま分割（実装に追従） | `common/chat/textsplit.py` |
| **T06-01-05** | 超長単語 | `max_chars` 未満に収まらない単語を分割 | `common/chat/textsplit.py` |
| **T06-01-06** | 空文字 | `""` → `[""]` または `[]`（実装に追従） | `common/chat/textsplit.py` |
| **T06-01-07** | 無効パラメータ | `max_chars<=0` 等で `ValueError` | `common/chat/textsplit.py` |
| **T06-01-08** | 末尾境界 | 末尾が区切り文字で終わるケースの扱い | `common/chat/textsplit.py` |

```bash
python -m tests.common.chat.T06_TextSplit_01_textsplit_test
```

---
### T06-02 : TextSplit Utility (Edges)

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T06-02-01** | 最小分割                 | `max_chars=1` で 1 文字ずつ分割                                           | `common/chat/textsplit.py` |
| **T06-02-02** | 英文文末（". "）         | 区切り記号後の空白を**保持**して分割（実装準拠）                         | `common/chat/textsplit.py` |
| **T06-02-03** | CRLF 混在                | `\r\n` を含むテキストの長さ制約分割                                      | `common/chat/textsplit.py` |
| **T06-02-04** | ジャスト境界             | `len(text) == max_chars` の等号境界                                      | `common/chat/textsplit.py` |
| **T06-02-05** | 不正長（<=0）            | `max_chars <= 0` で `ValueError`                                         | `common/chat/textsplit.py` |
| **T06-02-06** | 非 int 許容              | 文字列数値などを **int キャスト許容**（正常分割）                         | `common/chat/textsplit.py` |
| **T06-02-07** | 超長単語ハード分割       | 空白なし長語を `max_chars` ごとに強制分割                                | `common/chat/textsplit.py` |

```bash
python -m tests.common.chat.T06_TextSplit_02_textsplit_edges_test
```

---
### T06-03 : TextSplit Utility (More Cases)

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T06-03-01** | 英文 空白保持（複合文） | `. ` を含む複合文で空白扱いが実装準拠であることを再確認 | `common/chat/textsplit.py` |
| **T06-03-02** | CJK 文区切り複合 | `。！？…` 混在で文数が期待以上になる | `common/chat/textsplit.py` |
| **T06-03-03** | Unicode/絵文字 長さ制御 | サロゲート/結合文字でも `max_chars` を超えない | `common/chat/textsplit.py` |
| **T06-03-04** | 改行保持 厳密一致 | `\r\n`/`\n` 混在で `"".join(out) == text` を満たす | `common/chat/textsplit.py` |
| **T06-03-05** | 文区切り優先 vs ハード分割 | `max_chars` 付近の文末記号で優先順位が現実装どおり | `common/chat/textsplit.py` |
| **T06-03-06** | 決定性 | 同一入力・同一パラメータで出力が完全一致 | `common/chat/textsplit.py` |
| **T06-03-07** | `max_chars` キャスト/境界 | `"50"` は許容、`"0"`/`"abc"` は例外（現実装） | `common/chat/textsplit.py` |

```bash
python -m tests.common.chat.T06_TextSplit_03_textsplit_more_cases_test
```

---
### T06-04 : TextSplit Arg/Compat

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T06-04-01** | 互換レイヤ: 例外 | 引数なし → `TypeError`（`_parse_args` 先頭分岐） | `common/chat/textsplit.py` |
| **T06-04-02** | 互換レイヤ: 型誤り | `self` 相当 + 第2引数も非文字列 → `TypeError` | `common/chat/textsplit.py` |
| **T06-04-03** | 互換レイヤ: 既定値 | `max_chars` 省略 → 既定 `2000` が効く（保存モード） | `common/chat/textsplit.py` |
| **T06-04-04** | 互換レイヤ: 位置引数 | 第3引数で `split_sentences=True` 指定の経路 | `common/chat/textsplit.py` |
| **T06-04-05** | JA append 分岐 | JA 文末到達時の `if s: out.append(s)` 行の到達 | `common/chat/textsplit.py` |
| **T06-04-06** | EN 文末（無句点）flush 分岐 | 末尾に句点が無い英文で flush 側の分岐に到達することを確認 | `common/chat/textsplit.py` |
| **T06-04-07** | 空文字 + 文分割モード（互換経路） | 文分割モードで空文字入力時の互換経路が安定して空出力になることを確認 | `common/chat/textsplit.py` |
| **T06-04-08** | EN 文末: 末尾が空白のみ → append スキップ | 末尾が空白だけの場合に残バッファを append しない（スキップ枝）ことを確認 | `common/chat/textsplit.py` |
| **T06-04-09** | EN 文末: 改行/空白のみ入力 → append スキップ | 入力が改行/空白のみの場合に残バッファを append しない（スキップ枝）ことを確認 | `common/chat/textsplit.py` |
| **T06-04-10** | JA 文末: 直前が空白のみ → 空チャンクは append されない（ガード枝） | JA 文末直前が空白のみのケースで空チャンクが append されないこと（`if s:` ガード枝）を確認 | `common/chat/textsplit.py` |

```bash
python -m tests.common.chat.T06_TextSplit_04_textsplit_arg_compat_test
```

---
### T07-01 : Continuation Flow

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T07-01-01** | 空コンテキスト | 履歴・入力いずれも空 → 既定応答（実装に追従） | `common/chat/continuation.py` |
| **T07-01-02** | 正常継続 | 履歴＋新規入力からプロンプト合成→モック応答 | `common/chat/continuation.py` |
| **T07-01-03** | 例外握り潰し | provider 例外をログ＋固定メッセージ | `common/chat/continuation.py` |
| **T07-01-04** | 長文継続 | 新規入力が長文→`textsplit` 経由で複数回呼び出し | `common/chat/continuation.py` |
| **T07-01-05** | policy 直呼び | `policy.chat_fn` 指定時に provider マップをバイパス | `common/chat/continuation.py` |
| **T07-01-06** | メッセージ正規化 | `message.py` 正規化が呼ばれることを確認 | `common/chat/continuation.py` |
| **T07-01-07** | ステップ上限 | `max_steps` 超過時の打ち切り | `common/chat/continuation.py` |
| **T07-01-08** | None 応答 | provider が `None` を返す→ `str(None)` or 既定値 | `common/chat/continuation.py` |

```bash
python -m tests.common.chat.T07_Continuation_01_continuation_test
```

---
### T07-02 : Continuation (Edges)

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T07-02-01** | ステップ下限（0）             | `max_steps=0` でも **最低1回は chat 実行**（実装準拠）                                      | `common/chat/continuation.py` |
| **T07-02-02** | 空チャンク時の挙動           | `textsplit` が `[]` を返しても **元メッセージで1回投げる**                                  | `common/chat/continuation.py` |
| **T07-02-03** | 分割例外時フォールバック     | `textsplit` 例外でも **フォールバックで1回投げる**                                          | `common/chat/continuation.py` |
| **T07-02-04** | 非文字列応答の正規化         | provider 応答が非文字列でも `str()` 化される                                                | `common/chat/continuation.py` |
| **T07-02-05** | dict 入力の正規化            | 単一 dict 入力が `message.normalize_messages` 経由で正規化される                            | `common/chat/continuation.py` |

```bash
python -m tests.common.chat.T07_Continuation_02_continuation_edges_test
```

---
### T07-03: 継続チャット内部ガード

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **M02:T07-03-01** | policy 正規化 | `policy` が `None` または dict 以外の値でも `_resolve_policy` により空 dict に正規化されることを確認 | `common/chat/continuation.py` |
| **M02:T07-03-02** | 非 list メッセージのガード | `messages` が list 以外の場合、`_extract_tail_text` が空文字列を返し安全に終了することを確認 | `common/chat/continuation.py` |
| **M02:T07-03-03** | 分割結果の変則型対応 | `textsplit.split_text` の戻り値が dict / list / 想定外型の各パターンで `_split_into_chunks` が空文字・非文字列をスキップしつつ安全にチャンク化することを確認 | `common/chat/continuation.py` |
| **M02:T07-03-04** | ステップメッセージ構築ガード | `_prepare_step_messages` において、`base_messages` が非 list / 空 list / 末尾要素が dict・str 以外の場合でも、チャンクを含むメッセージ列を安全に構築できることを確認 | `common/chat/continuation.py` |
| **M02:T07-03-05** | max_steps / 返信文字列化エラーガード | `continue_chat` で `max_steps` が数値変換不能な値でも例外にならず、またチャット関数の返り値の `__str__` が例外を投げても落ちずに結果から除外されることを確認 | `common/chat/continuation.py` |

```bash
python -m tests.common.chat.T07_Continuation_03_continuation_guards_test
```

---
### T07-04: 継続チャット内部ガード（フォールバック完全網羅）

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T07-04-01** | 末尾テキスト抽出の例外ガード | list サブクラスで `__getitem__` 例外を発生させ、`_extract_tail_text` の `except` 経路を確認 | `common/chat/continuation.py` |
| **T07-04-02** | `split_text` が文字列を返す場合 | `textsplit.split_text` が `str` を返すケースで、`_split_into_chunks` がその文字列を 1 チャンクとして扱うことを確認 | `common/chat/continuation.py` |
| **T07-04-03** | `split_text` が未知型を返す場合 | `split_text` が dict/list/tuple/str 以外を返したとき、元テキスト全体を 1 チャンクとして扱うフォールバック枝を確認 | `common/chat/continuation.py` |
| **T07-04-04** | 空テキスト分割ガード | `text=""` 入力時に `_split_into_chunks` が即座に空リストを返すガードを確認 | `common/chat/continuation.py` |
| **T07-04-05** | `continue_chat` 応答空・str() 例外ガード | `max_steps` キャスト失敗 + `reply.__str__` 例外発生時でも落ちず、`responses` が空のまま `""` を返す経路を確認 | `common/chat/continuation.py` |
| T07-04-06 | dict `"chunks"` 非 list/tuple ガード | `_split_into_chunks` が `{"chunks": <非 list/tuple>}` を受け取った場合に空リストへフォールバックする経路 | `common/chat/continuation.py` |

```bash
python -m tests.common.chat.T07_Continuation_04_continuation_guards2_test
```

---
### T07-05: 継続チャット詳細ガード

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T07-05-01** | 末尾テキスト抽出 | 末尾が str → そのまま返す | `common/chat/continuation.py` |
| **T07-05-02** | 末尾テキスト抽出 | 末尾が dict/str 以外 → 空文字を返す | `common/chat/continuation.py` |
| **T07-05-03** | step メッセージ構築 | 末尾が想定外型 → chunk を append | `common/chat/continuation.py` |
| **T07-05-04** | step メッセージ構築 | base が list 以外 → `[chunk]` のみ返す | `common/chat/continuation.py` |
| **T07-05-05** | step メッセージ構築 | base が空 list → `[chunk]` のみ返す | `common/chat/continuation.py` |
| **T07-05-06** | split_text 結果の dict-chunks ガード | dict だが `"chunks"` が list/tuple 以外 → `[]` を返す | `common/chat/continuation.py` |

```bash
python -m tests.common.chat.T07_Continuation_05_continuation_tail_and_prepare_test
```

---
### T07-06: 継続チャット top-level ガード

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T07-06-01** | tail_text 空時の早期リターン | `_extract_tail_text` の結果（`tail_text`）が空文字列の場合に、`continue_chat` が即座に `""` を返し `chat_fn` が一度も呼ばれないことを確認 | `common/chat/continuation.py` |
| **T07-06-02** | 分割失敗時のフォールバック抑止 | `_split_into_chunks` が `None` を返すケース（内部で `textsplit.split_text` が例外を投げた想定）で、`continue_chat` が `""` を返し `chat_fn` を呼ばないことを確認 | `common/chat/continuation.py` |
| **T07-06-03** | 非文字列応答の正常結合 | `chat_fn` が `str` 以外のオブジェクトを返しても `str()` 正常経路で `responses` に追加され、結合結果として返されることを確認 | `common/chat/continuation.py` |

```bash
python -m tests.common.chat.T07_Continuation_06_continuation_top_level_guards_test
```

---
### T08-01 : Sharing Session

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T08-01-01** | export 基本 | user セッションを JSON(dict) 化、必須キー確認 | `common/chat/sharing.py` |
| **T08-01-02** | import 基本 | JSON からセッション再構築（id/ts/messages 等） | `common/chat/sharing.py` |
| **T08-01-03** | guild 共有 | user→guild への共有登録（上書き・追記を含む） | `common/chat/sharing.py` |
| **T08-01-04** | 不正 JSON | 欠落/型不整合→安全に失敗（例外抑止 or None） | `common/chat/sharing.py` |
| **T08-01-05** | 冪等性 | 同一 JSON の再 import は差分なし | `common/chat/sharing.py` |
| **T08-01-06** | サニタイズ | 余剰フィールドは無視／既知のみ採用 | `common/chat/sharing.py` |
| **T08-01-07** | バージョン互換 | schema version 不一致時の扱い（互換/拒否） | `common/chat/sharing.py` |
| **T08-01-08** | 部分共有 | 特定会話のみ共有対象に含める | `common/chat/sharing.py` |

```bash
python -m tests.common.chat.T08_Sharing_01_sharing_test
```

---
### T08-02 : Sharing Migration

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T08-02-01** | 旧形式 dict 入力のマイグレーション | `version` 無し + `history` キーを持つ dict を `import_session` が受け取り、`messages` への変換・最小限のフィールド補完を行う | `common/chat/sharing.py` |
| **T08-02-02** | 旧形式 JSON(v0) のマイグレーション | `{"version":0,"provider":...,"model":...,"history":[...]}` のような JSON 文字列から、`version>=1` かつ `messages` 付きのセッション dict を構築できることを確認 | `common/chat/sharing.py` |
| **T08-02-03** | 余剰フィールド付き旧形式のサニタイズ | 旧形式に `unknown`/`token_count` 等の余剰キーが混在していても、migration + sanitize 後のセッション dict からは除外されることを確認 | `common/chat/sharing.py` |
| **T08-02-04** | version 型不整合のフォールバック | `version` が文字列や負数など不正な場合でも例外とならず、`version>=1` の数値に補正される or version 未指定として扱われることを確認 | `common/chat/sharing.py` |
| **T08-02-05** | dict 直接入力の互換性 | すでに `messages` を持つ dict（version 無し）を `import_session` に直接渡した場合でも、安全に現行セッション dict に正規化されることを確認 | `common/chat/sharing.py` |

```bash
python -m tests.common.chat.T08_Sharing_02_migration_test
```

---
[テストユーティリティ](../../README_TEST.md) > M02: common/chatモジュール単体テスト
