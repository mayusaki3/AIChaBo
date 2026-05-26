# AIChaBo（AIChaBo/あいちゃぼ） 

AIChaBo（あいちゃぼ）は、ユーザーが発行した API キーを使って Discord 上で LLM ( ChatGPT / Gemini / Claude ) を利用できる Bot です。  
構成は「UI層」「AI層」「共通層」に分かれており、将来的な多プラットフォーム対応を想定しています。（対応するとは言っていない）  

利用者の認証情報に API キー を設定する仕組みのため、LLMの利用料は利用者が負担する形になります。  
サーバー単位で利用者の認証情報を共有することもでき、その場合は共有元の利用者が利用料を負担することになります。  
使用される認証情報は、利用者が設定した認証情報＞共有された認証情報 となっています。  
API キー は暗号化して保管しています。（Fernetを利用）

## ドキュメント（整理中）
- [目次](./docs/ja-JP/目次.md)

## Provider Adapter Registry（develop）

develop ブランチでは、AI provider 呼び出し境界を `Provider Adapter Registry` に集約しています。

### 目的

- `common/chat` から `ai/*` 直接依存を除去
- provider adapter の動的差し替え
- registry-based mock test
- plugin/provider 拡張の準備
- UI層 / AI層 / 共通層 の責務分離強化

### 構成

```text
UI Layer
  ↓
common/chat/chat_loop.py
  ↓
common/chat/provider_registry.py
  ↑
ai/provider_bootstrap.py
  ↑
ai/openai
ai/gemini
ai/claude
```

### CI

以下の GitHub Actions により、provider 境界を継続検査しています。

```text
.github/workflows/provider-registry-tests.yml
```

検査対象:

- provider registry tests
- bootstrap tests
- static import boundary tests
- registry-based mock tests

### 設計仕様

詳細仕様は以下を参照してください。

- `docs/ja-JP/仕様/コア仕様/06_provider_adapter_registry仕様.md`
- `docs/ja-JP/仕様/コア仕様/07_chat_loop依存逆転設計.md`
- `docs/ja-JP/仕様/コア仕様/08_provider_registry詳細設計.md`
- `docs/ja-JP/仕様/コア仕様/09_provider_registration_lifecycle設計.md`
- `docs/ja-JP/仕様/コア仕様/10_adapter_bootstrap詳細設計.md`
- `docs/ja-JP/仕様/コア仕様/11_provider_adapter移行設計.md`
- `docs/ja-JP/仕様/コア仕様/12_mock_provider_lifecycle設計.md`
- `docs/ja-JP/仕様/コア仕様/13_provider_bootstrap運用仕様.md`


## 環境変数の設定（Discord用）

1. `.env.example` を `.env` にコピーしてください。
2. 必要な トークン・ID を `.env` に記入してください：
    ### 🔹 Discord Bot Token の取得手順
    1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
    2. 「New Application」からアプリケーションを作成
    3. 左メニュー「Bot」→「Add Bot」でBotを追加
    4. 「Token」→「Reset Token」→ 表示されたトークンをコピー
    5. `.env` の DISCORD_BOT_TOKEN= に貼り付け  
    🔒 注意：このトークンは絶対に外部に公開しないでください。Gitに含めないよう `.gitignore` で保護します。
    
    ### 🔹 Discord Guild ID の取得手順（開発時のみ）
    1. DiscordクライアントでDiscordにアクセス
    2. ユーザー設定 → 詳細設定 → 「開発者モード」を有効化
    3. 対象のサーバー名を右クリック → 「IDをコピー」
    4. `.env` の DISCORD_GUILD_ID= に貼り付け
