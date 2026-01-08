# テストユーティリティ

Discord を介さずに各機能の健全性を確認するためのテスト群です。  
CI 実行を想定し、書き込みを伴うテストは **既定で skip / dry-run** です。  
  
開発テスト用に以下のインストール作業を行ってください。
```shell
pip install -r requirements-dev.txt
```
各テストは「python -m tests.common.chat.*」のように実行しますが、以下の形式で実行すると、テストのカバー率が確認できます。
```shell
# テスト実行（通常実行）
python -m tests.common.chat.T01_Provider_01_provider_test

# テスト実行（カバー率確認：単一）
coverage run -m tests.common.chat.T01_Provider_01_provider_test

# テスト実行（カバー率確認：全体）
coverage run -m unittest discover -s tests -p "*_test.py"

# テスト実行（カバー率確認：全体・結果を累積）
coverage erase
coverage run -a -m tests.common.chat.T01_Provider_01_provider_test
coverage run -a -m tests.common.secret.T02_SecretStore_01_store_test
#    :             以下、残りのテストを実施

# カバー率レポート表示
coverage report -m
# カバー率レポート詳細表示（ブラウザ表示）
coverage html
htmlcov/index.html
```

これらをまとめたPowerShellスクリプトがあります。
```powershell
# 全テスト実行
.\tests\test_all.ps1
```

## テスト番号と検証内容（Index）

> すべてのテストは共通レポータにより  
> `✅/❌[DOMAIN-MODULE:Txx-yy-zz] <タイトル>`  
> `--- SUMMARY DOMAIN-MODULE:Txx-yy: ✅=N / ❌=M / TOTAL=K ---`  
> を出力します。  
> unittest は **メソッド名の昇順**（`test_01_*` → `test_02_*` …）で実行します。

例：
```
✅[COMMON-CHAT:T01-01-01] ...
--- SUMMARY COMMON-CHAT:T01-01 common/chat/provider: ✅=4 / ❌=0 / TOTAL=4 ---
```

### マッピング未登録時（-?? 表示）の扱い

`tests/_report.py` は、`run_unittest_suite(..., mapping)` に渡された **mapping(dict)** に
テストメソッドが見つからない場合、テストIDを **`<suite_id>-??`** として表示する。

例：
```
✅[COMMON-SECRET:T01-04 common/secret/store-??] test_99_unmapped_case
```

これは **「テストIDのマッピングが未登録」**を示すフォールバックであり、
README 側の表記やモジュール名が未確定であることを意味しない。

運用ルール：
- 原則として、コミット対象のテストは mapping を必ず揃え、`-??` 表示を残さない。
- 仕様/棚卸し未完のテストは、ファイル名プレフィックス `_Txx_...` 等で明示し、
  その間は mapping 未整備（-?? 表示）を許容してもよい（運用で選択）。

### 単体テスト
- [common/secretモジュール単体テスト](common/secret/README_TEST_COMMON_SECRET.md)
- [common/chatモジュール単体テスト](common/chat/README_TEST_COMMON_CHAT.md)
- [common/utilsモジュール単体テスト](common/utils/README_TEST_COMMON_UTILS.md)
- [common/sessionモジュール単体テスト](common/session/README_TEST_COMMON_SESSION.md)

### 結合テスト




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

---

## 備考

このテストセットにより、  
**Discord 非依存**の範囲を先にテストできます（高速／安全／CI 向き）。
