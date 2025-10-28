# utiltests

Discord を介さずに **コア機能の健全性** を確認するための軽量テスト群です。  
CI で回すことを想定し、書き込みを伴うテストは **既定で skip / dry-run** になります。

## 各テストの目的と実行方法

### 1) コア・ユーティリティ
- **provider_test.py**  
    `common/chat/provider.py` の `normalize_provider` / `display_provider` の網羅テスト。

    ```shell
    python -m utiltests.provider_test
    ```

### 2) シークレットストア
- **store_test.py**  
    SecretStore の基本/並行書き込み（last-writer-wins, no corruption）。

    ```shell
    python -m utiltests.store_test
    ```

### 3) 認証フロー
- **auth_resolve_test.py**（既定 skip）  
    common/chat/auth.resolve_auth_and_key() のスケルトン。USM/SSM/Store を使用。

    ```shell
    # 有効化
    # - PowerShell
    $env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
    # - Linux/macOS (bash/zsh)
    export AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1

    python -m utiltests.auth_resolve_test

    # 無効化（既定 skip に戻す）
    # - PowerShell
    Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE
    # - Linux/macOS (bash/zsh)
    unset AIChaBo_TEST_ENABLE_AUTH_RESOLVE
    ```

- **auth_seed.py**（ユーティリティ）  
    Discord なしで USM/SSM/SecretStore にテスト認証情報を流し込み（既定 DRY-RUN、--confirm で実書き込み）。

    ```shell
    python -m utiltests.auth_seed --help
    ```

### 4) メッセージ/文脈（Discord 非依存）
- **context_test.py**（将来拡張枠）  
    message.build_context() のテスト。Discord 依存剥離後に有効化。

- **message_test.py**  
    run_once_for_test() を用いたメッセージ経路の最小確認。

    ```shell
    python -m utiltests.message_test
    ```

### 5) チャットループ
- **chat_loop_test.py**  
    common/chat/chat_loop.run() の単体テスト（スタブでも可）。

    ```shell
    python -m utiltests.chat_loop_test
    ```

### auth_seed.py
Discord なしで USM / SSM / SecretStore にテスト用の認証情報を流し込むユーティリティ。
既定は DRY-RUN。--confirm 指定時のみ書き込み。

## 注意事項

- 本番データに影響しない ように、CI 環境では SecretStore の保存先を隔離することを推奨します。
- auth_seed.py は便宜上のユーティリティであり、*本番運用では /ac_ コマンドを利用**してください。

---

このセットで「Discord 非依存の範囲」を先にテスト可能にできます。  
