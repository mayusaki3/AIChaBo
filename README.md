# AIChaBo（AIChaBo/あいちゃぼ） 

AIChaBo（あいちゃぼ）は、ユーザーが発行した API キーを使って Discord 上で LLM ( ChatGPT / Gemini / Claude ) を利用できる Bot です。  
構成は「UI層」「AI層」「共通層」に分かれており、将来的な多プラットフォーム対応を想定しています。（対応するとは言っていない）  

利用者の認証情報に API キー を設定する仕組みのため、LLMの利用料は利用者が負担する形になります。  
サーバー単位で利用者の認証情報を共有することもでき、その場合は共有元の利用者が利用料を負担することになります。  
使用される認証情報は、利用者が設定した認証情報＞共有された認証情報 となっています。  
API キー は暗号化して保管しています。（Fernetを利用）

## ドキュメント（整理中）
- [目次](./docs/ja-JP/目次.md)


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

## インストール方法（Ubuntuの場合）
```shell
sudo apt update && sudo apt upgrade -y

# Git, Python, venv 等
sudo apt install -y git python3 python3-venv python3-pip unzip

# 任意のディレクトリ作成
cd /opt
sudo mkdir AIChaBo
sudo chown $USER AIChaBo
cd AIChaBo

# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate

# AIChaBoをクローン
git clone -b main https://github.com/mayusaki3/AIChaBo.git src
cd src

# requirements.txt に応じて依存ライブラリをインストール
pip install -r requirements.txt
```
requirements.txt に含まれる主なライブラリ:

- python-dotenv
- discord.py>=2.3.2
- aiohttp>=3.12,<4
- duckduckgo-search>=5.3.0
- ddgs
- openai>=1.0.0
- google-generativeai
- anthropic
- PyYAML>=6.0.1
- cryptography

```shell
cp .env.example .env
# 環境変数の設定
nano .env
```

## インストール方法（Windowsの場合）
### 0) 事前準備
1. Python 3.10 系を公式からインストール（Add to PATH にチェック）。
2. Git for Windows をインストール。
3. VS Code（推奨）＋拡張機能「Python」「Pylance」。

### 1) リポジトリ取得
```shell
# 任意のディレクトリで
git clone https://github.com/mayusaki3/AIChaBo.git
cd AIChaBo
git checkout develop
```
### 2) 仮想環境（venv）
```shell
# 仮想環境の作成と有効化
python -m venv venv
.\venv\Scripts\activate
```

### 3) requirements.txt に応じて依存ライブラリをインストール
```shell
pip install -r requirements.txt
```

```shell
cp .env.example .env
# 環境変数の設定
notepad .env
# 起動
python -m ui.discord.Discord_AIChaBo
```

## 使用方法（Ubuntuの場合）
### サービスの設定内容
/etc/systemd/system/AIChaBo.service
```ini
[Unit]
Description=AIChaBo Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/AIChaBo/src
ExecStart=/opt/AIChaBo/venv/bin/python -m ui.discord.Discord_AIChaBo
Restart=always

[Install]
WantedBy=multi-user.target
```
### 起動方法
```shell
# 上記設定を書き込み
sudo nano /etc/systemd/system/AIChaBo.service

# 設定有効化と起動
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable AIChaBo
sudo systemctl start AIChaBo

# 動作確認
sudo journalctl -u AIChaBo -f
```

### 更新方法
```shell
# AIChaBo サーバーを停止
sudo systemctl stop AIChaBo.service

# 最新のコードを取得
cd /opt/AIChaBo/src
git pull origin main

# 仮想環境をアクティベート
source ../venv/bin/activate

# 必要であれば依存パッケージを再インストール
pip install -r requirements.txt

# サービス再起動
sudo systemctl start AIChaBo.service

# ステータス確認
sudo systemctl status AIChaBo.service
```

## 機密情報を全削除する場合
以下の格納先フォルダごと削除してください。

Fernet起動時の既定は「ユーザーのホーム配下」です。
- Windows: C:\Users\<あなたのユーザー名>\.aichabo\master.key（＋機密データのJSON等）
- macOS/Linux: ~/.aichabo/master.key

同じ場所にフォルダ ~/.aichabo/ も作られます。  
※ AC_MASTER_KEY を環境変数で与えている場合は master.keyファイルは作られません。

## データ整合性と自動修復ポリシー

### 目的
秘密ストア（Fernet）で利用する JSON（`users.json` / `servers.json`）が外部要因で壊れた場合でも、運用を止めない。

### 方針
- 破損JSONは空辞書で復旧する（読込時）。  
- ノード形の自動修復：以下のキーが **dict 以外** だった場合、自動的に空の dict へ再初期化して処理を継続する。
  - `users.json`: `data[<user_id>]["providers"]`
  - `servers.json`: `data[<guild_id>]["providers"]`
- “鍵が存在するか”の判定は **復号できるか** で行う（文字列有無ではない）。

### レジリエンス仕様

本モジュールは永続ストアの破損・不正構造に対して自己修復動作を行う。

- **壊れノード再初期化**  
  `put_server_key()` 実行時に `data[str(gid)]` または `providers` が dict でない場合、空dictで再初期化して継続する。

- **削除系の堅牢化**  
  `delete_user_keys()` および `delete_server_keys()` は、対象ノードが空・欠落・保存失敗でも例外を送出せず False を返す。

- **破損JSON復旧**  
  `_load_json()` は構文エラーを検出した場合、バックアップを試み、最終的に空dictで継続する。

- **例外握りつぶし方針**  
  復号失敗や破損ノードはスキップし、APIは None/空dict を返す。エラーを上位に伝播させない。

### 互換性
- 既存APIの引数・戻りは変更しない。例外ポリシーも従来通り（保存・削除の失敗は False / 例外握りつぶし範囲は最小）。

### 想定シナリオ
- 手動編集や競合でノードが `list` や `str` に化けた場合でも、`put_*_key` 実行時に再初期化して保存を完了する。
- 読込時に JSON 全体が壊れていれば空で復旧し、以後の保存で整合状態へ戻す。

### テスト
- M01:T01-04-26/27 で上記ノード正規化分岐を検証する。
- 並列書き込み（LWW）や壊れJSON復旧、cleanup例外の網羅は既存のM01:T01-01〜04で担保。

## /コマンド一覧（Discord）

AIChaBo は以下の /コマンドを提供しています：

| 基本コマンド                   | 説明                                                                   |
|--------------------------------|------------------------------------------------------------------------|
| `/ac_help`                     | すべての /ac コマンドのヘルプを表示します。                            |
| `/ac_template`                 | 認証情報設定用テンプレート（JSON）をダウンロードします。               |
| `/ac_auth [file]`              | 使用するAIチャット/画像認識/画像生成の認証情報を登録します。 *1                          |
| `/ac_removeauth`               | 登録したあいちゃぼの認証情報を削除します。 *1                          |
| `/ac_authsharing`              | 認証情報が未登録の人に現在の認証情報をサーバー単位で共有します。 *1    |
| `/ac_authunsharing`            | サーバー単位で共有されている認証情報の共有を解除します。 *1            |
| `/ac_status [option]`          | 使用中のあいちゃぼの状態を表示します。 *2                              |
| `/ac_threads`                  | あいちゃぼと会話中のスレッド一覧を表示します。                         |
| `/ac_newchat [title] [Private]`| あいちゃぼとの会話用に新しいスレッドを作成します（件名は任意）         |

*1: 認証情報は「自分の認証情報」＞「共有された認証情報」の順に使用します。自分の認証情報のみ共有でき、誰の認証情報でも共有解除できます。共有状態で自分の認証情報を削除しても、共有解除は別途行う必要があります。

*2: optionは、以下が指定できます。
>| option              | 説明                                                                |
>|---------------------|---------------------------------------------------------------------|
>| `-exp`              | 現スレッドのコンテキストリストを common/session/dump にエクスポート |
>| `-expall`           | 全スレッドのコンテキストリストを common/session/dump にエクスポート |
>| `-expprompt`        | 現在使用中のプロンプトを common/session/dump にエクスポート         |
>| `-loadprompt`       | プロンプトを再読み込み                                              |
>| `-expintent`        | 現在使用中のインテント/辞書を common/session/dump にエクスポート    |
>| `-loadintent`       | インテント/辞書を再読み込み                                         |
>| `-printmsg:on/off`  | ONで、AIに投げるメッセージ内容をコンソールに出力                    |
>| `-expmsg:on/off`    | ONで、AIに投げるメッセージ内容を common/session/dump に出力         |
>| `-showopt`          | 設定されているオプションを表示                                      |
>| `-tracetool:on/off` | ONで、AIが起動するツール内容をコンソールに出力                      |

| スレッド内コマンド             | 説明                                                                   |
|--------------------------------|------------------------------------------------------------------------|
| `/ac_invite`                   | あいちゃぼを現在のスレッドに招待します。                               |
| `/ac_leave`                    | あいちゃぼを現在のスレッドから退出させます。                           |
| `/ac_newtopic`                 | 新しくトピックを始めます。以前の会話内容は忘れます。                   |
| `/ac_summary`                  | 現在のトピックを要約し、要約前の会話内容は忘れます。                   |

## 環境変数の設定（あいちゃぼ用）

あいちゃぼのチャット機能を使用するには、認証情報（JSONCファイル）のアップロードが必要です。  
1. `/ac_template` で認証情報設定用テンプレートをダウンロードします。
2. 利用するAIチャット毎にリネームして、必要な情報を記入してください：  
チャット用、画像認識用、画像生成用と、それぞれ別のLLMプロバイダ/モデルを指定できます。

    ### 🔹 OpenAI API Key の取得手順
    1. [OpenAI Platform](https://platform.openai.com/account/api-keys) にログイン
    2. 「+ Create new secret key」でAPIキーを生成
    3. 表示された `sk-xxxxx...` 形式のキーをコピー
    4. /ac_template コマンドでダウンロードした JSONCファイル の 各"api_key": に貼り付け
    🔒 注意：このAPIキーは絶対に外部に公開しないでください。
    5. 必要に応じて利用するチャットモデルをJSONファイル の 各"model": に貼り付け
    6. 必要に応じて以下のリンクよりログインしてBillingより支払方法や使用制限を設定
       https://platform.openai.com/account/billing

    ### 🔹 Gemini API Key の取得手順（Google AI Studio 直API）
    1. Google AI Studio にログインし、API Keys ページを開きます。
    2. 「Create API key」をクリックして発行・コピー。
    3. 表示されたキーをコピー
    4. /ac_template コマンドでダウンロードした JSONCファイル の 各"api_key": に貼り付け
    🔒 注意：このAPIキーは絶対に外部に公開しないでください。
    5. 必要に応じて利用するチャットモデルをJSONファイル の 各"model": に貼り付け

    ### 🔹 Claude API Key の取得手順（Anthropic 直API）
    1. Anthropic Console にログインします。
    2. Console の Account / API Keys で Create Key を実行し、表示されたキーをコピーします。
    3. /ac_template コマンドでダウンロードした JSONCファイル の 各"api_key": に貼り付け
    🔒 注意：このAPIキーは絶対に外部に公開しないでください。
    4. 必要に応じて利用するチャットモデルをJSONファイル の 各"model": に貼り付け

3. 利用するAIチャットのファイルを `/ac_auth` コマンドでアップロードします。  
   AIチャットを切り替える場合は、別のファイルをアップロードします。

   ### 🔹 認証情報テンプレートの構成
   `/ac_template` コマンドでダウンロードできる認証テンプレートは、複数の AI 機能（チャット・画像認識・画像生成）に対応するように構成されています。

    ```json
    {
        // あいちゃぼ認証情報テンプレートの仕様バージョン
        "template_version": "1.0",
        // === Chat（テキスト会話）用の設定 ===
        "chat": {
            // 利用プロバイダ名（いずれかを選択: OpenAI / Gemini / Claude ）
            "provider": "OpenAI",
            // プロバイダのAPIキー
            "api_key": "ここにあなたが利用するAPIキーを入力",
            // 使用モデル（Chat用）
            // 例: OpenAI: gpt-4o / o4-mini
            //     Gemini: gemini-1.5-pro / gemini-1.5-flash
            //     Claude: claude-sonnet-4-20250514 など
            "model": "gpt-4o",
            // 1レスポンスあたりの最大出力トークン
            "max_tokens": 1500,
            // プロンプトのカスタマイズ
            "prompt_overrides": {
                // あいちゃぼの、追加のふるまいを指示します。'#'で始まる行はコメントです。
                "character_append": [
                    "# あいちゃぼの、追加のふるまいを指示します。",
                    "#【口調上書き】よりビジネス寄りで丁寧な敬体を心がけ、絵文字は原則使わない。"
                ],
                // '/ac_summary' コマンドで実行する要約方法を差し替えます。'#'で始まる行はコメントです。
                "summary_replace": [
                    "# 要約のやり方を指示します。'#'で始まる行はコメントです。",
                    "#前置きなく、箇条書き 3〜6 点でまとめてください：",
                    "#- 重要ポイントと事実",
                    "#- 決定事項",
                    "#- 未決・リスク",
                    "#- 次アクション（担当・期日）",
                    "#挨拶や長い引用は入れないでください。"
                ]
            }
        },
        // === Vision（画像の説明/OCRなど）用の設定 ===
        "vision": {
            // 利用プロバイダ名（いずれかを選択: OpenAI / Gemini / Claude ）
            "provider": "OpenAI",
            // プロバイダのAPIキー
            "api_key": "ここにあなたが利用するAPIキーを入力",
            // 使用モデル（Vision用）
            // 例: OpenAI: gpt-4o / gpt-4o-mini
            //     Gemini: gemini-1.5-pro / 1.5-flash
            //     Claude: claude-sonnet-4-20250514 など
            "model": "gpt-4o"
        },
        // === 画像生成（image.generate）用の設定 ===
        "imagegen": {
            // 利用プロバイダ名（いずれかを選択: OpenAI / Gemini ）
            "provider": "OpenAI",
            // プロバイダのAPIキー
            "api_key": "ここにあなたが利用するAPIキーを入力",
            // 使用モデル（画像生成用）
            // 例: OpenAI: dall-e-3 / gpt-image-1
            //     Gemini: imagen-4.0-generate-001 / imagen-4.0-ultra-generate-001 / imagen-4.0-fast-generate-001 / imagen-3.0-generate-002 など
            "model": "dall-e-3",
            // 既定の出力サイズ（モデルによって許容値が異なるため、あいちゃぼに情報があれば補正されます）
            "size": "1024x1024",
            // 既定の品質（モデルによって "standard" / "hd" など異なるため、あいちゃぼに情報があれば補正されます）
            "quality": "standard"
        }
    }
    ```
    
    ### 🔸 各フィールドの説明
    以下の大項目に分かれています。詳細はテンプレート内のコメントを参照してください。
    - **chat**：テキスト会話に使用する設定です。
    - **vision**：画像を処理する際に使用されます。
    - **imagegen**：画像生成用の設定です。
    
    > ⚠ 各セクションの `"provider"` は `"OpenAI"` `"Gemini"` `"Claude"` が指定可能です）。  
    > ⚠ Web検索機能は [DuckDuckGo](https://duckduckgo.com/) を使用しています。

## 招待リンクの設定

AIChaBoの招待リンクの作成方法は以下の通りです。
   1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
   2. My Applicationsで AIChaBo を選択
   3. 左メニュー「OAuth2」→「OAuth2 URL Generator」を表示
   4. 「scopes」で以下のパーミッションをチェック  
     - bot  
     - applications.commands  
   5. 「Bot Permissions」で以下のパーミッションをチェック  
     - View Channels  
     - Send Messages  
     - Create Public Threads  
     - Create Private Threads  
     - Send Messages in threads  
     - Manage Threads  
     - Read Message History
     - Use Slash Commands  
   6. 「Generated URL」でコピーしてブラウザで開き、サーバーを選択して招待

AIChaBo
https://discord.com/oauth2/authorize?client_id=1392390825148944406&permissions=397284543488&integration_type=0&scope=bot+applications.commands

AIChaBo Dev
https://discord.com/oauth2/authorize?client_id=1395576546747744357&permissions=397284543488&integration_type=0&scope=bot+applications.commands
