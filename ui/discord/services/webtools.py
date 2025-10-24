# “web.*” 系アクションの委譲口。
# - まずはサイト固有プラグイン（providers）に投げ、該当がなければ後日 generic フォールバックを導入予定
from common.plugins.dispatcher import try_handle_by_plugin

async def do_web_read(urls: list[str], user_text: str, run_webread):
    """URLリストをサイト固有プラグインへ委譲。該当なしなら None。"""
    return await try_handle_by_plugin(user_text, urls, run_webread)

async def do_web_search(queries: list[str], user_text: str, run_search):
    """現状は既存の検索実装に委譲。将来 generic_search プラグインへ差し替え可能にする。"""
    return await run_search(queries, user_text)
