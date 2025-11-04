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
| **T03-01** | Auth 解決（opt-in） | resolve empty | `common/chat/auth.py` |
| **T04-01** | ChatCore モック LLM | provider echo | `ui/discord/services/chat_core.py` |
| **T05-01** | ChatLoop MOCK | minimal run / provider echo | `common/chat/chat_loop.py` |
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

### T03-01 : Auth 解決（opt-in）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T03-01-01** | 無認証解決 | 空 dict | `common/chat/auth.py` |

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
| **T04-01-01** | OpenAI echo | モック応答検証 | `ui/discord/services/chat_core.py` |
| **T04-01-02** | Gemini echo | モック応答検証 | `ui/discord/services/chat_core.py` |
| **T04-01-03** | Claude echo | モック応答検証 | `ui/discord/services/chat_core.py` |

```bash
python -m utiltests.T04_ChatCore_01_chat_core_test
```

---

### T05-01 : ChatLoop MOCK

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T05-01-01** | OpenAI echo | MOCK 応答 | `common/chat/chat_loop.py` |
| **T05-01-02** | Anthropic echo | MOCK 応答 | `common/chat/chat_loop.py` |
| **T05-01-03** | Google echo | MOCK 応答 | `common/chat/chat_loop.py` |

```bash
python -m utiltests.T05_ChatLoop_01_chat_loop_test
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
