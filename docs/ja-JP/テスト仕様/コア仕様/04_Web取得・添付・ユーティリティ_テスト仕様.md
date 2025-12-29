[目次](../../目次.md) > テスト仕様 > コア仕様 > Web取得・添付・ユーティリティ テスト仕様

# Web取得・添付・ユーティリティ テスト仕様（コア仕様）

本書は、**コア仕様「Web取得・添付・ユーティリティ仕様」** に対応する  
テスト仕様を定義する。

---

## 1. 対応仕様

- [Web取得・添付・ユーティリティ仕様](../../仕様/コア仕様/04_Web取得・添付・ユーティリティ仕様.md)

---

## 2. テスト対象モジュール

| 領域 | 対象モジュール |
|---|---|
| Web取得 | common/utils/webread_utils.py |
| 添付管理 | common/utils/attachments.py |
| JSONC | common/utils/jsonc.py |
| ログ | common/utils/logger.py |
| マスク | common/utils/redact.py |
| スレッド補助 | common/utils/thread_utils.py |

---

## 3. 仕様テスト定義

### 3.1 Web取得の安全性

#### 対応仕様
- [Web取得・添付・ユーティリティ仕様 / 3. Web 取得（検索/読み取り）](../../仕様/コア仕様/04_Web取得・添付・ユーティリティ仕様.md#3-web-取得検索読み取り)

#### 観点
- HTTP エラー時に例外を外部へ漏らさない
- 想定外 MIME でも処理継続する
- タイムアウト時に停止しない

#### 該当テスト
- [COMMON-UTILS:T08-01-xx] webread robustness

---

### 3.2 添付ファイル管理

#### 対応仕様
- [Web取得・添付・ユーティリティ仕様 / 4. 添付管理（attachments）](../../仕様/コア仕様/04_Web取得・添付・ユーティリティ仕様.md#4-添付管理attachments)

#### 観点
- attachment_id 単位で一意に管理される
- ファイル欠損時も致命障害にならない

#### 該当テスト
- [COMMON-UTILS:T09-01-xx] attachment handling

---

### 3.3 JSONC 読み書き

#### 対応仕様
- [Web取得・添付・ユーティリティ仕様 / 5. JSONC 読み取り（jsonc）](../../仕様/コア仕様/04_Web取得・添付・ユーティリティ仕様.md#5-jsonc-読み取りjsonc)

#### 観点
- コメント付き JSON を正しく処理できる
- 構文エラー時に空 dict へフォールバックする

#### 該当テスト
- [COMMON-UTILS:T10-01-xx] jsonc load/save

---

## 4. (impl) テスト

- 分岐網羅
- ログ出力経路
- redact マスク条件

#### 該当テスト
- [COMMON-UTILS:Txx-xx-xx] (impl) branch coverage

---
[目次](../../目次.md) > テスト仕様 > コア仕様 > Web取得・添付・ユーティリティ テスト仕様
