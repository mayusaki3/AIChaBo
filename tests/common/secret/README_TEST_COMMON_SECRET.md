[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト

# common/secret モジュール単体テスト

本書は `common/secret/*` の単体テストについて、  
**(1) 仕様テスト（docs が正）** と **(2) impl テスト（カバレッジ目的・mapping が正）** を分けて示す。

## 1. 対象

| 区分 | 対象モジュール | 説明 |
|---|---|---|
| 仕様 | `common/secret/store.py` | 秘密ストア（暗号化して永続化、復旧/堅牢性含む） |
| impl | `common/secret/store.py` | 仕様に含めにくい例外分岐等の到達（カバレッジ目的） |

## 2. 実行方法

### 2.1 仕様テスト（単体）

```powershell
# T01 (spec)
python -m tests.common.secret.T01_SecretStore_01_store_test
python -m tests.common.secret.T01_SecretStore_02_store_edge_test
python -m tests.common.secret.T01_SecretStore_03_store_init_test
python -m tests.common.secret.T01_SecretStore_04_store_misc_test
```

### 2.2 impl テスト（単体）

- (impl) は **カバレッジ到達を主目的**とする。
- このため **mapping が正（-?? を出さない）**ことが前提。

```powershell
# T01 (impl)
python -m tests.common.secret.T01_SecretStore_05impl_store_misc_test
```

### 2.3 カバレッジ計測（推奨）

```powershell
coverage erase

# spec
coverage run -a -m tests.common.secret.T01_SecretStore_01_store_test
coverage run -a -m tests.common.secret.T01_SecretStore_02_store_edge_test
coverage run -a -m tests.common.secret.T01_SecretStore_03_store_init_test
coverage run -a -m tests.common.secret.T01_SecretStore_04_store_misc_test

# impl
coverage run -a -m tests.common.secret.T01_SecretStore_05impl_store_misc_test

coverage report -m
```

## 3. テストケース一覧（仕様）

### 3.1 [COMMON-SECRET:T01-01] encrypt/decrypt roundtrip + LWW（基本）

| テストID | 観点 | 対象 |
|---|---|---|
| COMMON-SECRET:T01-01-01 | user鍵: put/get roundtrip | SecretStore |
| COMMON-SECRET:T01-01-02 | server鍵: roundtrip + has + delete | SecretStore |
| COMMON-SECRET:T01-01-03 | user鍵: 並列 put -> LWW | SecretStore |
| COMMON-SECRET:T01-01-04 | server鍵: 並列 put -> LWW | SecretStore |

### 3.2 [COMMON-SECRET:T01-02] edge（入力ガード/互換/安全性）

| テストID | 観点 | 対象 |
|---|---|---|
| COMMON-SECRET:T01-02-01 | put_user: provider空 -> ValueError | SecretStore |
| COMMON-SECRET:T01-02-02 | put_server: provider空 -> ValueError | SecretStore |
| COMMON-SECRET:T01-02-03 | get_user: provider空 -> None | SecretStore |
| COMMON-SECRET:T01-02-04 | get_server: provider空 -> None | SecretStore |
| COMMON-SECRET:T01-02-05 | has_server_any_key False/True | SecretStore |
| COMMON-SECRET:T01-02-06 | delete_server_keys 安全 | SecretStore |
| COMMON-SECRET:T01-02-07 | 旧prefixなし互換 | SecretStore |
| COMMON-SECRET:T01-02-08 | 壊れJSON復旧 | SecretStore |
| COMMON-SECRET:T01-02-09 | delete_user_keys 全削除 | SecretStore |

### 3.3 [COMMON-SECRET:T01-03] init/recovery（起動時）

| テストID | 観点 | 対象 |
|---|---|---|
| COMMON-SECRET:T01-03-01 | env優先: master.key未生成 | SecretStore |
| COMMON-SECRET:T01-03-02 | env無し: master.key生成 + chmod例外経路 | SecretStore |
| COMMON-SECRET:T01-03-03 | _load_json: pathなし -> {} | SecretStore |
| COMMON-SECRET:T01-03-04 | 破損トークン(user)はスキップ | SecretStore |
| COMMON-SECRET:T01-03-05 | 破損トークン(server)はスキップ | SecretStore |
| COMMON-SECRET:T01-03-06 | 未知provider -> None | SecretStore |
| COMMON-SECRET:T01-03-07 | _save_json: 失敗時tmp削除 | SecretStore |

### 3.4 [COMMON-SECRET:T01-04] misc（堅牢性・部分成功）

| テストID | 観点 | 対象 |
|---|---|---|
| COMMON-SECRET:T01-04-01 | get_user_keys 部分成功（破損トークンはスキップ） | SecretStore |
| COMMON-SECRET:T01-04-02 | get_server_keys gid無し->{} | SecretStore |
| COMMON-SECRET:T01-04-03 | put_server_key 上書き | SecretStore |
| COMMON-SECRET:T01-04-04 | delete_* 空/欠落でもFalse（堅牢性） | SecretStore |

## 4. テストケース一覧（impl）

### 4.1 [COMMON-SECRET:T01-05] (impl) branch/exception coverage

- **目的**：仕様テストでは要求しにくい分岐（例外処理など）に到達し、カバレッジを確保する。  
- **前提**：`tests/_report.py` の mapping が正であり、`-??` 表示を出さない（mapping欠落はNG）。

| テストID | 観点 | 対象 |
|---|---|---|
| COMMON-SECRET:T01-05-01 | backend_name が実装名を返す | SecretStore |
| COMMON-SECRET:T01-05-02 | _dec('') は ValueError | SecretStore |
| COMMON-SECRET:T01-05-03 | _load_json: パス無し -> {} | SecretStore |
| COMMON-SECRET:T01-05-04 | _load_json: 破損JSON→復旧save失敗でも {} を返す | SecretStore |
| COMMON-SECRET:T01-05-05 | _save_json: cleanup unlink 失敗を握りつぶす | SecretStore |

---
[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト
