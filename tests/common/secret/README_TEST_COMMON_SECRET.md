[テストユーティリティ](../../README_TEST.md) > M01: common/secretモジュール単体テスト

# M01: ccommon/secretモジュール単体テスト

## テスト番号と検証内容（Index）

| Suite | 目的（スコープ） | 機能 | モジュール |
|---|---|---|---|
| **T01-01** | SecretStore R/W・競合 | R/W / concurrent LWW | `common/secret/store.py` |
| **T01-02** | SecretStore Edge & Recovery | errors / exists / recovery | `common/secret/store.py` |
| **T01-03** | SecretStore Init & Errors | env-key / key-gen / chmod-exc / replace-fail | `common/secret/store.py` |
| **T01-04** | SecretStore Misc Branches   | partial-success / save-ok / dump-error | `common/secret/store.py` |

---

## テスト詳細

### T01-01 : SecretStore 基本 & LWW

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-01-01** | user key R/W | roundtrip | `common/secret/store.py` |
| **T01-01-02** | server key R/W | roundtrip | `common/secret/store.py` |
| **T01-01-03** | LWW（user） | 同時書込 → provider単位 LWW / 破損なし | `common/secret/store.py` |
| **T01-01-04** | LWW（server） | 同時書込 → provider単位 LWW / 破損なし | `common/secret/store.py` |

#### 実行

```bash
python -m tests.common.secret.T01_SecretStore_01_store_test
```

---

### T01-02 : SecretStore Edge & Recovery

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-02-01** | 例外系 | `put_user_key("", None)` → ValueError | `common/secret/store.py` |
| **T01-02-02** | 例外系 | `put_server_key("", None)` → ValueError | `common/secret/store.py` |
| **T01-02-03** | 空入力分岐 | `get_user_key("", None)` → None | `common/secret/store.py` |
| **T01-02-04** | 空入力分岐 | `get_server_key("", None)` → None | `common/secret/store.py` |
| **T01-02-05** | 存在判定 | `has_server_any_key` False→True | `common/secret/store.py` |
| **T01-02-06** | 削除の安全性 | `delete_server_keys` 非存在 gid でも例外なし | `common/secret/store.py` |
| **T01-02-07** | 後方互換 | `'fernet:'` 無しトークンでも復号可 | `common/secret/store.py` |
| **T01-02-08** | 壊れ JSON 復旧 | `_load_json` の self-heal（空で上書き） | `common/secret/store.py` |
| **T01-02-09** | ユーザー削除 | `delete_user_keys` で providers 空化 | `common/secret/store.py` |

#### 実行
```bash
python -m tests.common.secret.T01_SecretStore_02_store_edge_test
```

---

### T01-03 : SecretStore Init & Errors

#### ケース
| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-03-01** | 環境変数鍵 | `AC_MASTER_KEY` 優先（master.key 不生成） | `common/secret/store.py` |
| **T01-03-02** | 鍵生成＋権限例外 | `master.key` 自動生成 / `os.chmod` 例外経路 | `common/secret/store.py` |
| **T01-03-03** | JSON 無 | `_load_json`：パス未作成 → `{}` | `common/secret/store.py` |
| **T01-03-04** | 破損スキップ（user） | 復号不可は `get_user_key=None` / `get_user_keys` から除外 | `common/secret/store.py` |
| **T01-03-05** | 破損スキップ（server） | `get_server_keys` で正常分のみ残る | `common/secret/store.py` |
| **T01-03-06** | 未知プロバイダ | `get_server_key` 未登録 provider → `None` | `common/secret/store.py` |
| **T01-03-07** | 書込み失敗後始末 | `_save_json`：`os.replace` 失敗→`finally` で tmp 削除 | `common/secret/store.py` |

#### 実行
```bash
python -m tests.common.secret.T01_SecretStore_03_store_init_test
```

---

### T01-04 : SecretStore Misc Branches

#### ケース
| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-04-01** | user keys 部分成功 | openai=OK / claude=破損 → {"openai":b"OK"} | `common/secret/store.py` |
| **T01-04-02** | server keys 未登録 | gid 不在 → {} | `common/secret/store.py` |
| **T01-04-03** | save 正常系 | _save_json 正常、tmp 残らず | `common/secret/store.py` |
| **T01-04-04** | save 失敗系 | json.dump TypeError → 例外＋tmp 後始末 | `common/secret/store.py` |
| **T01-04-05** | user key enc 無 | get_user_key: enc 不在 → None（line 109） | `common/secret/store.py` |
| **T01-04-06** | user keys 削除 | delete_user_keys true 分岐（132-134） | `common/secret/store.py` |
| **T01-04-07** | JSON 無 | _load_json: パス無 → {}（line 204） | `common/secret/store.py` |
| **T01-04-08** | 空トークン | _dec("") → ValueError を get_user_key が握り潰す（193） | `common/secret/store.py` |
| **T01-04-09** | 復旧失敗 | 壊れ JSON ＋ save 失敗 → (213-214) pass | `common/secret/store.py` |
| **T01-04-10** | 後始末失敗 | _save_json finally で remove 失敗 → (236-237) pass | `common/secret/store.py` |
| **T01-04-11** | 直接復号例外 | `_dec("")` を直接呼び出し、例外分岐（ValueError）を明示的に踏む | `common/secret/store.py` |
| **T01-04-12** | 削除の両枝 | `delete_user_keys` の false→true 両パス（未存在→存在時）を網羅 | `common/secret/store.py` |

#### 実行
```bash
python -m tests.common.secret.T01_SecretStore_04_store_misc_test
```

---
[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト
