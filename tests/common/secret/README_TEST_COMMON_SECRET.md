[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト

# common/secret モジュール単体テスト（SecretStore）

本書は `common/secret/store.py` を対象とする単体テストの案内である。  
本モジュールは「認証情報（APIキー等）の暗号化保存」を担い、ユーザー単位・ギルド単位の両方を扱う。

## 1. 対象

- 実装：`common/secret/store.py`
- テスト：`tests/common/secret/*`
- 仕様（正）：`docs/ja-JP/テスト仕様/コア仕様/01_認証・秘密ストア_テスト仕様.md`

## 2. テストスイート一覧（仕様テスト / implテスト）

### 2.1 仕様テスト（docs が正）

| Suite | 目的 | テストコード |
|---|---|---|
| COMMON-SECRET:T01-01 | put/get の基本動作・LWW（並列 put の勝ち） | `tests/common/secret/T01_SecretStore_01_store_test.py` |
| COMMON-SECRET:T01-02 | 入力ガード・互換（旧prefix）・壊れJSON復旧・delete 全削除など | `tests/common/secret/T01_SecretStore_02_store_edge_test.py` |
| COMMON-SECRET:T01-03 | 初期化（master.key生成/復旧）・load/save の基本枝 | `tests/common/secret/T01_SecretStore_03_store_init_test.py` |
| COMMON-SECRET:T01-04 | 追加の堅牢性（部分成功 / 上書き / 空削除など） | `tests/common/secret/T01_SecretStore_04_store_misc_test.py` |

※仕様テスト（T01-01/02/03/04）は **ドキュメント（テスト仕様）記載が正**であり、README 側では「詳細の表」を維持する。  
（テストコードは docs に従い実装される前提）

### 2.2 implテスト（mapping が正 / カバレッジ目的）

| Suite | 目的 | テストコード |
|---|---|---|
| COMMON-SECRET:T01-05 (impl) | 実装枝（例外・復旧・cleanup等）に到達しカバレッジを上げる | `tests/common/secret/T01_SecretStore_05impl_store_misc_test.py` |

※T01-05 (impl) は「仕様の充足」ではなく「未到達行の到達」を目的とする。  
そのため、**テストIDの正（source of truth）は mapping（`run_unittest_suite(..., mapping)` に渡す辞書）**とする。  
README 側では「テストコード内 mapping を参照」する運用とする（詳細表の正は README ではなく mapping）。

## 3. テストケース詳細（仕様テスト：詳細の表）

### 3.1 COMMON-SECRET:T01-01（基本動作 / LWW）

| テストID | 観点 | テストコード（メソッド） |
|---|---|---|
| COMMON-SECRET:T01-01-01 | user鍵: put/get roundtrip | `T01_SecretStore_01_store_test.py::test_01_user_roundtrip` |
| COMMON-SECRET:T01-01-02 | server鍵: roundtrip + has + delete | `T01_SecretStore_01_store_test.py::test_02_server_roundtrip_and_delete` |
| COMMON-SECRET:T01-01-03 | user鍵: 並列 put -> LWW | `T01_SecretStore_01_store_test.py::test_03_user_concurrent_lww` |
| COMMON-SECRET:T01-01-04 | server鍵: 並列 put -> LWW | `T01_SecretStore_01_store_test.py::test_04_server_concurrent_lww` |

### 3.2 COMMON-SECRET:T01-02（edge / guard / compatibility）

| テストID | 観点 | テストコード（メソッド） |
|---|---|---|
| COMMON-SECRET:T01-02-01 | put_user: provider空 -> ValueError | `T01_SecretStore_02_store_edge_test.py::test_01_put_user_empty_provider_raises` |
| COMMON-SECRET:T01-02-02 | put_server: provider空 -> ValueError | `T01_SecretStore_02_store_edge_test.py::test_02_put_server_empty_provider_raises` |
| COMMON-SECRET:T01-02-03 | get_user: provider空 -> None | `T01_SecretStore_02_store_edge_test.py::test_03_get_user_empty_provider_returns_none` |
| COMMON-SECRET:T01-02-04 | get_server: provider空 -> None | `T01_SecretStore_02_store_edge_test.py::test_04_get_server_empty_provider_returns_none` |
| COMMON-SECRET:T01-02-05 | has_server_any_key False/True | `T01_SecretStore_02_store_edge_test.py::test_05_has_server_any_key_false_then_true` |
| COMMON-SECRET:T01-02-06 | delete_server_keys 安全 | `T01_SecretStore_02_store_edge_test.py::test_06_delete_server_keys_safe_when_no_entry` |
| COMMON-SECRET:T01-02-07 | 旧prefixなし互換 | `T01_SecretStore_02_store_edge_test.py::test_07_backward_compat_no_prefix` |
| COMMON-SECRET:T01-02-08 | 壊れJSON復旧 | `T01_SecretStore_02_store_edge_test.py::test_08_broken_json_is_recovered_to_empty` |
| COMMON-SECRET:T01-02-09 | delete_user_keys 全削除 | `T01_SecretStore_02_store_edge_test.py::test_09_delete_user_keys_clears_all` |

### 3.3 COMMON-SECRET:T01-03（init / recovery / tmp-cleanup）

| テストID | 観点 | テストコード（メソッド） |
|---|---|---|
| COMMON-SECRET:T01-03-01 | env優先: master.key未生成 | `T01_SecretStore_03_store_init_test.py::test_01_init_with_env_key` |
| COMMON-SECRET:T01-03-02 | env無し: master.key生成 + chmod例外経路 | `T01_SecretStore_03_store_init_test.py::test_02_init_generates_masterkey_and_handles_chmod_error` |
| COMMON-SECRET:T01-03-03 | _load_json: pathなし -> {} | `T01_SecretStore_03_store_init_test.py::test_03_load_json_when_path_not_exists` |
| COMMON-SECRET:T01-03-04 | 破損トークン(user)はスキップ | `T01_SecretStore_03_store_init_test.py::test_04_corrupted_user_tokens_are_skipped` |
| COMMON-SECRET:T01-03-05 | 破損トークン(server)はスキップ | `T01_SecretStore_03_store_init_test.py::test_05_server_keys_skip_only_corrupt_entries` |
| COMMON-SECRET:T01-03-06 | 未知provider -> None | `T01_SecretStore_03_store_init_test.py::test_06_get_server_key_unknown_provider` |
| COMMON-SECRET:T01-03-07 | _save_json: 失敗時tmp削除 | `T01_SecretStore_03_store_init_test.py::test_07_save_json_tmp_cleanup_on_replace_error` |

### 3.4 COMMON-SECRET:T01-04（misc / robustness）

| テストID | 観点 | テストコード（メソッド） |
|---|---|---|
| COMMON-SECRET:T01-04-01 | get_user_keys 部分成功（破損トークンはスキップ） | `T01_SecretStore_04_store_misc_test.py::SecretStoreMiscTest.test_01_get_user_keys_partial_success` |
| COMMON-SECRET:T01-04-02 | get_server_keys gid無し->{} | `T01_SecretStore_04_store_misc_test.py::SecretStoreMiscTest.test_02_get_server_keys_missing_gid_returns_empty` |
| COMMON-SECRET:T01-04-03 | put_server_key 上書き | `T01_SecretStore_04_store_misc_test.py::SecretStoreMiscTest.test_03_put_server_key_overwrite` |
| COMMON-SECRET:T01-04-04 | delete_* 空/欠落でもFalse（堅牢性） | `T01_SecretStore_04_store_misc_test.py::SecretStoreMiscTest.test_04_delete_empty_or_missing_is_safe_false` |

## 4. 実行方法

### 4.1 個別実行（python -m）

```powershell
# T01-01～T01-05 を個別実行例
python -m tests.common.secret.T01_SecretStore_01_store_test
python -m tests.common.secret.T01_SecretStore_02_store_edge_test
python -m tests.common.secret.T01_SecretStore_03_store_init_test
python -m tests.common.secret.T01_SecretStore_04_store_misc_test
python -m tests.common.secret.T01_SecretStore_05impl_store_misc_test
```

### 4.2 一括実行（tests/test_all.ps1）

```powershell
# ルートで
.\tests\test_all.ps1
```

## 5. カバレッジ（coverage）

```powershell
# 例：SecretStore のみ
coverage erase
coverage run -a -m tests.common.secret.T01_SecretStore_01_store_test
coverage run -a -m tests.common.secret.T01_SecretStore_02_store_edge_test
coverage run -a -m tests.common.secret.T01_SecretStore_03_store_init_test
coverage run -a -m tests.common.secret.T01_SecretStore_04_store_misc_test
coverage run -a -m tests.common.secret.T01_SecretStore_05impl_store_misc_test
coverage report -m
```

## 6. mapping 失敗（-??）の扱い

テスト出力に `common/secret/store-??` のような `-??` が出るのは、  
`tests/_report.py` に渡した mapping 辞書でテストメソッド名が解決できなかったことを意味する。

本プロジェクトでは **-?? を許容しない運用**とするため、  
各テストコードは `run_unittest_suite(..., mapping)` に「全テストメソッドの mapping」を必ず含めること。

---
[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト
