# utiltests/web_read_test.py（最小）
import asyncio
from common.plugins.dispatcher import try_handle_by_plugin, list_providers
from common.plugins.base import ReadRequest, ReadResponse

async def _fake_read(reqs):
    # ここは実装側の read_urls に合わせて必要なら実コード呼び出しに差替
    import aiohttp, async_timeout
    out=[]
    async with aiohttp.ClientSession() as sess:
        for r in reqs:
            async with async_timeout.timeout(20):
                async with sess.get(r.url, headers=r.headers or {}) as resp:
                    text = await resp.text()
                    out.append(ReadResponse(url=str(resp.url), status=resp.status, headers=dict(resp.headers), body_text=text, tag=r.tag))
    return out

async def main():
    if not list_providers():
        print("SKIP: no providers registered")
        return
    user_text = "このリポのREADMEの要点まとめて"
    urls = ["https://github.com/python/cpython"]  # 公開URL
    pr = await try_handle_by_plugin(user_text, urls, _fake_read)
    assert pr is not None, "PluginResult should not be None"
    assert pr.citations, "citations should exist"
    print("OK: plugin handled; cites:", pr.citations[:2])

if __name__ == "__main__":
    asyncio.run(main())
