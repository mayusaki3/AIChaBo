<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260525-140500Z-PROVREGMIGVAL
lang: ja-JP
canonical_title: provider_registry_migration_validation
document_type: testspec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > provider_registry_migration_validation

# provider_registry_migration_validation

## Purpose（存在理由）

本書は、Provider Adapter Registry 導入後に、AIChaBo の provider 解決経路・責務境界・起動初期化が正しく成立していることを検証する。

---

## 検証対象

| 対象 | 内容 |
|---|---|
| provider registry | provider adapter 解決 |
| bootstrap | 起動時 provider 登録 |
| chat_loop | registry 経由呼び出し |
| common/chat | AI層直接依存禁止 |
| registry-based mock | mock provider 検証 |
| CI | 継続検査 |

---

## Migration Validation Checklist

### MIGRATION-VAL-01

目的:

Provider Adapter Registry が provider adapter を登録・解決できること。

確認:

- register_provider
- resolve_provider
- overwrite
- snapshot/restore
- clear

対応:

- T09_ProviderRegistry_01_provider_registry_test

---

### MIGRATION-VAL-02

目的:

起動時に provider bootstrap が標準 provider を登録できること。

確認:

- register_standard_providers
- reload_standard_providers
- rollback
- provider list verification

対応:

- T01_ProviderBootstrap_01_provider_bootstrap_test

---

### MIGRATION-VAL-03

目的:

chat_loop が registry 経由で provider adapter を解決すること。

確認:

- importlib 未使用
- ai.* 直接 import 不使用
- resolve_provider 使用

対応:

- common/chat/chat_loop.py
- T10_StaticImportBoundary_01_common_chat_import_boundary_test

---

### MIGRATION-VAL-04

目的:

registry-based mock provider により chat_loop を外部 API 非依存で検証できること。

確認:

- success mock
- provider failure
- unregistered provider
- secret leak protection

対応:

- T11_ChatLoopMockRegistry_01_chat_loop_mock_registry_test

---

### MIGRATION-VAL-05

目的:

Discord 起動時に provider bootstrap が実行されること。

確認:

- register_standard_providers 実行
- provider 一覧表示
- bootstrap failure 停止

対応:

- ui/discord/Discord_AIChaBo.py

---

### MIGRATION-VAL-06

目的:

CI により provider 境界が継続検査されること。

確認:

- provider-registry-tests workflow
- registry tests
- bootstrap tests
- static import boundary tests
- registry-based mock tests

対応:

- .github/workflows/provider-registry-tests.yml

---

## Migration Completion Criteria

以下を満たした時点で migration 完了とする。

- common/chat が ai.* を直接 import しない
- chat_loop が registry 経由で provider 解決する
- bootstrap が起動時に provider 登録する
- registry-based mock tests が成立する
- CI で責務境界を継続検査できる
- OpenAI / Gemini / Claude 通常チャットが従来どおり動作する

---

## Future Work

今後の拡張候補:

- provider plugin interface
- image provider registry
- tool provider registry
- structured provider result
- async provider lifecycle manager
- provider capability negotiation

---

[目次](../../目次.md) > 仕様 > コア仕様 > provider_registry_migration_validation
