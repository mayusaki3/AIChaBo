<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-104500Z-CHATLOOPDI
lang: ja-JP
canonical_title: chat_loop依存逆転設計
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > chat_loop依存逆転設計

# chat_loop依存逆転設計

## Purpose（存在理由）

本書は、`common/chat/chat_loop.py` から AI プロバイダ層への直接依存を除去し、Provider Adapter Registry 経由へ移行するための設計を定義する。

現行の `chat_loop.py` は、provider 名から `ai.{provider}.{provider}_api` を動的 import している。

この構成は動作上は有効であるが、`common` コアが AI 層の配置規約を知っているため、コア責務境界の観点では移行対象である。

---

## Non-goals（対象外）

本書は以下を対象外とする。

- 実装コードの作成
- OpenAI / Gemini / Claude 個別 API の詳細仕様
- UI 層の変更
- 外部連携プラグイン仕様の変更
- 既存チャットループ仕様の全面改訂

---

## 現行構造

現行のチャットループでは、概ね以下の流れで AI プロバイダ呼び出しを行う。

```text
common/chat/chat_loop.py
  ↓ provider名からモジュール名を組み立て
ai.{provider}.{provider}_api
  ↓
call_{provider}_chat(...)
```

この構造では、`common/chat/chat_loop.py` が以下を知っている。

- AI 層が `ai` 配下に存在すること
- provider ごとに `ai/{provider}/{provider}_api.py` が存在すること
- チャット関数名が `call_{provider}_chat` であること

これらは AI 層の実装規約であり、コア側が直接知るべきではない。

---

## 目標構造

移行後の目標構造は以下とする。

```text
common/chat/chat_loop.py
  ↓
common/chat/provider_registry.py
  ↓
registered provider adapter
  ↓
ai/{provider}/...
```

`chat_loop.py` は provider adapter の登録・解決機構のみを参照する。

`chat_loop.py` は `ai` 配下のファイル名、モジュール名、関数名を組み立ててはならない。

---

## 責務分離

### chat_loop.py の責務

`chat_loop.py` は以下に責務を限定する。

- 入力検証
- policy 取得
- 認証情報解決
- provider key 正規化
- provider adapter 解決要求
- provider adapter 呼び出し
- 応答文字列化
- 例外捕捉と安全なエラー応答

`chat_loop.py` は provider 固有 API の payload を構築してはならない。

`chat_loop.py` は provider 固有 response を解釈してはならない。

### provider_registry.py の責務

`provider_registry.py` は以下に責務を限定する。

- provider key と adapter callable の対応管理
- adapter 登録
- adapter 解決
- adapter 一覧取得
- registry 初期化またはクリア
- テスト用差し替え支援

`provider_registry.py` は provider 固有 API を直接呼び出してはならない。

### provider adapter の責務

provider adapter は以下に責務を持つ。

- provider 固有 API 呼び出し
- provider 固有 payload 構築
- provider 固有 response 解釈
- provider 固有エラーの共通化
- model / token / vision 等の provider 差異吸収

---

## 最小移行インターフェース

初期移行では、既存互換を優先し、provider adapter は以下の callable 形を満たせばよい。

```text
async callable(
    context_list: list[str],
    api_key: str,
    model: str,
    **options
) -> str
```

この形式は既存の `call_openai_chat` 等に近く、移行コストを抑える。

将来的に tool request や continuation を構造化する場合は、戻り値を構造化 result へ拡張する。

---

## 互換移行方針

移行は以下の段階で行う。

### Phase 1: Registry 追加

`common/chat/provider_registry.py` を追加する。

この段階では、既存 AI provider 実装は変更しない。

### Phase 2: Adapter 登録処理追加

OpenAI / Gemini / Claude の既存 `call_{provider}_chat` を registry に登録する初期化処理を追加する。

登録処理は、AI 層または起動処理側に置く。

### Phase 3: chat_loop.py の参照先変更

`chat_loop.py` の `_get_provider_chat_fn` を provider registry 参照へ置き換える。

この段階で `chat_loop.py` から `importlib.import_module("ai...")` 相当の処理を除去する。

### Phase 4: 静的検査追加

`common/chat` 配下に `import ai.` または `from ai.` が存在しないことを検証するテストを追加する。

### Phase 5: 構造化 result 移行検討

必要に応じて、provider adapter の戻り値を文字列から構造化 result へ拡張する。

---

## エラー処理

provider adapter が未登録の場合、`chat_loop.py` は設定エラーとして安全に終了する。

provider adapter の呼び出し中に例外が発生した場合、`chat_loop.py` は例外を捕捉し、UI 層へ未処理例外を伝播させない。

エラー詳細はログへ記録する。

ログおよび UI 応答には API キー等の機密情報を含めてはならない。

---

## テスト対応

本設計に対応する主なテストは以下である。

- Provider Adapter Registry テスト仕様
  - PROVIDER-REGISTRY-T01-01
  - PROVIDER-REGISTRY-T02-01
  - PROVIDER-REGISTRY-T03-01
  - PROVIDER-REGISTRY-T05-01
  - PROVIDER-REGISTRY-T06-01
  - PROVIDER-REGISTRY-T07-01
  - PROVIDER-REGISTRY-T08-01

実装前に、provider registry の単体テストを先に作成する。

---

## 採用判断

本設計を採用することで、`common/chat` は AI 層の配置規約から分離される。

これにより、今後の以下の拡張が容易になる。

- 新規 AI provider 追加
- ローカル LLM provider 追加
- テスト用 mock provider 差し替え
- 開発支援用 provider の実験
- UI 層を Discord 以外へ展開する場合の再利用

---

[目次](../../目次.md) > 仕様 > コア仕様 > chat_loop依存逆転設計
