[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト

# common/secret モジュール単体テスト

本書は **common/secret/store.py** に対する  
単体テストの構成・テストID・検証内容を定義する。

本 README は **tests 側の実装・運用視点** のドキュメントであり、  
仕様上の位置付けは以下を参照する。

- docs/ja-JP/テスト仕様/コア仕様/01_認証・秘密ストア_テスト仕様.md

---

## テスト番号と検証内容（Index）

| Suite | 目的（スコープ） | 機能 | モジュール |
|---|---|---|---|
| **T01-01** | SecretStore 基本 | encrypt / decrypt | `common/secret/store.py` |
| **T01-02** | SecretStore 競合制御 | concurrent LWW | `common/secret/store.py` |
| **T01-03** | SecretStore 復旧 | broken json recovery | `common/secret/store.py` |
| **T01-04** | SecretStore 削除系 | delete robustness | `common/secret/store.py` |
| **T01-05 (impl)** | SecretStore 実装補助 | branch / exception / coverage | `common/secret/store.py` |

---

## テスト詳細

### T01-01 : SecretStore 基本（暗号化）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-01-01** | user key R/W | roundtrip | `common/secret/store.py` |
| **T01-01-02** | server key R/W | roundtrip + has + delete | `common/secret/store.py` |
| **T01-01-03** | LWW（user） | 並列 put → LWW | `common/secret/store.py` |
| **T01-01-04** | LWW（server） | 並列 put → LWW | `common/secret/store.py` |

#### 実行

```bash
python -m tests.common.secret.T01_SecretStore_01_store_test
```

---

### T01-02 : SecretStore 競合・境界条件

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-02-01** | 入力検証 | provider 空 → ValueError | `common/secret/store.py` |
| **T01-02-02** | 入力検証 | provider 空（server） → ValueError | `common/secret/store.py` |
| **T01-02-03** | 空入力 | get_user_key → None | `common/secret/store.py` |
| **T01-02-04** | 空入力 | get_server_key → None | `common/secret/store.py` |
| **T01-02-05** | 存在判定 | has_server_any_key | `common/secret/store.py` |
| **T01-02-06** | 削除安全性 | delete_server_keys 安全 | `common/secret/store.py` |
| **T01-02-07** | 後方互換 | prefix 無しトークン復号 | `common/secret/store.py` |
| **T01-02-08** | JSON 復旧 | 壊れ JSON self-heal | `common/secret/store.py` |
| **T01-02-09** | 全削除 | delete_user_keys | `common/secret/store.py` |

#### 実行

```bash
python -m tests.common.secret.T01_SecretStore_02_store_edge_test
```

---

### T01-03 : SecretStore 初期化・復旧

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-03-01** | 環境変数鍵 | AC_MASTER_KEY 優先 | `common/secret/store.py` |
| **T01-03-02** | 鍵生成 | master.key 生成＋chmod 例外 | `common/secret/store.py` |
| **T01-03-03** | JSON 無 | _load_json → {} | `common/secret/store.py` |
| **T01-03-04** | 破損スキップ | user key | `common/secret/store.py` |
| **T01-03-05** | 破損スキップ | server key | `common/secret/store.py` |
| **T01-03-06** | 未知 provider | get_server_key → None | `common/secret/store.py` |
| **T01-03-07** | 書込失敗 | tmp cleanup | `common/secret/store.py` |

#### 実行

```bash
python -m tests.common.secret.T01_SecretStore_03_store_init_test
```

---

### T01-04 : SecretStore 削除系（仕様）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-04-01** | 部分成功 | user keys 部分復号 | `common/secret/store.py` |
| **T01-04-02** | 未登録 gid | get_server_keys → {} | `common/secret/store.py` |
| **T01-04-03** | 上書き | put_server_key overwrite | `common/secret/store.py` |
| **T01-04-04** | 空削除 | delete_* empty → False | `common/secret/store.py` |

#### 実行

```bash
python -m tests.common.secret.T01_SecretStore_04_store_misc_test
```

---

### T01-05 : SecretStore 実装補助（impl）

> 本スイートは **仕様には含まれない**。  
> 分岐・例外・行カバレッジを目的とする。

#### 内容

- 内部 util 例外経路
- tmp cleanup 分岐
- def 行 / with 行 到達
- reload によるカバレッジ補助

#### 実行

```bash
python -m tests.common.secret.T01_SecretStore_05-impl_store_misc_test
```

---
[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト
