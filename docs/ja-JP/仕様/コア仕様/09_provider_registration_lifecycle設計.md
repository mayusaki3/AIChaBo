<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-110500Z-PROVREGLIFE
lang: ja-JP
canonical_title: provider_registration_lifecycle設計
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > provider_registration_lifecycle設計

# provider_registration_lifecycle設計

## Purpose（存在理由）

本書は、AIChaBo における provider adapter の登録、初期化、差し替え、再読み込みの lifecycle を定義する。

Provider Adapter Registry は、`common/chat` と AI プロバイダ層を分離するための境界である。

そのため、registry へ adapter をいつ、どこで、どの責務により登録するかを明確化する必要がある。

---

## Non-goals（対象外）

本書は以下を対象外とする。

- provider_registry.py の詳細 API 定義
- OpenAI / Gemini / Claude の個別 adapter 実装
- Discord 起動処理の詳細
- 外部連携プラグインの lifecycle
- 認証情報の登録・共有・削除手順

---

## 基本方針

provider adapter 登録は、チャット実行時ではなく、起動時または明示的 reload 時に行う。

`chat_loop.py` は provider adapter を自動 import / 自動登録してはならない。

adapter 登録責務は、以下のいずれかに集約する。

- AI 層が提供する bootstrap 関数
- アプリケーション起動処理
- テスト初期化処理

---

## lifecycle 状態

Provider Adapter Registry は、以下の状態を持つ。

| 状態 | 意味 |
|---|---|
| 未初期化 | registry に adapter が登録されていない |
| 初期化済み | 標準 provider adapter が登録されている |
| テスト差し替え中 | mock adapter 等により一部または全部が差し替えられている |
| reload 中 | registry を再構成している |
| 異常 | 登録失敗または不整合が検出された |

---

## 標準初期化フロー

標準初期化は、アプリケーション起動時に 1 回実行される。

```text
起動処理
  ↓
AI provider bootstrap 呼び出し
  ↓
OpenAI adapter 登録
Gemini adapter 登録
Claude adapter 登録
  ↓
registry 初期化完了
  ↓
チャット受付開始
```

チャット受付開始前に registry 初期化が完了していることが望ましい。

ただし、初期化未完了でもプロセス全体を停止させるかどうかは、運用方針として別途判断する。

---

## bootstrap 責務

bootstrap は、AI provider adapter の登録だけを行う。

bootstrap は以下を行ってはならない。

- API キーの取得
- ユーザー認証情報の検証
- 実際の AI API 呼び出し
- UI 層へのメッセージ送信
- Discord 型への依存

bootstrap は、provider callable を registry に登録するだけである。

---

## 推奨 bootstrap 配置

初期設計では、以下の配置を推奨する。

```text
ai/provider_bootstrap.py
```

このファイルは AI 層側に属し、`common/chat/provider_registry.py` を import して標準 provider を登録する。

依存方向は以下となる。

```text
起動処理
  ↓
ai/provider_bootstrap.py
  ↓
common/chat/provider_registry.py
```

この依存は、AI 層が common の registry API を利用する方向であり、common が AI 層を知る方向ではないため許容する。

---

## reload フロー

reload は、adapter 登録状態を再構成する明示操作である。

reload は以下の順で行う。

1. 現在の registry 状態を snapshot する
2. registry を clear する
3. 標準 provider adapter を再登録する
4. 登録結果を検証する
5. 成功時は新 registry を採用する
6. 失敗時は snapshot から復元する

reload 失敗時に registry が空または部分登録状態のまま残ってはならない。

---

## テスト差し替え lifecycle

テストでは、外部 API を呼ばない mock adapter を登録できなければならない。

推奨手順は以下である。

1. `snapshot_providers()` で現状態を退避する
2. `clear_providers()` または `overwrite=True` で mock adapter を登録する
3. テストを実行する
4. `restore_providers(snapshot)` で元の状態へ戻す

テストが失敗した場合でも、finally 相当の処理で registry 状態を復元する。

---

## チャット実行時の扱い

チャット実行時に provider が未登録だった場合、`chat_loop.py` は provider 未登録エラーとして扱う。

この時、`chat_loop.py` はその場で AI 層を import して自動登録を試みてはならない。

理由は、チャット実行責務と初期化責務が混在するためである。

---

## エラー処理

### 起動時登録失敗

起動時に標準 provider adapter 登録へ失敗した場合、ログに記録する。

起動を継続するか停止するかは運用設定で判断できる余地を残す。

ただし、未登録 provider がある状態では、該当 provider のチャット実行は失敗する。

### reload 失敗

reload 失敗時は、直前の snapshot へ復元する。

復元にも失敗した場合は、registry を異常状態として扱い、チャット実行を安全側で拒否する。

### テスト差し替え失敗

テスト差し替え失敗時は、テストを失敗させる。

本番 registry 状態へ影響を残してはならない。

---

## セキュリティ

provider registration lifecycle は API キーを扱わない。

registry に登録されるのは adapter callable であり、認証情報ではない。

API キーは、チャット実行時に SecretStore から解決され、adapter 呼び出し引数としてのみ渡される。

---

## 実装前チェック

実装前に以下を確認する。

- registry API が provider_registration_lifecycle を満たす
- bootstrap の配置が AI 層側である
- 起動処理から bootstrap を呼ぶ位置が明確である
- reload 失敗時の復元方針が定義されている
- テスト差し替え時の復元方針が定義されている

---

## 次作業

本設計の次作業は以下である。

1. adapter bootstrap 設計を詳細化する
2. OpenAI / Gemini / Claude adapter 移行方針を整理する
3. registry 単体テストを作成する
4. provider bootstrap テストを作成する
5. `chat_loop.py` の provider 解決経路を registry へ切り替える

---

[目次](../../目次.md) > 仕様 > コア仕様 > provider_registration_lifecycle設計
