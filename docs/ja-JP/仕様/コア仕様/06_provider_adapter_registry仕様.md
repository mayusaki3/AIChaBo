<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-102500Z-AIPROVREG
lang: ja-JP
canonical_title: Provider Adapter Registry仕様
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > Provider Adapter Registry仕様

# Provider Adapter Registry仕様

## Purpose（存在理由）

本書は、AIChaBo コアから AI プロバイダ層を呼び出すための Provider Adapter Registry の仕様を定義する。

AIChaBo のコアは、UI 層および AI プロバイダ層から独立して動作する必要がある。

そのため、`common` 配下のコア実装は、`ai.openai`、`ai.gemini`、`ai.claude` 等の具体的なディレクトリ構造および関数名規約に直接依存してはならない。

Provider Adapter Registry は、コアが provider 名から実行可能なチャット処理を解決するための抽象化境界である。

---

## Non-goals（対象外）

本書は以下を対象外とする。

- OpenAI / Gemini / Claude 等の各 API 仕様
- 各プロバイダ固有のリクエスト payload 詳細
- 各プロバイダの料金、モデル一覧、利用制限
- Discord 等の UI 層における表示仕様
- 外部連携プラグイン全般の仕様
- 実装コードの具体的なクラス構成

---

## 基本方針

Provider Adapter Registry は、以下の方針に従う。

- `common` は AI 層の内部ファイル配置を知らない
- `common` は provider 名と抽象 adapter のみを扱う
- AI 層は、自身の provider adapter を registry に登録する
- チャットループは registry から adapter を解決して呼び出す
- 未登録 provider はエラー状態として扱う
- adapter 呼び出し失敗は UI 層へ未処理例外として伝播させない

---

## 用語

| 用語 | 意味 |
|---|---|
| provider | OpenAI / Gemini / Claude 等の AI プロバイダを識別する内部名 |
| adapter | provider 固有 API 呼び出しを共通インターフェースへ変換する境界実装 |
| registry | provider 名と adapter の対応を保持するコア側の解決機構 |
| chat callable | チャット応答生成を実行する callable |
| provider key | `openai`、`gemini`、`claude` 等の正規化済み provider 名 |

---

## Registry の責務

Registry は、以下の責務を持つ。

- provider key に対応する adapter を登録する
- provider key に対応する adapter を解決する
- provider key の重複登録を制御する
- 登録済み provider 一覧を返す
- 未登録 provider を検出する
- テスト時に registry 状態を差し替え可能にする

Registry は、AI プロバイダ API を直接呼び出してはならない。

Registry は、adapter の実装詳細を知ってはならない。

---

## Adapter の責務

Adapter は、以下の責務を持つ。

- provider 固有 API を呼び出す
- provider 固有 payload を構築する
- provider 固有 response を共通結果へ変換する
- provider 固有エラーを共通エラーへ変換する
- provider 固有の model / token / vision 対応差異を吸収する

Adapter は、UI 層の型および UI 表示仕様に依存してはならない。

Adapter は、認証情報の保存場所を直接参照してはならない。

Adapter は、呼び出し時に渡された認証情報のみを使用する。

---

## Adapter 呼び出し入力

チャット用 adapter は、少なくとも以下の入力を受け取る。

| 項目 | 必須 | 説明 |
|---|---|---|
| context_list | 必須 | LLM に渡す会話文脈 |
| api_key | 必須 | 解決済み API キー |
| model | 必須 | 使用モデル名 |
| max_tokens | 任意 | 最大出力トークン数 |
| options | 任意 | provider に依存しない追加設定 |

入力は、UI 固有構造ではなく、コアで扱える一般構造でなければならない。

---

## Adapter 呼び出し結果

チャット用 adapter は、少なくとも以下のいずれかを返す。

| 結果 | 意味 |
|---|---|
| text | 正常なテキスト応答 |
| error | provider 呼び出し失敗 |
| tool_request | ツール呼び出し要求 |
| continuation_required | 継続応答が必要な状態 |

初期実装では、既存互換のため文字列応答を許容する。

ただし、将来的には構造化結果へ移行できるようにする。

---

## Registry 登録タイミング

Registry 登録は、以下のいずれかのタイミングで行う。

1. アプリケーション起動時
2. AI 層初期化時
3. テスト初期化時
4. 明示的な reload 操作時

通常実行時に、チャットループが毎回 AI 層を動的 import してはならない。

---

## 依存方向

依存方向は以下とする。

```text
ui
  ↓
common/chat
  ↓
common/chat/provider_registry
  ↓
registered adapter callable
  ↓
ai/{provider}
```

`common/chat` から `ai/{provider}` への直接 import は、移行期間を除き禁止する。

---

## common/plugins との境界

Provider Adapter Registry は、`common/plugins` とは別の概念として扱う。

`common/plugins` は、Web 取得、外部サービス連携、開発サポート等のツール拡張を扱う。

Provider Adapter Registry は、LLM provider 呼び出しを扱う。

両者はどちらも拡張点であるが、以下の理由により分離する。

- provider adapter はチャットループの必須経路である
- external plugin は任意起動の副処理である
- provider adapter は認証済み API キーを直接使用する
- external plugin は必ずしも LLM provider 認証情報を使用しない

---

## エラーポリシー

Registry または Adapter でエラーが発生した場合、以下の方針に従う。

- 未登録 provider は設定エラーとして扱う
- adapter 呼び出し失敗は provider 呼び出しエラーとして扱う
- 詳細はログへ記録する
- UI 層へは簡潔なエラーを返す
- API キーなどの機密値はログおよび UI 出力へ含めない

---

## 移行方針

現行の `common/chat/chat_loop.py` は、provider 名から `ai.{provider}.{provider}_api` を動的 import している。

この方式は、移行前の互換手段としてのみ扱う。

移行後は、以下の構成を目標とする。

1. `common/chat/provider_registry.py` を追加する
2. OpenAI / Gemini / Claude の adapter を登録する
3. `common/chat/chat_loop.py` は registry のみを参照する
4. AI 層のファイル配置規約を `common` から除去する
5. 既存テストに provider registry 境界テストを追加する

---

## テスト観点

Provider Adapter Registry には、少なくとも以下のテスト観点が必要である。

| テスト番号 | 観点 |
|---|---|
| PR-001 | provider adapter を登録できる |
| PR-002 | 登録済み provider を解決できる |
| PR-003 | 未登録 provider 解決時に安全側のエラーとなる |
| PR-004 | 重複登録時の扱いが仕様どおりである |
| PR-005 | テスト用 adapter へ差し替えできる |
| PR-006 | `common/chat` が `ai/{provider}` を直接 import しない |
| PR-007 | adapter 呼び出し失敗時に UI 層へ未処理例外が伝播しない |
| PR-008 | 機密情報がログ・エラー文へ混入しない |

---

## 他 document_type との関係

本書は、AIChaBo コア仕様 概要およびチャットループ仕様に従属する spec である。

Provider Adapter Registry の testspec は、本書を参照して作成される。

実装は、本書および対応 testspec が確定した後に作成される。

---

[目次](../../目次.md) > 仕様 > コア仕様 > Provider Adapter Registry仕様
