<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-111500Z-ADAPTERBOOT
lang: ja-JP
canonical_title: adapter_bootstrap詳細設計
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > adapter_bootstrap詳細設計

# adapter_bootstrap詳細設計

## Purpose（存在理由）

本書は、AIChaBo における標準 AI provider adapter を Provider Adapter Registry へ登録する bootstrap 処理の詳細設計を定義する。

bootstrap は、`common/chat` から AI 層への直接依存を排除しつつ、OpenAI / Gemini / Claude 等の既存 provider 実装を registry 経由で利用可能にするための初期化境界である。

---

## Non-goals（対象外）

本書は以下を対象外とする。

- Provider Adapter Registry の API 詳細
- `chat_loop.py` の実装修正詳細
- 各 provider API payload の詳細
- 認証情報の検証処理
- Discord 等 UI 層の起動仕様
- 外部連携プラグインの初期化仕様

---

## 配置

adapter bootstrap の配置は以下とする。

```text
ai/provider_bootstrap.py
```

このファイルは AI 層に属する。

`ai/provider_bootstrap.py` は `common/chat/provider_registry.py` を import して、AI 層の既存 chat callable を registry へ登録する。

---

## 依存方向

依存方向は以下とする。

```text
起動処理
  ↓
ai/provider_bootstrap.py
  ↓
common/chat/provider_registry.py
  ↑
ai/openai/openai_api.py
ai/gemini/gemini_api.py
ai/claude/claude_api.py
```

`common/chat` から `ai/provider_bootstrap.py` を import してはならない。

`common/chat` から `ai/openai` 等を import してはならない。

---

## bootstrap の公開 API

初期実装では、以下の API を提供する。

| API | 役割 |
|---|---|
| `register_standard_providers(overwrite: bool = False) -> None` | 標準 provider adapter を registry に登録する |
| `reload_standard_providers() -> None` | snapshot を取得し、標準 provider を再登録する |
| `get_standard_provider_keys() -> list[str]` | 標準 provider key 一覧を返す |

---

## 標準 provider

初期実装で登録対象とする provider は以下である。

| provider key | adapter callable |
|---|---|
| `openai` | `ai.openai.openai_api.call_openai_chat` |
| `gemini` | `ai.gemini.gemini_api.call_gemini_chat` |
| `claude` | `ai.claude.claude_api.call_claude_chat` |

adapter callable は、`common/chat/provider_registry.py` の ChatProviderAdapter 形に合致している必要がある。

---

## 登録順序

標準 provider の登録順序は以下とする。

1. OpenAI
2. Gemini
3. Claude

登録順序は表示順やデバッグ出力の安定性のために固定する。

登録順序に意味的優先順位を持たせてはならない。

---

## 起動時登録

アプリケーション起動時に、起動処理は `register_standard_providers()` を呼び出す。

この処理は、チャット受付開始前に完了することが望ましい。

起動時登録は API キーを必要としない。

起動時登録は外部 API を呼び出してはならない。

---

## reload 処理

`reload_standard_providers()` は、以下の手順で実行する。

1. 現在の registry 状態を snapshot する
2. registry を clear する
3. `register_standard_providers(overwrite=True)` を実行する
4. 標準 provider が全て登録されたことを検証する
5. 成功時は新状態を採用する
6. 失敗時は snapshot から復元する

reload 失敗時に registry を空または部分登録状態のまま残してはならない。

---

## エラー処理

### adapter import 失敗

標準 provider adapter の import に失敗した場合、bootstrap は例外を送出する。

起動処理はこの例外を捕捉し、起動継続可否を判断する。

### adapter 形不一致

adapter callable が callable でない場合、registry 登録時に拒否される。

bootstrap はこの失敗を握りつぶしてはならない。

### 部分登録失敗

一部 provider の登録だけが成功した状態は許容しない。

reload 時は snapshot へ復元する。

起動時は、登録失敗を明示的にログへ記録する。

---

## UI 層との関係

UI 層は、bootstrap の実行タイミングを決めることができる。

ただし、UI 層は provider adapter の中身を知ってはならない。

UI 層は provider key 一覧を表示用途に利用できるが、adapter callable を直接呼び出してはならない。

---

## テスト方針

adapter bootstrap には、少なくとも以下のテスト観点が必要である。

| テスト番号 | 観点 |
|---|---|
| BOOTSTRAP-T01 | 標準 provider を登録できる |
| BOOTSTRAP-T02 | 標準 provider key 一覧が固定順で取得できる |
| BOOTSTRAP-T03 | reload 成功時に registry が再構成される |
| BOOTSTRAP-T04 | reload 失敗時に snapshot へ復元される |
| BOOTSTRAP-T05 | bootstrap が API キーを要求しない |
| BOOTSTRAP-T06 | bootstrap が外部 API を呼び出さない |
| BOOTSTRAP-T07 | `common/chat` から bootstrap を import していない |

---

## 実装順序

実装は以下の順序で行う。

1. `common/chat/provider_registry.py` を実装する
2. provider registry の単体テストを実装する
3. `ai/provider_bootstrap.py` を実装する
4. adapter bootstrap の単体テストを実装する
5. 起動処理に bootstrap 呼び出しを追加する
6. `chat_loop.py` を registry 参照へ切り替える
7. `common/chat` から AI 層直接 import がないことを静的検査する

---

## 採用判断

本設計を採用することで、AI provider adapter の登録責務は AI 層側に集約される。

これにより、`common/chat` は AI 層の具体構造を知らずに provider 呼び出しを実行できる。

---

[目次](../../目次.md) > 仕様 > コア仕様 > adapter_bootstrap詳細設計
