<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-105500Z-PROVREGDETAIL
lang: ja-JP
canonical_title: provider_registry詳細設計
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > provider_registry詳細設計

# provider_registry詳細設計

## Purpose（存在理由）

本書は、Provider Adapter Registry仕様および chat_loop依存逆転設計に基づき、`common/chat/provider_registry.py` の詳細設計を定義する。

本設計は、`common/chat/chat_loop.py` から AI 層の具体ディレクトリ構造および関数命名規約への依存を除去するための実装前設計である。

---

## Non-goals（対象外）

本書は以下を対象外とする。

- 実装コードそのもの
- OpenAI / Gemini / Claude の個別 adapter 実装
- UI 層の初期化処理詳細
- 画像認識、画像生成、音声等の provider 拡張仕様
- 外部連携プラグインの registry 仕様

---

## 設計方針

`provider_registry.py` は、以下の方針で設計する。

- コアから見える provider 呼び出し境界を単一化する
- provider 名は正規化済み key として扱う
- adapter は callable として登録する
- registry は AI provider API を直接呼び出さない
- registry は UI 固有型を扱わない
- テスト時に registry 状態を安全に差し替えられる
- 重複登録の扱いは決定的にする

---

## 配置

配置先は以下とする。

```text
common/chat/provider_registry.py
```

このファイルは `common/chat` 配下に置く。

理由は、registry がチャット実行経路専用の provider 解決機構であり、外部連携プラグインとは責務が異なるためである。

---

## 公開API

初期実装で必要な公開 API は以下とする。

| API | 役割 |
|---|---|
| `register_provider(provider: str, adapter: ChatProviderAdapter, *, overwrite: bool = False) -> None` | provider adapter を登録する |
| `resolve_provider(provider: str) -> ChatProviderAdapter` | provider adapter を解決する |
| `has_provider(provider: str) -> bool` | provider 登録有無を返す |
| `list_providers() -> list[str]` | 登録済み provider key 一覧を返す |
| `clear_providers() -> None` | registry を空にする |
| `snapshot_providers() -> dict[str, ChatProviderAdapter]` | 現在状態を退避する |
| `restore_providers(snapshot: dict[str, ChatProviderAdapter]) -> None` | 退避状態へ復元する |

---

## ChatProviderAdapter 型

初期実装では、ChatProviderAdapter を以下の callable protocol として扱う。

```text
async callable(
    context_list: list[str],
    api_key: str,
    model: str,
    **options
) -> str
```

戻り値は既存互換のため文字列とする。

将来的に tool request、continuation、token usage 等を扱う場合は、戻り値を構造化 result へ拡張する。

---

## provider key 正規化

registry API に渡される provider 名は、内部で `common/chat/provider.py` の `normalize_provider` 相当の処理により正規化する。

登録時と解決時の正規化規則は同一でなければならない。

未正規化名で登録された場合でも、registry 内部では正規化済み key で保持する。

例:

| 入力 | 内部 key |
|---|---|
| `OpenAI` | `openai` |
| `openai` | `openai` |
| `Anthropic` | `claude` |
| `google` | `gemini` |

---

## 重複登録ポリシー

初期実装では、重複登録は原則禁止する。

同一 provider key が既に登録済みの場合、`overwrite=False` では明示的な例外を送出する。

テストや reload 用に上書きが必要な場合は、`overwrite=True` を指定した場合のみ上書きを許可する。

この方針により、本番実行時の意図しない provider 差し替えを防止しつつ、テスト時の差し替えを可能にする。

---

## 未登録 provider の扱い

`resolve_provider(provider)` は、未登録 provider に対して明示的な例外を送出する。

ただし、この例外は `chat_loop.py` 側で捕捉され、UI 層へ未処理例外として伝播してはならない。

UI 層へ返す文言は、設定エラーであることが識別できる簡潔な内容とする。

---

## registry 状態管理

registry はプロセス内メモリとして保持する。

初期実装では永続化しない。

理由は、adapter は関数または callable object であり、永続化対象ではないためである。

永続化するのは provider 設定や認証情報であり、adapter 登録状態ではない。

---

## テスト差し替え

テストでは、外部 API を呼ばない mock adapter を registry に登録できなければならない。

テスト実行時は以下のいずれかの方式を許可する。

1. `clear_providers()` 後に mock adapter を登録する
2. `snapshot_providers()` で退避し、テスト後に `restore_providers()` で復元する
3. `overwrite=True` で対象 provider のみ mock adapter に差し替える

テスト間で registry 状態が漏洩してはならない。

---

## chat_loop.py との接続

`chat_loop.py` は、現行の `_get_provider_chat_fn(provider)` を以下の挙動へ変更する。

```text
_get_provider_chat_fn(provider)
  ↓
provider_registry.resolve_provider(provider)
```

`chat_loop.py` は `importlib.import_module("ai...")` を使用してはならない。

`chat_loop.py` は `call_{provider}_chat` という命名規約を知ってはならない。

---

## 初期化フローとの関係

provider registry は、起動処理または AI 層初期化処理によって登録される。

`chat_loop.py` は、未登録 provider の場合に登録処理を自動実行してはならない。

理由は、チャットループの責務を provider 登録まで拡張すると、初期化責務と実行責務が混在するためである。

---

## セキュリティ

registry は API キーを保持してはならない。

API キーは、チャットループで認証解決された後、adapter 呼び出し引数として渡される。

registry の一覧表示やデバッグ出力に機密情報が含まれてはならない。

---

## エラー分類

| 状態 | 分類 | 処理 |
|---|---|---|
| provider 名が空 | 設定エラー | 登録・解決を拒否 |
| adapter が callable でない | 実装エラー | 登録を拒否 |
| provider 未登録 | 設定エラー | resolve で例外 |
| 重複登録 | 実装または初期化エラー | overwrite=False では例外 |
| adapter 呼び出し失敗 | provider 呼び出しエラー | chat_loop 側で捕捉 |

---

## 実装前提

実装前に、以下のテストを作成する。

- provider adapter 登録テスト
- provider adapter 解決テスト
- 未登録 provider テスト
- 重複登録テスト
- mock adapter 差し替えテスト
- `common/chat` から `ai.` を直接 import しない静的検査

---

## 採用判断

本詳細設計を採用することで、provider 呼び出し境界は `provider_registry.py` に集約される。

これにより、`common/chat/chat_loop.py` は AI 層の具体構造から分離される。

---

[目次](../../目次.md) > 仕様 > コア仕様 > provider_registry詳細設計
