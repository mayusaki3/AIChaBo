# テストユーティリティ

Discord を介さずに **コア機能の健全性** を確認するためのテスト群です。  
CI 実行を想定し、書き込みを伴うテストは **既定で skip / dry-run** です。  
  
開発テスト用に以下のインストール作業を行ってください。
```shell
pip install -r requirements-dev.txt
```
各テストは「python -m utiltests.*」で実行しますが、以下の形式で実行すると、テストのカバー率が確認できます。
```shell
# テスト実行（通常実行）
python -m utiltests.T01_Provider_01_provider_test

# テスト実行（カバー率確認：単一）
coverage run -m utiltests.T01_Provider_01_provider_test

# テスト実行（カバー率確認：全体）
coverage run -m unittest discover -s utiltests -p "*_test.py"

# テスト実行（カバー率確認：全体・結果を累積）
coverage erase
coverage run -a -m utiltests.T01_Provider_01_provider_test
coverage run -a -m utiltests.T02_SecretStore_01_store_test
#    :             以下、残りのテストを実施

# カバー率レポート表示
coverage report -m
# カバー率レポート詳細表示（ブラウザ表示）
coverage html
htmlcov/index.html
```

## テスト番号と検証内容（Index）

> すべてのテストは共通レポータにより  
> `✅/❌[Txx-yy-zz] <タイトル>`  
> `--- SUMMARY Txx-yy: ✅=N / ❌=M / TOTAL=K ---`  
> を出力します。  
> unittest は **メソッド名の昇順**（`test_01_*` → `test_02_*` …）で実行します。

| Suite | 目的（スコープ） | 機能 | モジュール |
|---|---|---|---|
| **T01-01** | Provider 正規化 | alias normalize / display | `common/chat/provider.py` |
| **T02-01** | SecretStore R/W・競合 | R/W / concurrent LWW | `common/secret/store.py` |
| **T02-02** | SecretStore Edge & Recovery | errors / exists / recovery | `common/secret/store.py` |
| **T02-03** | SecretStore Init & Errors | env-key / key-gen / chmod-exc / replace-fail | `common/secret/store.py` |
| **T02-04** | SecretStore Misc Branches   | partial-success / save-ok / dump-error | `common/secret/store.py` |
| **T03-01** | Auth 解決（opt-in） | resolve empty | `common/chat/auth.py` |
| **T04-01** | ChatCore モック LLM | provider echo | `ui/discord/services/chat_core.py` |
| **T05-01** | ChatLoop MOCK | minimal run / provider echo | `common/chat/chat_loop.py` |
| **T05-02** | ChatLoop Edges | 明示model優先 / policy追加パラメータ透過 / 例外ハンドリング（provider例外→既定メッセージ） | `common/chat/chat_loop.py` |
| **T05-03** | ChatLoop More Edges | APIキー未設定 / 全メッセージ空白化 / policy=None→既定メッセージ / プロバイダ空文字返却 / プロバイダ関数None→既定メッセージ | `common/chat/chat_loop.py` |
| **T05-04** | ChatLoop Cover Rest | provider前後空白・大文字許容 / policy={}＋明示model / プロバイダがNone返却→既定メッセージ | `common/chat/chat_loop.py` |
| **T05-05** | ChatLoop Helper Paths | セッション由来policy→APIキー解決→provider関数呼出の配線を通す（明示model有無パス／extra透過） | `common/chat/chat_loop.py` |
| **T06-01** | Message 最小経路 | run_once_for_test | `common/chat/message.py` |
| **T07-01** | Context（SKIP） | future ctx build | `message.build_context()` |

---

### ルール

- unittest 標準要約は非表示 → **共通レポータのみ**
- 実行順は **メソッド名順**
- **破壊的テストは opt-in**
  - `.envtest` → REAL モード
  - `AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1` → Auth テスト有効化

---

### auth_seed.py

USM / SSM / SecretStore に**テスト用認証情報**を流し込むユーティリティ。  
既定 DRY-RUN。**`--confirm`** で書込み。

> 本番運用では `/ac_` コマンドを使用

---

## テスト詳細

### T01-01 : Provider 正規化

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-01-01** | エイリアス正規化 | known → canonical 変換 | `common/chat/provider.py` |
| **T01-01-02** | 未知入力処理 | unknown → lower-case | `common/chat/provider.py` |
| **T01-01-03** | 表示統一 | display label の一致 | `common/chat/provider.py` |
| **T01-01-04** | 空入力防御 | `display_provider("")` / `display_provider(None)` が空文字を返す | `common/chat/provider.py` |

#### 実行

```bash
python -m utiltests.T01_Provider_01_provider_test
```

---

### T02-01 : SecretStore 基本 & LWW

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-01-01** | user key R/W | roundtrip | `common/secret/store.py` |
| **T02-01-02** | server key R/W | roundtrip | `common/secret/store.py` |
| **T02-01-03** | LWW（user） | 同時書込 → provider単位 LWW / 破損なし | `common/secret/store.py` |
| **T02-01-04** | LWW（server） | 同時書込 → provider単位 LWW / 破損なし | `common/secret/store.py` |

#### 実行

```bash
python -m utiltests.T02_SecretStore_01_store_test
```

---

### T02-02 : SecretStore Edge & Recovery

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-02-01** | 例外系 | `put_user_key("", None)` → ValueError | `common/secret/store.py` |
| **T02-02-02** | 例外系 | `put_server_key("", None)` → ValueError | `common/secret/store.py` |
| **T02-02-03** | 空入力分岐 | `get_user_key("", None)` → None | `common/secret/store.py` |
| **T02-02-04** | 空入力分岐 | `get_server_key("", None)` → None | `common/secret/store.py` |
| **T02-02-05** | 存在判定 | `has_server_any_key` False→True | `common/secret/store.py` |
| **T02-02-06** | 削除の安全性 | `delete_server_keys` 非存在 gid でも例外なし | `common/secret/store.py` |
| **T02-02-07** | 後方互換 | `'fernet:'` 無しトークンでも復号可 | `common/secret/store.py` |
| **T02-02-08** | 壊れ JSON 復旧 | `_load_json` の self-heal（空で上書き） | `common/secret/store.py` |
| **T02-02-09** | ユーザー削除 | `delete_user_keys` で providers 空化 | `common/secret/store.py` |

#### 実行
```bash
python -m utiltests.T02_SecretStore_02_store_edge_test
```

---

### T02-03 : SecretStore Init & Errors

#### ケース
| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-03-01** | 環境変数鍵 | `AC_MASTER_KEY` 優先（master.key 不生成） | `common/secret/store.py` |
| **T02-03-02** | 鍵生成＋権限例外 | `master.key` 自動生成 / `os.chmod` 例外経路 | `common/secret/store.py` |
| **T02-03-03** | JSON 無 | `_load_json`：パス未作成 → `{}` | `common/secret/store.py` |
| **T02-03-04** | 破損スキップ（user） | 復号不可は `get_user_key=None` / `get_user_keys` から除外 | `common/secret/store.py` |
| **T02-03-05** | 破損スキップ（server） | `get_server_keys` で正常分のみ残る | `common/secret/store.py` |
| **T02-03-06** | 未知プロバイダ | `get_server_key` 未登録 provider → `None` | `common/secret/store.py` |
| **T02-03-07** | 書込み失敗後始末 | `_save_json`：`os.replace` 失敗→`finally` で tmp 削除 | `common/secret/store.py` |

#### 実行
```bash
python -m utiltests.T02_SecretStore_03_store_init_test
```

---

### T02-04 : SecretStore Misc Branches

#### ケース
| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-04-01** | user keys 部分成功 | openai=OK / claude=破損 → {"openai":b"OK"} | `common/secret/store.py` |
| **T02-04-02** | server keys 未登録 | gid 不在 → {} | `common/secret/store.py` |
| **T02-04-03** | save 正常系 | _save_json 正常、tmp 残らず | `common/secret/store.py` |
| **T02-04-04** | save 失敗系 | json.dump TypeError → 例外＋tmp 後始末 | `common/secret/store.py` |
| **T02-04-05** | user key enc 無 | get_user_key: enc 不在 → None（line 109） | `common/secret/store.py` |
| **T02-04-06** | user keys 削除 | delete_user_keys true 分岐（132-134） | `common/secret/store.py` |
| **T02-04-07** | JSON 無 | _load_json: パス無 → {}（line 204） | `common/secret/store.py` |
| **T02-04-08** | 空トークン | _dec("") → ValueError を get_user_key が握り潰す（193） | `common/secret/store.py` |
| **T02-04-09** | 復旧失敗 | 壊れ JSON ＋ save 失敗 → (213-214) pass | `common/secret/store.py` |
| **T02-04-10** | 後始末失敗 | _save_json finally で remove 失敗 → (236-237) pass | `common/secret/store.py` |
| **T02-04-11** | 直接復号例外 | `_dec("")` を直接呼び出し、例外分岐（ValueError）を明示的に踏む | `common/secret/store.py` |
| **T02-04-12** | 削除の両枝 | `delete_user_keys` の false→true 両パス（未存在→存在時）を網羅 | `common/secret/store.py` |

#### 実行
```bash
python -m utiltests.T02_SecretStore_04_store_misc_test
```

---

### T03-01 : Auth 解決（opt-in）

> 実行前に `AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1` を設定してください（安全のため既定は SKIP ）。

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T03-01-01** | 無認証解決 | USM/SSM 空、keys 無 → `{}` | `common/chat/auth.py` |
| **T03-01-02** | USMのみ非機密 | USMに provider/model、keys 無 → `{}` | `common/chat/auth.py` |
| **T03-01-03** | ユーザー鍵優先 | USM( provider/model ) + user_key → 解決（`max_tokens` 既定付与） | `common/chat/auth.py` |
| **T03-01-04** | サーバ鍵フォールバック | user_key 無、server_keys に `openai` → 解決 | `common/chat/auth.py` |
| **T03-01-05** | provider正規化 | USM provider が `OPENAI` でも normalize → `openai` キーに一致 | `common/chat/auth.py` |
| **T03-01-06** | model欠落 | providerのみ → `{}` | `common/chat/auth.py` |
| **T03-01-07** | SSM優先（USM無） | USM 無・SSM に provider/model、server_keys で解決 | `common/chat/auth.py` |

#### 実行

```bash
# bash/zsh
export AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
python -m utiltests.T03_Auth_01_auth_resolve_test
unset AIChaBo_TEST_ENABLE_AUTH_RESOLVE

# PowerShell
$env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
python -m utiltests.T03_Auth_01_auth_resolve_test
Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE
```

---

### T04-01 : ChatCore モック LLM

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-01-01** | 入力ガード | text="   " を例外またはガードで弾く | `common/chat/chat_core.py` |
| **T04-01-02** | 必須項目 | context.chat.provider / context.chat.model 欠落で ValueError | `common/chat/chat_core.py` |
| **T04-01-03** | 最小往復 | chat_fn 未指定なら echo、chat_fn 指定時は委譲 | `common/chat/chat_core.py` |
| **T04-01-04** | 入力ガード（型） | text=None で ValueError（非文字列分岐の到達） | `common/chat/chat_core.py` |
| **T04-01-05** | echo 分岐 | chat_fn 無し → trim 後にそのまま返す | `common/chat/chat_core.py` |
| **T04-01-06** | chat_fn 注入 | `send_once(..., chat_fn=...)` で注入関数が呼ばれ、`provider/model/text` が正しく引数で渡ることを検証 | `common/chat/chat_core.py` |

```bash
python -m utiltests.T04_ChatCore_01_chat_core_test
```

---

### T05-01 : ChatLoop 基本

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T05-01-01** | 空入力の固定化 | context_list=["   "] → （入力が空です）を返す | `common/chat/chat_loop.py` |
| **T05-01-02** | model 未解決ガイド | model=None かつ policy={} → （モデル設定が見つかりません…）を返す | `common/chat/chat_loop.py` |
| **T05-01-03** | 正常系（依存スタブ） | policy で model 補完、_resolve_api_key を "KEY" にパッチ、_get_provider_chat_fn をモックして "pong" を返す | `common/chat/chat_loop.py` |
| **T05-01-04** | provider ガード | provider="   " → （プロバイダが不正です）を返す | `common/chat/chat_loop.py` |

```bash
python -m utiltests.T05_ChatLoop_01_chat_loop_test
```

---

### T05-02 : ChatLoop Edges

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T05-02-01** | 明示 model の優先 | policy の model より引数 model を優先（fake_call に渡る model を検証） | `common/chat/chat_loop.py` |
| **T05-02-02** | 追加パラメータ透過 | policy の temperature/top_p などがプロバイダ関数に **extra** として渡る | `common/chat/chat_loop.py` |
| **T05-02-03** | 例外ハンドリング | プロバイダ関数が例外を投げたら `"（チャット実行でエラーが発生しました）"` を返す | `common/chat/chat_loop.py` |

```bash
python -m utiltests.T05_ChatLoop_02_chat_loop_edges_test
```

---

### T05-03 : ChatLoop More Edges

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T05-03-01** | APIキー未設定 | `_resolve_api_key` が None/空 → 既定メッセージ | `common/chat/chat_loop.py` |
| **T05-03-02** | 全メッセージ空白化 | `context_list=["  ","\t"," \n "]` → 空入力メッセージ | `common/chat/chat_loop.py` |
| **T05-03-03** | policy=None | policy=None は現行実装上エラー → 既定メッセージ応答 | `common/chat/chat_loop.py` |
| **T05-03-04** | 空文字返却 | provider 関数が `""` を返す枝（戻り値型の許容確認） | `common/chat/chat_loop.py` |
| **T05-03-05** | 関数取得失敗 | `_get_provider_chat_fn` が `None` → 例外ハンドリング文言 | `common/chat/chat_loop.py` |

```bash
python -m utiltests.T05_ChatLoop_03_chat_loop_more_edges_test
```

---

### T05-04 : ChatLoop Cover Rest

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T05-04-01** | provider 前処理 | `provider="  OPENAI  "` を許容（前後空白/大文字） | `common/chat/chat_loop.py` |
| **T05-04-02** | policy 空辞書 | `policy={}` かつ `model="explicit"` で正常完了 | `common/chat/chat_loop.py` |
| **T05-04-03** | ChatLoop cover rest | provider returns None → `"None"`（stringify 挙動を検証） | `common/chat/chat_loop.py` |

```bash
python -m utiltests.T05_ChatLoop_04_chat_loop_cover_rest_test
```

---

### T05-05 : ChatLoop Helper Paths

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T05-05-01** | policy→key→provider 呼出 | policy(model)採用・_resolve_api_key・_get_provider_chat_fn を通る／extra受渡 | `common/chat/chat_loop.py` |
| **T05-05-02** | 明示model優先＋extra透過 | 明示 model が policy を上書き／extra(top_p等) が provider関数へ渡る | `common/chat/chat_loop.py` |


```bash
python -m utiltests.T05_ChatLoop_05_chat_loop_helper_paths_test
```

---

### T06-01 : Message 最小経路

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T06-01-01** | 最小実行パス | run_once_for_test 経路通過 | `common/chat/message.py` |

```bash
python -m utiltests.T06_Message_01_message_test
```

---

### T07-01 : Context（SKIP）

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T07-01-01** | 将来拡張 | skeleton（SKIP） | `message.build_context()` |

```bash
python -m utiltests.T07_Context_01_context_test
```

---

## 備考

このテストセットにより、  
**Discord 非依存**の範囲を先にテストできます（高速／安全／CI 向き）。
