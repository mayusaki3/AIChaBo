<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-112500Z-PROVADAPTERMIG
lang: ja-JP
canonical_title: provider_adapter移行設計
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > provider_adapter移行設計

# provider_adapter移行設計

## Purpose（存在理由）

本書は、OpenAI / Gemini / Claude の既存チャット呼び出し実装を Provider Adapter Registry 経由へ移行するための設計を定義する。

本設計は、既存の AI provider 実装を大きく変更せず、`common/chat/chat_loop.py` から AI 層への直接 import を除去することを目的とする。

---

## Non-goals（対象外）

本書は以下を対象外とする。

- 各 provider API payload の全面再設計
- 画像認識 adapter の registry 化
- 画像生成 adapter の registry 化
- tool request の構造化戻り値対応
- UI 層の変更
- 認証情報テンプレート仕様の変更

---

## 現行 provider 実装

現行 develop では、以下のチャット callable が存在する。

| provider key | 現行 callable |
|---|---|
| `openai` | `ai.openai.openai_api.call_openai_chat` |
| `gemini` | `ai.gemini.gemini_api.call_gemini_chat` |
| `claude` | `ai.claude.claude_api.call_claude_chat` |

これらは、初期 Provider Adapter Registry の `ChatProviderAdapter` として登録可能な形に近い。

---

## 移行方針

初期移行では、既存 callable をそのまま adapter として登録する。

```text
register_provider("openai", call_openai_chat)
register_provider("gemini", call_gemini_chat)
register_provider("claude", call_claude_chat)
```

この段階では、新しい adapter class は作らない。

理由は、責務境界の移行を優先し、provider API 実装の全面変更を避けるためである。

---

## 入力互換

既存 callable は以下の入力を受け取る。

```text
context_list: list[str]
api_key: str
model: str
max_tokens: int
```

Provider Adapter Registry の初期 adapter 形もこれに合わせる。

`chat_loop.py` から渡す `extra` は、既存 callable が受け取れる範囲に制限する。

未知の option を無制限に渡す場合は、provider callable 側で `**kwargs` 非対応のためエラーになる可能性がある。

そのため、初期移行では `max_tokens` を中心に互換 option のみに限定する。

---

## provider 別注意点

### OpenAI

OpenAI は `gpt-5` / `o1` / `o3` / `o4` 系で `max_completion_tokens` を使用する必要がある。

この差異は `ai.openai.openai_api.call_openai_chat` 側で吸収済みである。

Provider Adapter Registry は、この差異を知ってはならない。

### Gemini

Gemini は REST API の `generationConfig.maxOutputTokens` へ変換する。

この差異は `ai.gemini.gemini_api.call_gemini_chat` 側で吸収する。

Provider Adapter Registry は、この差異を知ってはならない。

### Claude

Claude は Anthropic Messages API の `max_tokens` を使用する。

この差異は `ai.claude.claude_api.call_claude_chat` 側で吸収する。

Provider Adapter Registry は、この差異を知ってはならない。

---

## mock 対応

現行 provider callable には `AIChaBo_TEST_MOCK` による mock 経路が存在する。

ただし、Provider Adapter Registry 導入後は、registry 差し替えによる mock adapter 登録を主とする。

`AIChaBo_TEST_MOCK` は互換目的で残してよいが、将来的には registry-based mock へ移行する。

---

## 移行手順

移行は以下の順で行う。

1. `common/chat/provider_registry.py` を追加する
2. registry 単体テストを追加する
3. `ai/provider_bootstrap.py` を追加する
4. `call_openai_chat` / `call_gemini_chat` / `call_claude_chat` を登録する
5. bootstrap 単体テストを追加する
6. 起動処理から bootstrap を呼ぶ
7. `chat_loop.py` の provider 解決を registry 参照へ変更する
8. `common/chat` から `ai.` 直接 import がないことを静的検査する

---

## 互換性

本移行では、既存の認証テンプレート、provider 名、model 名、ユーザー操作を変更しない。

`/ac_auth`、認証共有、通常チャットの利用者向け挙動は維持する。

変更対象は、内部の provider 解決経路のみである。

---

## リスク

### bootstrap 未実行

起動処理が bootstrap を呼び忘れた場合、全 provider が未登録となり、チャット実行が失敗する。

対策として、起動時ログに登録済み provider 一覧を出力する。

### option 不一致

`chat_loop.py` から provider callable へ未知の option を渡すと TypeError になる可能性がある。

対策として、初期移行では provider callable に渡す option を明示的に制限する。

### mock 経路の二重化

環境変数 mock と registry mock が共存するため、テスト方針が一時的に二重化する。

対策として、今後のテストでは registry mock を優先する。

---

## 完了条件

本移行は、以下を満たした時点で完了とする。

- `chat_loop.py` が `ai.{provider}` を import しない
- `chat_loop.py` が `call_{provider}_chat` 命名規約を知らない
- 標準 provider が bootstrap で登録される
- registry mock adapter によるテストが可能である
- OpenAI / Gemini / Claude の通常チャットが従来どおり動作する

---

[目次](../../目次.md) > 仕様 > コア仕様 > provider_adapter移行設計
