<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-103500Z-AIPROVREGTEST
lang: ja-JP
canonical_title: Provider Adapter Registry テスト仕様
document_type: testspec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > テスト仕様 > コア仕様 > Provider Adapter Registry テスト仕様

# Provider Adapter Registry テスト仕様

---

## PROVIDER-REGISTRY-T01-01 provider adapter registration
<!-- hldocs:sec_id=provreg-t01-01 -->

### 概要

provider key に対応する adapter を registry に登録できることを検証する。

### 前提条件

- Provider Adapter Registry が初期化済みである
- テスト用 adapter callable または adapter object が用意されている

### 検証内容

- 正規化済み provider key で adapter を登録できる
- 登録済み provider 一覧に provider key が含まれる
- 登録処理で UI 層および AI 層の具体型を要求しない

### 期待結果

- provider key と adapter の対応が registry に保持される

### 参照仕様

- Provider Adapter Registry仕様  
  <!-- hldocs:ref=doc-20260513-102500Z-AIPROVREG#Registryの責務 -->

---

## PROVIDER-REGISTRY-T02-01 provider adapter resolution
<!-- hldocs:sec_id=provreg-t02-01 -->

### 概要

登録済み provider key から adapter を解決できることを検証する。

### 前提条件

- provider key に対応する adapter が登録済みである

### 検証内容

- provider key を指定して adapter を取得できる
- 取得した adapter が呼び出し可能である
- provider key の正規化結果と registry の key が一致する

### 期待結果

- チャットループは registry から解決した adapter を使用できる

### 参照仕様

- Provider Adapter Registry仕様  
  <!-- hldocs:ref=doc-20260513-102500Z-AIPROVREG#Registryの責務 -->

---

## PROVIDER-REGISTRY-T03-01 unregistered provider handling
<!-- hldocs:sec_id=provreg-t03-01 -->

### 概要

未登録 provider を解決しようとした場合、安全側のエラーとして扱われることを検証する。

### 前提条件

- 未登録 provider key を指定できる

### 検証内容

- 未登録 provider key の解決に失敗する
- 未登録 provider 解決失敗が未処理例外として UI 層へ伝播しない
- エラー応答に API キー等の機密情報が含まれない

### 期待結果

- 未登録 provider は設定エラーとして安全に扱われる

### 参照仕様

- Provider Adapter Registry仕様  
  <!-- hldocs:ref=doc-20260513-102500Z-AIPROVREG#エラーポリシー -->

---

## PROVIDER-REGISTRY-T04-01 duplicate registration policy
<!-- hldocs:sec_id=provreg-t04-01 -->

### 概要

同一 provider key に対する重複登録時の扱いが仕様どおりであることを検証する。

### 前提条件

- 同一 provider key に対して複数 adapter を登録可能なテスト環境である

### 検証内容

- 重複登録を禁止する場合、明示的なエラーとなる
- 上書きを許可する場合、最後に登録された adapter が有効となる
- いずれの場合も registry 状態が不定にならない

### 期待結果

- 重複登録時の挙動が決定的である

### 参照仕様

- Provider Adapter Registry仕様  
  <!-- hldocs:ref=doc-20260513-102500Z-AIPROVREG#Registryの責務 -->

---

## PROVIDER-REGISTRY-T05-01 test adapter replacement
<!-- hldocs:sec_id=provreg-t05-01 -->

### 概要

テスト用 adapter に差し替えられることを検証する。

### 前提条件

- テスト用 adapter callable が存在する
- registry 状態をテストごとに初期化できる

### 検証内容

- 本番 provider adapter を使わずにテスト用 adapter を登録できる
- テスト用 adapter がチャットループから呼び出される
- テスト終了後に registry 状態を復元できる

### 期待結果

- 外部 API を呼び出さずに provider 経路をテストできる

### 参照仕様

- Provider Adapter Registry仕様  
  <!-- hldocs:ref=doc-20260513-102500Z-AIPROVREG#Registry登録タイミング -->

---

## PROVIDER-REGISTRY-T06-01 common does not directly import ai provider modules
<!-- hldocs:sec_id=provreg-t06-01 -->

### 概要

`common/chat` が `ai/{provider}` の具体モジュールを直接 import しないことを検証する。

### 前提条件

- `common/chat` 配下の実装ファイルを静的検査できる

### 検証内容

- `common/chat` 配下に `import ai.` が存在しない
- `common/chat` 配下に `from ai.` が存在しない
- `common/chat` が `ai.{provider}.{provider}_api` の命名規約に依存しない

### 期待結果

- `common/chat` は provider registry のみを通じて AI 層へ接続する

### 参照仕様

- Provider Adapter Registry仕様  
  <!-- hldocs:ref=doc-20260513-102500Z-AIPROVREG#依存方向 -->

---

## PROVIDER-REGISTRY-T07-01 adapter failure isolation
<!-- hldocs:sec_id=provreg-t07-01 -->

### 概要

adapter 呼び出し失敗時に、チャットループおよび UI 層へ未処理例外が伝播しないことを検証する。

### 前提条件

- 呼び出し時に例外を送出するテスト用 adapter が用意されている

### 検証内容

- adapter 内部例外が捕捉される
- UI 層へは簡潔なエラー応答が返る
- 詳細エラーはログ記録対象となる
- 機密情報はエラー文に含まれない

### 期待結果

- adapter 失敗時もチャットループは安全に終了する

### 参照仕様

- Provider Adapter Registry仕様  
  <!-- hldocs:ref=doc-20260513-102500Z-AIPROVREG#エラーポリシー -->

---

## PROVIDER-REGISTRY-T08-01 secret redaction on provider errors
<!-- hldocs:sec_id=provreg-t08-01 -->

### 概要

provider adapter 経路で発生したエラーに API キー等の機密情報が混入しないことを検証する。

### 前提条件

- 機密情報を含む例外を送出するテスト用 adapter が用意されている

### 検証内容

- エラー応答に API キーが含まれない
- ログ出力に API キーが含まれない
- redact 処理が provider adapter エラー経路にも適用される

### 期待結果

- provider adapter の失敗経路でも機密情報が保護される

### 参照仕様

- Provider Adapter Registry仕様  
  <!-- hldocs:ref=doc-20260513-102500Z-AIPROVREG#エラーポリシー -->

---

[目次](../../目次.md) > テスト仕様 > コア仕様 > Provider Adapter Registry テスト仕様
