# AIChaBo v0.9 — Release Notes

_Release date: 2025-09-15 (JST)_

**対象ブランチ:** `main`

本リリースは、Discord 上でのあいちゃぼ（AIChaBo）の“現時点で稼働している機能”のみを簡潔にまとめたものです。細かな履歴や実装詳細は含めません。

## 1. 概要（動作中の機能）
- **マルチプロバイダ対応のチャット**：OpenAI / Gemini / Claude を利用した会話が可能（ユーザー自身の API キーを使用）。
- **認証情報テンプレートの配布と登録**：`/ac_template` で JSONC テンプレート取得、`/ac_auth` で登録。サーバー単位の **共有/解除**（`/ac_authsharing`, `/ac_authunsharing`）に対応。
- **スレッド/会話管理**：新規チャット作成（`/ac_newchat`）、スレッド一覧（`/ac_threads`）、招待/退出（`/ac_invite`, `/ac_leave`）、トピック開始・要約（`/ac_newtopic`, `/ac_summary`）。
- **ステータス/運用**：`/ac_status` により状態表示・各種オプション（プロンプト/インテント再読込、ログ出力切替、ツールトレース など）が利用可能。

## 2. 利用可能な /コマンド（抜粋・稼働確認済み）
- 基本: `/ac_help`, `/ac_template`, `/ac_auth [file]`, `/ac_removeauth`
- 認証共有: `/ac_authsharing`, `/ac_authunsharing`
- 状態表示: `/ac_status [option]`（`-loadprompt`, `-loadintent`, `-printmsg:on/off`, `-exp`, `-expall`, `-expprompt`, `-expintent`, `-expmsg:on/off`, `-showopt`, `-tracetool:on/off`）
- スレッド: `/ac_threads`, `/ac_newchat [title] [Private]`
- スレッド内: `/ac_invite`, `/ac_leave`, `/ac_newtopic`, `/ac_summary`

## 3. 運用メモ
- **systemd サービス起動サンプル**を同梱（README 記載）。Ubuntu でのデプロイ/更新手順も記載済み。

---

※ 本ノートは `main` ブランチ（2025-09-15 時点）の実装とコマンド仕様に基づきます。