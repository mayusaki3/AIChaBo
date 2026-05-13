<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-101500Z-AICOREBOUNDARY
lang: ja-JP
canonical_title: common責務境界 仕様-実装照合結果
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > common責務境界 仕様-実装照合結果

# common責務境界 仕様-実装照合結果

## Purpose（存在理由）

本書は、AIChaBo develop ブランチにおける `common` 配下のコア実装について、UI 層および AI プロバイダ層からの責務分離状況を照合した結果を記録する。

本書は、既存の「仕様-実装 照合チェックリスト」に基づき、現時点で確認できた適合点、要整理点、および次作業を分類するための結果文書である。

---

## Scope（対象範囲）

本書の対象は、develop ブランチ上の以下のコア領域である。

- `common/chat/*`
- `common/secret/*`
- `common/session/*`
- `common/utils/*`
- `common/plugins/*`
- `common/actions/*`

本書では、Discord 固有の UI 実装、および OpenAI / Gemini / Claude 等の AI プロバイダ実装自体は、照合対象ではなく依存先として扱う。

---

## Non-goals（対象外）

本書は以下を対象外とする。

- 実装修正そのもの
- テストケース詳細の定義
- UI 層の再設計
- AI プロバイダ層の再設計
- プラグイン仕様の完成形定義
- main ブランチへの反映判断

---

## 判定区分

本書では、照合結果を以下の区分で分類する。

| 区分 | 意味 |
|---|---|
| 適合 | 現行仕様と実装の責務境界が概ね一致している |
| 要整理 | 現時点では動作上許容できるが、将来の責務分離に向けて整理が必要 |
| 仕様不足 | 実装または設計方針に対し、仕様側の記述が不足している |
| 実装不具合 | 仕様に反する実装が確認された |
| 仕様変更要否 | 現行仕様の前提を変更するか判断が必要 |

---

## 照合結果サマリ

| 観点 | 判定 | 結果 |
|---|---|---|
| `common` から Discord への直接依存 | 適合 | 検索上、`common` から `discord` / `Interaction` / `app_commands` への直接依存は確認されなかった |
| provider 名正規化 | 適合 | `common/chat/provider.py` に集約されており、AI API 呼び出しには踏み込んでいない |
| 認証解決 | 適合 | `common/chat/auth.py` が非機密設定と秘密ストアを統合し、UI 固有処理を含まない |
| 秘密ストア | 適合 | `common/secret/store.py` が暗号化・復号・破損時復旧・削除操作を担当している |
| プラグイン dispatch | 適合 | `common/plugins/dispatcher.py` にプラグイン探索・実行入口が存在する |
| AI プロバイダ呼び出し | 要整理 | `common/chat/chat_loop.py` が `ai.{provider}.{provider}_api` の配置規約を知っている |
| provider adapter 抽象化 | 仕様不足 | provider callable の登録・解決契約が仕様として未確定 |

---

## 適合事項

### UI 層非依存

`common` 配下の主要実装から、Discord 固有型および Discord API への直接依存は確認されなかった。

これにより、現時点の `common` は、UI 層から呼び出される共通コアとして成立している。

### provider 名正規化の集約

provider 名の正規化は `common/chat/provider.py` に分離されている。

この処理は OpenAI / Gemini / Claude の実 API 呼び出しには踏み込まず、内部キーと表示名の変換に限定されている。

### 認証解決の共通化

`common/chat/auth.py` は、ユーザー設定、サーバー共有設定、秘密ストアを統合し、チャット呼び出し用の認証情報を解決する。

この責務は UI 層および AI プロバイダ層のどちらにも属さないため、`common` 配下に置く判断は妥当である。

### 秘密ストアの独立性

`common/secret/store.py` は、API キー等の機密情報を暗号化して永続化する責務に集中している。

保存先、暗号化方式、破損時復旧、削除時の安全側動作は、UI 層および AI 層から独立している。

### プラグイン dispatch の基盤

`common/plugins/dispatcher.py` は、プラグイン探索、match、plan、consume の流れを提供している。

これは将来的な外部連携、開発サポート、Web 取得拡張の基盤として妥当である。

---

## 要整理事項

### `common/chat/chat_loop.py` から AI 層配置規約が見えている

現行の `common/chat/chat_loop.py` は、provider 名から `ai.{provider}.{provider}_api` を動的 import し、`call_{provider}_chat` を探索する。

これは、現時点では実用上の中間形として許容できる。

ただし、コア責務境界の観点では、`common` が AI 層のディレクトリ構造および関数命名規約を知っている状態である。

将来的には、`common` は AI 層を直接 import せず、登録済み provider adapter または callable を呼び出す構成へ移行することが望ましい。

---

## 仕様不足事項

### provider adapter 登録契約が未定義

現時点では、AI プロバイダ呼び出しの抽象化契約が仕様として未確定である。

今後、以下のいずれかを仕様化する必要がある。

- `common/chat/provider_registry.py` による provider callable 登録方式
- `common/chat/provider_adapter.py` による adapter インターフェース方式
- AI 層側が初期化時に provider を登録する方式
- UI 層または起動処理が provider registry を構成する方式

### プラグインと provider adapter の境界が未定義

`common/plugins` は外部連携・Web 取得系の拡張基盤として存在する。

一方で、AI provider の呼び出しも広義には adapter 的な構造を必要とする。

そのため、以下の境界を仕様化する必要がある。

- AI provider adapter は `common/plugins` に含めるのか
- AI provider adapter は `common/chat` 配下の専用 registry とするのか
- 外部連携プラグインと LLM provider adapter を同一概念として扱うのか
- 両者を明確に分けるのか

---

## 実装不具合事項

現時点では、責務境界に関する明確な実装不具合は確認されていない。

ただし、`common/chat/chat_loop.py` の AI 層動的 import は、将来の分離方針に対する設計上の要整理事項である。

---

## 仕様変更要否

現行仕様では、コアが AI 層を「抽象化された provider 呼び出し」として扱うことは示されている。

しかし、その抽象化単位が callable なのか、adapter class なのか、plugin なのかは未確定である。

このため、次工程では provider 呼び出し抽象化の仕様を追加するか、既存のチャットループ仕様へ追記する必要がある。

---

## 次作業

次作業は以下の順で行う。

1. provider adapter / registry の仕様案を作成する
2. `common/chat/chat_loop.py` から AI 層 import を除去する設計を作成する
3. 既存の OpenAI / Gemini / Claude 呼び出しを adapter 化する移行案を作成する
4. testspec に provider adapter 境界テストを追加する
5. 実装変更は、仕様およびテスト方針が確定した後に行う

---

[目次](../../目次.md) > 仕様 > コア仕様 > common責務境界 仕様-実装照合結果
