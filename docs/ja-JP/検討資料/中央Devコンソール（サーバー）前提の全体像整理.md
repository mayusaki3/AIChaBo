目次 > AIChaBo > アーキテクチャ > 中央Devコンソール（サーバー）前提の全体像整理

# 中央Devコンソール（サーバー）前提の全体像整理

## 1. 前提（合意事項）
- (3) あいちゃぼDevコンソールは **あいちゃぼ稼働サーバー上（中央）** に常駐する。
- (2) あいちゃぼDevTools（ローカル）は、中央からの要求に応じて
  - 情報提供（リポ状態、差分、テスト結果、環境情報など）
  - 成果物の生成/更新（ローカルworkspaceへの適用）
  - 評価（テスト/lint/整合チェックの実行）
  を行う。
- (1) Discordは、チャット/指示/承認/結果共有のUIであり、チャット内容からイシュー生成して取り込む（WorkItem化）ことを想定。

## 2. 役割分担（責務境界）
### (1) Discord（スレッド + /ac）
- 受付：会話から「作業単位（WorkItem）」の作成・更新を指示
- 承認：Plan/Apply、危険操作の承認
- 参照：進捗、ゲート結果、リンク（spec↔test↔impl）状況
- 共有：結果コメント（差分/ログ/次アクション）

### (3) Devコンソール（中央：オーケストレータ + 状態管理）
- 正（source of truth）：
  - WorkItem / Artifact / Link / Check / JobRun / Gate の管理
- 自動化：
  - Discord会話→Issue/WorkItem生成（取り込み）
  - パイプライン定義（spec→test→impl→verify）
  - 実行依頼の割当（どのDevToolsに実行させるか）
  - 結果集約と評価（PASS/FAIL、未実行チェック、整合違反検出）
- 品質保証：
  - 変更種別に応じた必須ゲート強制（例：spec変更→traceability必須）
  - 監査ログ（誰が何を要求し、どの結果だったか）

### (2) DevTools（ローカル：実行・取得）
- workspace情報の提供
  - repo/branch/commit、差分、ファイル一覧、依存バージョン、env fingerprint
- 実行
  - 生成（ローカルへのファイル作成・編集）
  - 評価（lint/test/build/整合チェック）
- 結果返却
  - ログ、差分、生成物パス、終了コード、環境fingerprint

## 3. 想定フロー（会話→Issue→実行→結果）
### 3.1 Issue/WorkItem取り込み
1) Discordスレッドで会話
2) /ac_issue_create（または自動抽出）
3) Devコンソールが WorkItem を生成
   - title / 概要 / 受け入れ条件（暫定）/ 対象repo / 優先度 / 担当候補
4) スレッドへ WorkItem ID を返信

### 3.2 Plan（生成・実行計画の作成）
1) /ac_plan WI-xxxx pipeline=spec→test→impl→verify
2) Devコンソールが必要情報をDevToolsへ要求
   - 例：現在の該当ファイル、目次、既存テスト、現状の失敗テストなど
3) DevToolsが情報返却
4) Devコンソールが
   - 生成物案（差分）
   - 実行予定（コマンド）
   - 期待結果（ゲート条件）
   をまとめて提示

### 3.3 Apply（適用・評価）
1) /ac_apply job_id
2) DevToolsへ「適用」指示（ローカルでファイル変更）
3) DevToolsが評価（lint/test等）を実行
4) 結果をDevコンソールへ返却
5) Devコンソールが Check / JobRun を確定し、Gate判定を更新
6) Discordへ結果コメント（PASS/FAIL、差分、ログ、次アクション）

## 4. “必要な情報は(2)から入手”を成立させる要件
### 4.1 情報要求の標準化（宣言的リクエスト）
- Devコンソール→DevToolsの要求は「自由文」ではなく、型付きアクションにする
  - get_repo_state / get_file / list_files / compute_diff / run_tests / apply_patch 等
- DevToolsは action ごとの許可/拒否/制約を実装（安全装置）

### 4.2 返却データの最小セット
- repo識別子、branch、HEAD commit
- env fingerprint（OS、言語ランタイム、主要ツール版）
- 生成物（差分 or パッチ）、変更ファイル一覧
- 実行ログ（短縮+フル参照）、終了コード
- 生成/評価した artifact_id との紐付け

## 5. チャット→Issue生成（自動化）での注意点
- 会話は曖昧になりやすいので、Issue化時に最低限の構造化が必要
  - 目的 / 範囲 / 受け入れ条件 / 対象repo / 影響範囲
- 受け入れ条件が曖昧な場合は、Devコンソールが “不足情報” を抽出してスレッドへ質問し、確定後に進める（勝手に進めない）

## 6. 監査・整合（中央で持つべき“管理データ”）
- WorkItemの状態遷移
- spec↔test_spec↔impl のリンク（Link）
- チェック結果（Check）とゲート判定（Gate）
- 実行履歴（JobRun）と、誰が承認したか（requested_by/approved_by）

## 7. まとめ（この前提での定義）
- 中央Devコンソールは「司令塔 + 状態の正 + 品質ゲート」。
- ローカルDevToolsは「実行者 + 情報提供者」。
- Discordは「共有UI + 指示/承認 + 結果共有」。

---
目次 > AIChaBo > アーキテクチャ > 中央Devコンソール（サーバー）前提の全体像整理
