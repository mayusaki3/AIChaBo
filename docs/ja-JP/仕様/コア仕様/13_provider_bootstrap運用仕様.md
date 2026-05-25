<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260525-131500Z-PROVBOOTOPS
lang: ja-JP
canonical_title: provider_bootstrap運用仕様
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > provider_bootstrap運用仕様

# provider_bootstrap運用仕様

## Purpose（存在理由）

本書は、Provider Adapter Registry 導入後における provider bootstrap の運用仕様を定義する。

本仕様により、AIChaBo の起動時に provider adapter を registry へ登録し、common/chat 層から AI provider 実装への直接依存を除去する。

---

## 基本方針

provider adapter の登録責務は bootstrap 層へ集約する。

common/chat は以下を知らない。

- ai/{provider} のディレクトリ構造
- call_{provider}_chat 命名規約
- importlib による動的 import
- provider 実装配置

common/chat は Provider Adapter Registry のみを利用する。

---

## bootstrap 実行タイミング

Provider bootstrap は、Bot 起動初期化時に一度だけ実行する。

推奨順序:

1. logger 初期化
2. config/environment 初期化
3. provider bootstrap 実行
4. Discord/UI handler 初期化
5. Bot 起動

---

## bootstrap 責務

provider bootstrap は以下を担当する。

- 標準 provider adapter 登録
- registry reload
- provider 一覧検証
- registry 初期化失敗時の rollback

provider bootstrap は以下を担当しない。

- API キー検証
- 外部 API 疎通確認
- モデル利用可否確認
- UI 初期化
- セッション初期化

---

## 標準 provider

初期構成では以下を標準 provider とする。

| provider | adapter |
|---|---|
| openai | call_openai_chat |
| gemini | call_gemini_chat |
| claude | call_claude_chat |

---

## 起動失敗時の扱い

provider bootstrap に失敗した場合、Bot は unsafe 状態で継続起動してはならない。

推奨動作:

- エラーログ出力
- registry rollback
- 起動停止
- 非0終了コード

---

## reload 運用

reload_standard_providers は以下用途で使用する。

- 開発時 hot reload
- provider adapter 差し替え
- registry リセット
- integration test 初期化

本番通常運用では頻繁に reload しない。

---

## mock provider 運用

テスト時は registry-based mock provider を使用する。

本番 bootstrap では mock provider を登録してはならない。

mock provider は tests 配下からのみ利用する。

---

## CI 検証

CI では以下を継続検査する。

- provider registry tests
- bootstrap tests
- static import boundary tests
- registry-based mock tests

CI 失敗時は provider 境界破壊として扱う。

---

## 完了条件

provider bootstrap 運用は、以下を満たした時点で成立する。

- 起動時に provider adapter が registry へ登録される
- common/chat が ai.* を直接 import しない
- chat_loop が registry 経由で provider 解決する
- bootstrap failure 時に rollback できる
- CI で責務境界を継続検査できる

---

[目次](../../目次.md) > 仕様 > コア仕様 > provider_bootstrap運用仕様
