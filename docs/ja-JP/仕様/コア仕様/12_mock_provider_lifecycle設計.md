<!--
HLDocS:LLM-MANAGED
doc_id: doc-20260513-113500Z-MOCKPROVLIFE
lang: ja-JP
canonical_title: mock_provider_lifecycle設計
document_type: spec
canonical_document: true
transport: [ui_copy]
-->

[目次](../../目次.md) > 仕様 > コア仕様 > mock_provider_lifecycle設計

# mock_provider_lifecycle設計

## Purpose（存在理由）

本書は、AIChaBo の Provider Adapter Registry 導入後における mock provider の lifecycle を定義する。

mock provider は、外部 AI API を呼び出さずにチャットループ、provider 解決、エラー経路、redact 処理をテストするために使用する。

---

## Non-goals（対象外）

本書は以下を対象外とする。

- mock 応答内容の詳細な品質評価
- OpenAI / Gemini / Claude API の疑似完全再現
- Discord UI の E2E テスト
- 外部 Web API の mock
- 画像認識・画像生成 adapter の mock 詳細

---

## 基本方針

mock provider は、Provider Adapter Registry 経由で登録する。

テスト時に AI 層の実 provider callable を直接 monkeypatch することは、段階的に減らす。

既存の `AIChaBo_TEST_MOCK` 環境変数による mock は互換目的で残してよいが、今後の新規テストでは registry-based mock を優先する。

---

## mock provider の責務

mock provider は、以下の責務を持つ。

- 外部 API を呼ばずに deterministic な応答を返す
- provider key ごとの呼び出し経路を検証可能にする
- adapter 呼び出し失敗を再現できる
- 機密情報混入テストを再現できる
- continuation や tool request の将来拡張に対応できる余地を持つ

mock provider は、UI 層に依存してはならない。

mock provider は、実 API キーを必要としてはならない。

---

## mock provider の配置

初期設計では、mock provider は tests 配下に置く。

```text
tests/mocks/mock_provider_adapter.py
```

本番コード配下に mock provider を置かない。

ただし、テスト支援用の registry 操作 API は `common/chat/provider_registry.py` に含める。

---

## mock 登録 lifecycle

テスト時の mock 登録は以下の手順で行う。

1. registry 状態を snapshot する
2. registry を clear する、または対象 provider のみ overwrite する
3. mock provider adapter を登録する
4. テストを実行する
5. finally 相当の処理で snapshot へ復元する

テスト失敗時でも registry 状態を復元しなければならない。

---

## mock adapter 種別

初期実装では、以下の mock adapter を用意する。

| 種別 | 目的 |
|---|---|
| success mock | 正常応答を返す |
| error mock | 例外を送出する |
| secret leak mock | 例外文に疑似 API キーを含める |
| empty response mock | 空応答を返す |
| type mismatch mock | 文字列以外を返す |

---

## 既存 AIChaBo_TEST_MOCK との関係

現行 provider callable には `AIChaBo_TEST_MOCK` による mock 経路が存在する。

Provider Adapter Registry 導入後は、mock の主経路を registry-based mock へ移行する。

`AIChaBo_TEST_MOCK` は以下の扱いとする。

- 既存テスト互換のため当面維持する
- 新規テストでは原則使用しない
- 将来的に削除または縮小する場合は、別途移行判断を行う

---

## テスト隔離

mock provider を使うテストは、他テストへ registry 状態を漏洩させてはならない。

そのため、テストヘルパーは以下を保証する。

- テスト開始時に registry 状態を退避する
- テスト終了時に registry 状態を復元する
- テスト中に登録した mock provider が残らない
- 並列テスト時の状態競合を避ける

並列テストに対応する場合は、registry の共有状態を扱うテストを直列実行対象として分類する。

---

## セキュリティテスト

secret leak mock は、疑似 API キーを含む例外を発生させる。

この mock により、以下を検証する。

- UI 応答に疑似 API キーが含まれない
- ログ出力に疑似 API キーが含まれない
- redact 処理が adapter エラー経路にも適用される

テストに使用する疑似 API キーは、実在する API キー形式と紛らわしくない固定文字列とする。

---

## chat_loop テストとの関係

chat_loop の provider 呼び出しテストでは、実 provider ではなく mock provider を registry に登録する。

これにより、以下を保証する。

- 外部 API 非依存
- テスト結果の決定性
- 認証解決後の adapter 呼び出し経路の検証
- 未登録 provider エラーの検証
- adapter 失敗時の安全終了の検証

---

## 実装前チェック

実装前に以下を確認する。

- registry に snapshot / restore が存在する
- mock adapter 登録に overwrite が使える
- テスト後の復元が必ず行われる
- 既存 `AIChaBo_TEST_MOCK` テストとの衝突がない
- mock provider が本番コードから参照されない

---

## 完了条件

mock provider lifecycle は、以下を満たした時点で成立する。

- registry-based mock により provider 呼び出し経路をテストできる
- 外部 AI API を呼ばずに chat_loop テストが成立する
- adapter 例外経路を再現できる
- 機密情報 redact 経路を再現できる
- テスト後に registry 状態が復元される

---

[目次](../../目次.md) > 仕様 > コア仕様 > mock_provider_lifecycle設計
