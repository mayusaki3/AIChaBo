[テストユーティリティ](../../README_TEST.md) > common/utilsモジュール単体テスト

# common/utilsモジュール単体テスト

## テスト番号と検証内容（Index）

| Suite | 目的（スコープ） | 機能 | モジュール |
|---|---|---|---|
| **T01-01** | 機密文字列マスキング | api_key / sk- / ghp_ / AIza 等の秘匿化 | `common/utils/redact.py` |
| **T02-01** | ログ出力ユーティリティ | 初期化分岐（handlers有無）/ info・warn・error（redact適用） | `common/utils/logger.py` |

---

## テスト詳細

### T01-01 : 機密文字列マスキング（redact）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-01-01** | api_key prefix+value | `api_key=XXXX` が `api_key=***` に置換される | `common/utils/redact.py` |
| **T01-01-02** | API-KEY prefix+value | `API-KEY: XXXX` が `API-KEY: ***` に置換される（大小無視） | `common/utils/redact.py` |
| **T01-01-03** | sk- 値単体 | `sk-XXXX` が `head(keep)+***` に置換される | `common/utils/redact.py` |
| **T01-01-04** | ghp_ 値単体 | `ghp_XXXX` が `head(keep)+***` に置換される | `common/utils/redact.py` |
| **T01-01-05** | AIza 値単体 | `AIzaXXXX` が `head(keep)+***` に置換される | `common/utils/redact.py` |
| **T01-01-06** | keep 指定 | keep 値変更により表示される head 長が変化する | `common/utils/redact.py` |
| **T01-01-07** | 非文字列入力 | int 等でも例外なく `str(obj)` が返る | `common/utils/redact.py` |
| **T01-01-08** | 非一致 | マスク対象でない文字列は変更されない | `common/utils/redact.py` |


#### 実行

```bash
python -m tests.common.utils.T01_Redact_01_redact_test
```

---

### T02-01 : ログ出力ユーティリティ（logger）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-01-01** | 初期化（handlers無し） | handlers が無い状態で import/reload すると handler が追加され level=INFO になる | `common/utils/logger.py` |
| **T02-01-02** | 初期化（handlers有り） | handlers が既にある状態で import/reload しても handler が増えない（重複しない） | `common/utils/logger.py` |
| **T02-01-03** | warn 出力 | `log_warn()` が WARNING として出力される | `common/utils/logger.py` |
| **T02-01-04** | error は redact | `log_error()` が redact を通して出力される（例：api_key が `***` に） | `common/utils/logger.py` |

#### 実行

```bash
python -m tests.common.utils.T02_Logger_01_logger_test
```

---
[テストユーティリティ](../../README_TEST.md) > common/utilsモジュール単体テスト
