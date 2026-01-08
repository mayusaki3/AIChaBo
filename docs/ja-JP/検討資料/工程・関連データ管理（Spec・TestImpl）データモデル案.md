目次 > AIChaBo > アーキテクチャ > 工程・関連データ管理（Spec/Test/Impl）データモデル案

# 工程・関連データ管理（Spec/Test/Impl）データモデル案

## 1. 目的
- 各工程（要件→仕様→テスト仕様→実装→検証→適用）の「状況」を一元管理する。
- 仕様↔テスト仕様↔実装 など、ファイル間の関連（トレーサビリティ）と、チェック状況（ゲートのPASS/FAIL）を管理する。
- 参照・更新は「ユーザー（Discordコマンド）」と「AIChaBo（自動ジョブ）」の双方から行われる。

## 2. 前提・スコープ
- 生成物の実体はリポジトリ上のファイル（docs, tests, src 等）として管理する。
- 本仕組みは “中央のメタデータ（管理情報）” を持ち、生成物ファイルそのものを置き換えない。
- ローカルエージェント方式の場合でも、メタデータの正は中央（Bot側）に置く（参照・更新はAgent経由）。

## 3. 管理対象（エンティティ）
- WorkItem（作業単位）：機能追加、バグ修正、リファクタなどの単位
- Artifact（成果物）：仕様・テスト仕様・実装・その他（設定、スクリプト等）
- Link（関連）：Artifact間の参照関係（spec→test、test→impl、spec→impl 等）
- Check（チェック結果）：lint/test/整合チェック/トレーサビリティチェック等の結果
- JobRun（実行履歴）：あいちゃぼが実行した一連の工程の実行記録
- Gate（品質ゲート定義）：必須チェックの集合、閾値、適用範囲

## 4. 最小データモデル（MVP）
### 4.1 WorkItem
- work_item_id: string（例: WI-2026-0001）
- title: string
- repo: string（リポジトリ識別子）
- branch: string（作業ブランチ）
- base_commit: string（開始時点）
- status: enum
  - draft / spec_ready / test_ready / impl_ready / verified / merged / closed
- owners: array（Discord user_id）
- labels: array（feature, bug, refactor 等）
- created_at / updated_at

### 4.2 Artifact
- artifact_id: string
- work_item_id: string
- type: enum（spec / test_spec / impl / other）
- path: string（repo内相対パス）
- target_commit: string（その成果物を評価したcommit）
- hash: string（内容hash: 任意だが推奨）
- status: enum
  - planned / generated / reviewed / applied / deprecated
- meta:
  - language（doc: ja-JP 等, code: ts/java/py 等）
  - tags（API名、モジュール名など）

### 4.3 Link（トレーサビリティ）
- link_id: string
- work_item_id: string
- from_artifact_id: string
- to_artifact_id: string
- relation: enum
  - spec_covers_test
  - test_verifies_spec
  - impl_implements_spec
  - test_targets_impl
  - replaces（差し替え）
- evidence:
  - ref_anchor（specの見出しID、テストID、クラス/関数名など）
  - note（補足）

### 4.4 Check（チェック結果）
- check_id: string
- work_item_id: string
- scope: enum（repo / module / artifact / link）
- target:
  - artifact_id（任意）
  - path（任意）
- kind: enum
  - lint
  - unit_test
  - integration_test
  - doc_consistency
  - traceability
  - security_scan
- status: enum（pass / fail / skipped / not_run）
- summary: string（短い要約）
- details_ref: string（ログ保存先、または添付ID）
- measured_at: datetime
- runner:
  - agent_id（ローカル実行の場合）
  - env_fingerprint（OS/Node/Java/Python版など）

### 4.5 JobRun（工程実行履歴）
- job_id: string
- work_item_id: string
- requested_by: Discord user_id
- mode: enum（plan / apply）
- pipeline: string（例: spec→test→impl→verify）
- steps:
  - step_name
  - status（pass/fail/skipped）
  - started_at / ended_at
  - outputs（生成artifact_id、ログ参照）
- created_at

## 5. Gate（品質ゲート）モデル
- gate_id: string（例: GATE-DEFAULT）
- applies_to: filter
  - repo / module / artifact_type / label
- required_checks: array
  - { kind, scope, threshold? }
- policy:
  - “spec変更があるなら traceability を必須”
  - “impl変更があるなら unit_test を必須”
  - “test_spec変更があるなら doc_consistency を必須”
- result: computed（現在のwork_itemに対して PASS/FAIL）

## 6. 参照・更新の操作I/F（ユーザー/AIChaBo共通）
### 6.1 参照（read）
- WorkItemの状態表示（工程の進捗、未完了チェック）
- Artifact一覧（spec/test/implのリンク関係）
- Gate結果（何がPASS/FAILか、未実行が何か）
- JobRun履歴（いつ誰が何を実行し、何が出たか）

### 6.2 更新（write）
- WorkItem作成/状態遷移（draft→spec_ready 等）
- Artifact登録（生成物のpath、commit、hash）
- Link登録（spec見出し↔テストIDなど）
- Check登録（実行結果）
- Gate定義の更新（Admin限定）

## 7. 実装選択肢（保存方式）
### 7.1 リポジトリ内ファイル（推奨：MVP）
- `docs/_meta/work_items/*.json`
- `docs/_meta/artifacts/*.json`
- `docs/_meta/links/*.json`
- `docs/_meta/checks/*.jsonl`
- `docs/_meta/gates/*.json`
利点：
- PRでレビュー可能（メタデータも履歴管理）
- “仕様↔テスト↔実装”の変化と同じリズムで更新できる
注意：
- 競合（同時編集）対策が必要（work_item単位ファイルで分割）

### 7.2 中央ストア（DB/Key-Value）
利点：
- 高速検索、同時更新に強い
注意：
- PRレビューから外れる（監査・運用が別物になる）
- まずはMVPで不要な場合が多い

## 8. ローカルエージェント方式との整合
- Agentは “成果物ファイル” を生成/更新するが、
  - メタデータ更新は「差分（Plan）」を中央へ提示し、
  - 「Apply」でメタデータを確定更新する流れが安全。
- Checkには `env_fingerprint` を必須にし、環境差の影響を見える化する。

## 9. 破綻しやすいポイントと対策
- リンクが更新されない（specだけ変わる等）
  - Gateで “変更種別に応じた必須チェック” を強制
- テストが増えるほど意図が不明になる
  - Link.evidence（spec見出し、テストID）を必須化
- ローカル環境差で通らない
  - env_fingerprint と再現ガイド（JobRun outputs）を必須化

## 10. 最小コマンド案（例）
- /ac_wi_new title repo branch
- /ac_wi_show WI-...
- /ac_wi_link add <spec_path#anchor> <test_id>
- /ac_wi_check record <kind> <pass/fail> <log_ref>
- /ac_wi_gate show WI-...
- /ac_wi_plan pipeline:spec→test→impl
- /ac_wi_apply job_id

---
目次 > AIChaBo > アーキテクチャ > 工程・関連データ管理（Spec/Test/Impl）データモデル案
