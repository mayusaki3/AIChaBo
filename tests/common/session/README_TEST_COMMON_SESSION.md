目次 > テスト仕様 > common > session

COMMON / SESSION テスト仕様

本ドキュメントは common/session 配下のセッション関連モジュールについて、
仕様テスト と 実装（カバレッジ）テスト の構成および対応関係を明示する。

テスト対象モジュール

ID	モジュール
T01	user_session_manager.py
T02	server_session_manager.py
T03	thread_context_manager.py

テスト構成方針

2.1 仕様テスト（Spec）

・外部仕様として保証すべき振る舞いを検証する
・将来のリファクタリングでも維持される前提とする
・仕様書（02_スレッド・セッション仕様.md）と対応付けられる

2.2 実装テスト（impl）

・内部実装に依存する分岐・例外経路を通すことを目的とする
・カバレッジ 100% 達成のための補完テスト
・仕様変更時に削除・変更される可能性がある

テストスイート一覧

T01 : UserSessionManager

【仕様テスト】

Suite	ファイル	内容
T01-01	T01_user_session_01_user_session_test.py	ユーザーセッションの基本仕様

・guard(None)
・未登録ユーザー取得
・set / get（api_key を保持しない）
・clear_session
・起動時ロード例外からの復旧
・provider / model 必須検証

【実装テスト（カバレッジ）】

Suite	ファイル	目的
T01-02 (impl)	T01_user_session_02impl_user_session_test.py	内部分岐補完

・has_session True / False
・clear_session no-op
・get_session が deepcopy を返すこと

T02 : ServerSessionManager

【仕様テスト】

Suite	ファイル	内容
T02-01	T02_server_session_01_server_session_test.py	サーバー共有設定・オプション仕様

・guard(None)
・未登録 server_id
・shared auth set / get / clear
・api_key 再帰除去
・provider / model 正規化
・option set / get / clear / all

【実装テスト（カバレッジ）】

Suite	ファイル	目的
T02-02 (impl)	T02_server_session_02impl_server_session_test.py	init / clear_option 分岐網羅

・PATH exists == False
・read 例外からの復旧
・sid / key 未登録分岐
・bucket 空 / 非空分岐

T03 : ThreadContextManager

【仕様テスト】

Suite	ファイル	内容
T03-01	T03_thread_context_01_thread_context_test.py	スレッド文脈管理仕様

・get_context 初期値
・append_context（添付有無）
・clear_context / has_context
・injection_message 生成
・JSON 変換保証
・export_context
・meta 操作一式

【実装テスト（カバレッジ）】

Suite	ファイル	目的
T03-02 (impl)	T03_thread_context_02impl_thread_context_test.py	内部分岐補完

・append_context 初期化分岐
・tone_prompt 空分岐
・export_all 例外握りつぶし
・clear_meta 分岐

実行方法

以下は説明用の記述であり、コードブロックは使用しない。

common/session 全体
tests\test_all.ps1 tests.common.session

個別実行
tests\test_all.ps1 tests.common.session.T01
tests\test_all.ps1 tests.common.session.T02
tests\test_all.ps1 tests.common.session.T03

完了条件

・仕様テスト：全 PASS
・実装テスト：全 PASS
・common/session 配下の全モジュールが Coverage 100%

現状、T01 / T02 / T03 のすべてが上記条件を満たしている。

目次 > テスト仕様 > common > session
