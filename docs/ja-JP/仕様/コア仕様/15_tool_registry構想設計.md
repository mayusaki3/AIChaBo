<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260525-141500Z-TOOLREGCONCEPT
lang: ja-JP
canonical_title: tool_registry構想設計
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > tool_registry構想設計

# tool_registry構想設計

## Purpose（存在理由）

本書は、AIChaBo の外部ツール連携を UI 層および AI provider 層から独立させるための Tool Registry 構想を定義する。

Provider Adapter Registry が AI provider 呼び出し境界を分離するのに対し、Tool Registry は Web 取得、外部 API、開発支援、Workflow 実行等の外部処理境界を分離する。

---

## 現状

現行 develop では、`common/plugins` に plugin dispatch の基盤が存在する。

既存実装は以下の特徴を持つ。

- `common/plugins/providers` 配下の Python ファイルを自動探索する
- `ProviderPlugin` protocol を使う
- URL match / plan / consume の流れを持つ
- 必要に応じて二段目 I/O を実行できる
- system prompt を plugin result meta に付与できる

これは Web 読取系 plugin としては有効である。

一方で、今後の外部ツール連携全体を扱うには、より一般化した Tool Registry が必要である。

---

## Tool Registry の位置づけ

Tool Registry は、以下を扱う共通コア機構である。

- Web 取得
- URL plugin
- ファイル処理
- GitHub 等の開発支援
- Workflow 実行
- Runtime IDE 連携
- 外部サービス API
- 将来のローカルツール実行

Tool Registry は、UI 層に依存してはならない。

Tool Registry は、AI provider 層に依存してはならない。

---

## Provider Registry との違い

| 項目 | Provider Adapter Registry | Tool Registry |
|---|---|---|
| 対象 | LLM provider 呼び出し | 外部ツール・副処理 |
| 必須性 | chat_loop の必須経路 | 必要時に選択実行 |
| 認証 | LLM API key | tool ごとの認証・設定 |
| 戻り値 | LLM応答 | tool result |
| 呼び出し元 | chat_loop | runtime / planner / plugin dispatcher |

---

## common/plugins との関係

`common/plugins` は Tool Registry の前段階または URL tool の一種として扱う。

初期移行では、既存 `common/plugins/dispatcher.py` を壊さず、Tool Registry の設計対象として以下のように位置づける。

```text
common/runtime/tool_registry.py
  ↓
common/plugins/dispatcher.py
  ↓
common/plugins/providers/*
```

つまり、既存 plugins を即座に廃止せず、Tool Registry から呼び出される tool adapter として再利用する。

---

## Tool の分類

初期分類は以下とする。

| 分類 | 内容 |
|---|---|
| url_tool | URL を入力として処理する tool |
| file_tool | 添付・ファイルを入力として処理する tool |
| dev_tool | GitHub / GitLab / CI / code review 等の開発支援 tool |
| workflow_tool | Workflow IDE / Runtime IDE 等の手順実行 tool |
| context_tool | Context / memory / summary を操作する tool |
| external_api_tool | 外部サービス API を呼び出す tool |

---

## Tool Registry の責務

Tool Registry は以下を担当する。

- tool key と tool adapter の登録
- tool capability の管理
- tool 実行要求の検証
- tool adapter 解決
- mock tool 差し替え
- tool 一覧取得
- tool 実行結果の共通化

Tool Registry は以下を担当しない。

- UI 表示
- LLM provider 呼び出し
- provider API key 管理
- Discord interaction 直接操作

---

## Tool Adapter の責務

Tool Adapter は以下を担当する。

- 外部処理の実行
- tool 固有 request の解釈
- tool 固有 response の共通 result 化
- tool 固有エラーの共通化
- 必要な認証情報の受け取り

Tool Adapter は UI 型に依存してはならない。

Tool Adapter は実行時に渡された context / credentials / options のみを使用する。

---

## 初期 Tool Registry API 案

初期 API 案は以下とする。

| API | 役割 |
|---|---|
| register_tool(tool_key, adapter, capabilities, overwrite=False) | tool を登録する |
| resolve_tool(tool_key) | tool adapter を解決する |
| list_tools() | 登録済み tool 一覧を返す |
| find_tools_by_capability(capability) | capability で tool を検索する |
| clear_tools() | registry を空にする |
| snapshot_tools() | registry 状態を退避する |
| restore_tools(snapshot) | registry 状態を復元する |

---

## Tool Request / Tool Result

Tool Registry では、将来的に以下の共通構造を導入する。

```text
ToolRequest
  - tool_key
  - input
  - context
  - credentials
  - options

ToolResult
  - success
  - items
  - display_text
  - citations
  - artifacts
  - meta
  - error
```

既存 `PluginResult` は、初期段階では `ToolResult` の一種として扱える。

---

## 実装フェーズ案

### Phase 1: 設計整理

- Tool Registry 仕様作成
- existing common/plugins との対応表作成
- URL tool adapter 方針作成

### Phase 2: Registry 実装

- common/runtime/tool_registry.py 追加
- registry tests 追加
- static import boundary tests 追加

### Phase 3: plugins bridge

- common/plugins/dispatcher.py を tool adapter 化
- URL plugin を url_tool として登録
- existing tests を維持

### Phase 4: dev_tool 追加

- GitHub / GitLab / CI 連携を tool adapter として扱う
- 開発支援機能へ接続

### Phase 5: runtime pipeline 統合

- chat_loop 直結ではなく runtime pipeline から tool を呼ぶ
- Context Lifecycle と連携する

---

## 注意点

Tool Registry は Provider Adapter Registry より影響範囲が広い。

そのため、既存 `common/plugins` を即時置換せず、bridge 方式で段階移行する。

Tool 実行は外部副作用を伴う可能性があるため、以下を仕様化する必要がある。

- dry-run
- permission
- user confirmation
- credential scope
- audit log
- timeout
- cancellation
- rate limit

---

## 次作業

次作業は以下である。

1. Tool Registry 仕様を作成する
2. common/plugins 現状照合結果を作成する
3. Tool Request / Tool Result 詳細設計を作成する
4. plugin dispatcher bridge 設計を作成する
5. 実装は設計と testspec 確定後に行う

---

[目次](../../目次.md) > 仕様 > コア仕様 > tool_registry構想設計
