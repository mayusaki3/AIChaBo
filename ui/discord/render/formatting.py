# Discord用の「表示整形」一式：
# - 長文分割（2000文字境界）
# - 口調誘導（「すぐに続けますね。/少々お待ちください。」→「続けますか？」へ置換）
# - 送信の最終段で redact を適用（万一の秘匿情報混入を防ぐ）
from common.utils.webread_utils import redact

DISCORD_LIMIT = 2000
CONT_PHRASES = ("すぐに続けますね。", "少々お待ちください。")
REPLACE_TO = "続けますか？"

def split_for_discord(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    """Discordの1メッセージ上限に合わせて安全に分割。"""
    s = redact(text or "")  # 念のため分割前にもマスク
    out, buf = [], ""
    for line in s.splitlines(True):  # 改行を保持しつつ結合
        if len(buf) + len(line) > limit:
            out.append(buf)
            buf = line
        else:
            buf += line
    if buf:
        out.append(buf)
    return out or [""]

def sanitize_continuation(chunks: list[str]) -> list[str]:
    """“待機系フレーズ”をユーザー誘導に置換。"""
    def _fix(t: str) -> str:
        for p in CONT_PHRASES:
            t = t.replace(p, REPLACE_TO)
        return t
    return [_fix(c) for c in chunks]

async def send_reply(channel, text: str, files=None):
    """送信の統一窓口。ここ以外で直接 send しない方針。"""
    chunks = sanitize_continuation(split_for_discord(text))
    first, rest = (chunks[0], chunks[1:])
    await channel.send(first, files=files or [])
    for c in rest:
        await channel.send(c)
