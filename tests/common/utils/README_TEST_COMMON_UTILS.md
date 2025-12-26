[テストユーティリティ](../../README_TEST.md) > common/utilsモジュール単体テスト

# common/utilsモジュール単体テスト

## テスト番号と検証内容（Index）

| Suite | 目的（スコープ） | 機能 | モジュール |
|---|---|---|---|
| **T01-01** | 機密文字列マスキング | api_key / sk- / ghp_ / AIza 等の秘匿化 | `common/utils/redact.py` |
| **T02-01** | ログ出力ユーティリティ | 初期化分岐（handlers有無）/ info・warn・error（redact適用） | `common/utils/logger.py` |
| **T03-01** | JSONC ロード | // / # / /*...*/ コメント除去 + 末尾カンマ除去 + load_jsonc | `common/utils/jsonc.py` |
| **T04-01** | 認証ファイル解析 | 認証ファイル(bytes)の JSON 解析（エラー種別の切り分け） | `common/utils/file_io.py` |
| **T06-01** | URL 事前取得（prefetch） | URL 読み取り→整形 + 署名(sig)生成（最大8件） | `common/utils/prefetch.py` |
| **T07-01** | スレッド管理（thread_utils） | server_id別の thread_id 永続化（load/save/add/remove/clean） | `common/utils/thread_utils.py` |
| **T07-02** | スレッド管理（branch） | 仕様テストでは踏みにくい分岐（no-op 等） | `common/utils/thread_utils.py` |
| **T08-01** | Web読み取り（webread_utils） | URL取得→HTML/テキスト判定→要約→整形（I/Oはモック） | `common/utils/webread_utils.py` |
| **T08-02** | Web読み取り（branch） | 仕様テストでは踏みにくい分岐（title/published/画像補正 等） | `common/utils/webread_utils.py` |
| **T08-03** | Web読み取り（remaining） | 残分岐の補完（text-like判定/HTTPエラー文字列生成 等） | `common/utils/webread_utils.py` |

---

## テスト詳細

### T01-01 : 機密文字列マスキング（redact）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T01-01-01** | api_key prefix+value | `api_key=XXXX` が `api_key=***` に置換される | `common/utils/redact.py` |
| **T01-01-02** | API-KEY prefix+value | `API-KEY: XXXX` が `API-KEY: ***` に置換される（大小無視） | `common/utils/redact.py` |
| **T01-01-03** | sk- 値単体 | `sk-XXXX` が `head(keep)+***` に置換される | `common/utils/redact.py` |
| **T01-01-04** | ghp_ 値単体 | `ghp_XXXX` が `head(keep)+***` に置換される | `common/utils/redact.py` |
| **T01-01-05** | AIza 値単体 | `AIzaXXXX` が `head(keep)+***` に置換される | `common/utils/redact.py` |
| **T01-01-06** | keep 指定 | keep 値変更により表示される head 長が変化する | `common/utils/redact.py` |
| **T01-01-07** | 非文字列入力 | int 等でも例外なく `str(obj)` が返る | `common/utils/redact.py` |
| **T01-01-08** | 非一致 | マスク対象でない文字列は変更されない | `common/utils/redact.py` |

#### 実行

```bash
python -m tests.common.utils.T01_Redact_01_redact_test
```

---

### T02-01 : ログ出力ユーティリティ（logger）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T02-01-01** | 初期化（handlers無し） | handlers が無い状態で import/reload すると handler が追加され level=INFO になる | `common/utils/logger.py` |
| **T02-01-02** | 初期化（handlers有り） | handlers が既にある状態で import/reload しても handler が増えない（重複しない） | `common/utils/logger.py` |
| **T02-01-03** | warn 出力 | `log_warn()` が WARNING として出力される | `common/utils/logger.py` |
| **T02-01-04** | error は redact | `log_error()` が redact を通して出力される（例：api_key が `***` に） | `common/utils/logger.py` |

#### 実行

```bash
python -m tests.common.utils.T02_Logger_01_logger_test
```

---

### T03-01 : JSONC ロード（jsonc）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T03-01-01** | // コメント | // コメントを除去して loads できる | `common/utils/jsonc.py` |
| **T03-01-02** | # コメント | # コメントを除去して loads できる | `common/utils/jsonc.py` |
| **T03-01-03** | block コメント | /*...*/ を除去して loads できる | `common/utils/jsonc.py` |
| **T03-01-04** | 文字列内保持 | 文字列内の // や /* */ を除去しない | `common/utils/jsonc.py` |
| **T03-01-05** | 末尾カンマ除去 | object/array の trailing comma を除去 | `common/utils/jsonc.py` |
| **T03-01-06** | 文字列内カンマ保持 | 文字列内の `,}` `,]` は除去しない | `common/utils/jsonc.py` |
| **T03-01-07** | 不正 JSON | 不正 JSON は例外 | `common/utils/jsonc.py` |
| **T03-01-08** | load_jsonc | ファイルを UTF-8 で読み取り loads できる | `common/utils/jsonc.py` |
| **T03-01-09** | strip 戻り型 | `_strip_*` が str を返す | `common/utils/jsonc.py` |

#### 実行

```bash
python -m tests.common.utils.T03_Jsonc_01_jsonc_test
```

---

### T04-01 : 認証ファイル解析（file_io）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T04-01-01** | 正常 JSON bytes | `parse_auth_file()` が bytes(JSON) を dict として返す | `common/utils/file_io.py` |
| **T04-01-02** | 不正 JSON | JSON として読めない bytes は `{"error": ...}` を返す | `common/utils/file_io.py` |
| **T04-01-03** | 不正 UTF-8 | UTF-8 デコードできない bytes は `{"error": ...}` を返す | `common/utils/file_io.py` |
| **T04-01-04** | bytes 以外 | bytes 以外の入力は `{"error": ...}` を返す | `common/utils/file_io.py` |

#### 実行

```bash
python -m tests.common.utils.T04_FileIo_01_file_io_test
```

---

### T06-01 : URL 事前取得（prefetch）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T06-01-01** | urls=None | `prefetch_doc_summaries(urls=None)` は `("", tuple())` を返す | `common/utils/prefetch.py` |
| **T06-01-02** | urls=[] | `prefetch_doc_summaries(urls=[])` は `("", tuple())` を返す | `common/utils/prefetch.py` |
| **T06-01-03** | 空要素除去 | `["", None, ""]` のような falsy URL を除去して空扱いにする | `common/utils/prefetch.py` |
| **T06-01-04** | 正常（format + sig） | read→format の結果文字列を返し、sig は入力URLの先頭最大8件 | `common/utils/prefetch.py` |
| **T06-01-05** | read_urls 例外 | `read_urls()` の例外が（仕様通り）伝播する | `common/utils/prefetch.py` |
| **T06-01-06** | read_urls 引数 | `max_bytes/max_chars/follow_pdfs/...` が期待通りに渡される | `common/utils/prefetch.py` |

#### 実行

```bash
python -m tests.common.utils.T06_Prefetch_01_prefetch_test
```

---

### T07-01 : スレッド管理（thread_utils）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T07-01-01** | パス組み立て | `get_server_file_path()` が `{service}/{server_id}.json` を返す | `common/utils/thread_utils.py` |
| **T07-01-02** | load: 未存在 | 対象ファイルが無い場合 `load_server_threads()` は `[]` を返す | `common/utils/thread_utils.py` |
| **T07-01-03** | save/load roundtrip | save→load で同値になり、要素は `str(...).strip()` が適用される | `common/utils/thread_utils.py` |
| **T07-01-04** | add: 重複防止 | `add_thread_to_server()` は同一IDを重複登録しない | `common/utils/thread_utils.py` |
| **T07-01-05** | remove: 条件付き削除 | `remove_thread_from_server()` は存在時のみ削除する | `common/utils/thread_utils.py` |
| **T07-01-06** | membership | `is_thread_managed()` が membership を返す | `common/utils/thread_utils.py` |
| **T07-01-07** | フィルタ | `filter_existing_threads(saved,current)` が共通要素のみ返す | `common/utils/thread_utils.py` |
| **T07-01-08** | 不在server削除条件 | `delete_server_data_if_missing()` が条件一致で削除し True | `common/utils/thread_utils.py` |
| **T07-01-09** | thread cleanup | `clean_deleted_threads()` が current_ids に基づき保存内容を更新 | `common/utils/thread_utils.py` |
| **T07-01-10** | server cleanup: base_dir無し | `clean_deleted_servers()` は base_dir 無しなら return | `common/utils/thread_utils.py` |
| **T07-01-11** | server cleanup: 不在server削除 | `clean_deleted_servers()` が既存server_id集合に無いファイルを削除 | `common/utils/thread_utils.py` |

#### 実行

```bash
python -m tests.common.utils.T07_ThreadUtils_01_thread_utils_test
```

---

### T07-02 : スレッド管理（branch）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T07-02-01** | no-op（保存不要） | `clean_deleted_threads()` で filtered==saved の場合、save を呼ばない | `common/utils/thread_utils.py` |
| **T07-02-02** | delete: file無 | `delete_server_data_if_missing()` は file 無しなら False | `common/utils/thread_utils.py` |
| **T07-02-03** | delete: server_id既存 | `delete_server_data_if_missing()` は server_id が existing に含まれるなら False | `common/utils/thread_utils.py` |

#### 実行

```bash
python -m tests.common.utils.T07_ThreadUtils_02_thread_utils_branch_test
```

---

### T08-01 : Web読み取り（webread_utils）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T08-01-01** | redact | シークレット類がマスクされる | `common/utils/webread_utils.py` |
| **T08-01-02** | whitespace | `_clean_whitespace()` が空白を圧縮する | `common/utils/webread_utils.py` |
| **T08-01-03** | filename | `_filename_from_url()` が末尾ファイル名を返す | `common/utils/webread_utils.py` |
| **T08-01-04** | ctype判定 | `_is_html_ctype()` / `_is_text_like()` の基本判定 | `common/utils/webread_utils.py` |
| **T08-01-05** | decode fallback | `_decode_text()` が utf-8→cp932→replace の順で復旧 | `common/utils/webread_utils.py` |
| **T08-01-06** | summarize_code | `_summarize_code()` が上限で省略する | `common/utils/webread_utils.py` |
| **T08-01-07** | HTML helpers | title/published/noise/main 等の補助関数群の基本動作 | `common/utils/webread_utils.py` |
| **T08-01-08** | header auth ルール | `_build_request_headers()` の Authorization 制御 | `common/utils/webread_utils.py` |
| **T08-01-09** | fetch例外 | `read_urls()` が fetch 例外を error として返す | `common/utils/webread_utils.py` |
| **T08-01-10** | HTTPエラー JSON | HTTP>=400 + JSON(dict) の message 等を抽出して note を作る | `common/utils/webread_utils.py` |
| **T08-01-11** | HTTPエラー 非JSON | HTTP>=400 + 非JSON で snippet を拾って note を作る | `common/utils/webread_utils.py` |
| **T08-01-12** | PDF | PDF を検出し `is_pdf=True` と note を返す | `common/utils/webread_utils.py` |
| **T08-01-13** | text-like | HTML以外の text-like を code要約として返す | `common/utils/webread_utils.py` |
| **T08-01-14** | HTML parse失敗 | HTML 解析不能なら error を返す | `common/utils/webread_utils.py` |
| **T08-01-15** | HTML 正常 | HTML 解析→title/published/main/images/summary を生成 | `common/utils/webread_utils.py` |
| **T08-01-16** | format | `format_read_results_for_llm()` が整形文字列を返す | `common/utils/webread_utils.py` |

#### 実行

```bash
python -m tests.common.utils.T08_WebReadUtils_01_webread_utils_test
```

---

### T08-02 : Web読み取り（branch）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T08-02-01** | redact guard | `redact()` は 非str/空 をそのまま返す | `common/utils/webread_utils.py` |
| **T08-02-02** | decode replace | `_decode_text()` の replace fallback を踏む | `common/utils/webread_utils.py` |
| **T08-02-03** | summarize_code no-trim | 省略不要な場合は全文相当（ブロック整形） | `common/utils/webread_utils.py` |
| **T08-02-04** | title 全空 | `_extract_title()` が空を返す経路 | `common/utils/webread_utils.py` |
| **T08-02-05** | published 不一致 | `_guess_published()` が None を返す経路 | `common/utils/webread_utils.py` |
| **T08-02-06** | drop_noise 対象無し | 対象要素が無い場合の no-op | `common/utils/webread_utils.py` |
| **T08-02-07** | main 最大div | `_pick_main_block()` の最大div選択 | `common/utils/webread_utils.py` |
| **T08-02-08** | 画像URL補正 | `_collect_images()` の `//` や `/path` 補正 | `common/utils/webread_utils.py` |
| **T08-02-09** | summarize 閾値 | `_summarize()` の閾値/省略 | `common/utils/webread_utils.py` |
| **T08-02-10** | headers extra枝 | `_build_request_headers()` の extraヘッダ反映 | `common/utils/webread_utils.py` |
| **T08-02-11** | HTTP error JSON非dict | JSONがdictでない場合の note 分岐 | `common/utils/webread_utils.py` |
| **T08-02-12** | 非text-like parse fail | 非HTML・非text-like で parse 失敗→ error | `common/utils/webread_utils.py` |
| **T08-02-13** | main空→itertext | `_pick_main_block()` が空なら itertext にフォールバック | `common/utils/webread_utils.py` |
| **T08-02-14** | max_chars trim | `max_chars` で本文がトリムされる | `common/utils/webread_utils.py` |
| **T08-02-15** | citationsなし | `format_read_results_for_llm(require_citations=False)` | `common/utils/webread_utils.py` |

#### 実行

```bash
python -m tests.common.utils.T08_WebReadUtils_02_webread_utils_branch_test
```

---

### T08-03 : Web読み取り（remaining）

#### ケース

| 番号 | 目的 | 検証内容 | モジュール |
|---|---|---|---|
| **T08-03-01** | text-like: json ctype | `_is_text_like()` が json 系 ctype を True 判定 | `common/utils/webread_utils.py` |
| **T08-03-02** | text-like: 拡張子推定 | `_is_text_like()` が `.py/.md/...` 等で True 判定 | `common/utils/webread_utils.py` |
| **T08-03-03** | text-like: False | text-like に該当しない場合 False | `common/utils/webread_utils.py` |
| **T08-03-04** | published 一致 | `_guess_published()` が一致で return する経路 | `common/utils/webread_utils.py` |
| **T08-03-05** | GitHub auth破棄 | `_build_request_headers()` が GitHub では Authorization を破棄 | `common/utils/webread_utils.py` |
| **T08-03-06** | LLM host auth許可 | `_build_request_headers()` が LLM host では Authorization を許可 | `common/utils/webread_utils.py` |
| **T08-03-07** | HTTP error snippet空 | snippet が空のとき note は `HTTP {code}` のみ | `common/utils/webread_utils.py` |
| **T08-03-08** | HTTP error snippet+redact | JSON decode 失敗時に snippet を拾い、secret を redact して note を作る | `common/utils/webread_utils.py` |

#### 実行

```bash
python -m tests.common.utils.T08_WebReadUtils_03_webread_utils_remaining_branch_test
```

---
[テストユーティリティ](../../README_TEST.md) > common/utilsモジュール単体テスト
