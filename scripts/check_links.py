#!/usr/bin/env python3
import sys
import re
import pathlib

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
errors = 0

LINK_RE = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$', re.MULTILINE)


def slugify_heading(text: str) -> str:
    """
    GitHub 風の見出しアンカーをざっくり再現する。
    - 小文字化
    - 前後の空白除去
    - 余分な記号を削除（日本語などのワード文字は残す）
    - 空白を '-' に変換
    """
    t = text.strip().lower()
    # 単語文字(\w), 空白, ハイフン以外を削る（日本語は \w に含まれる）
    t = re.sub(r"[^\w\- ]+", "", t)
    # 連続スペースを '-' に
    t = re.sub(r"\s+", "-", t)
    return t


def collect_anchors(md_path: pathlib.Path) -> set[str]:
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    anchors: set[str] = set()
    for m in HEADING_RE.finditer(text):
        heading_text = m.group(2)
        anchors.add(slugify_heading(heading_text))
    return anchors


def check_link(md: pathlib.Path, href: str) -> int:
    """
    個々のリンクをチェックし、エラー数を返す。
    - ファイルの存在
    - アンカー(#...)がある場合は見出しIDもチェック
    """
    local_errors = 0

    # プロトコル付きや mailto, フラグメントのみは従来どおりスキップ
    if href.startswith(("http://", "https://", "sandbox:")):
        return 0
    if href.startswith("#") or href.startswith("mailto:"):
        return 0

    # foo.md#anchor → path_part, fragment に分解
    if "#" in href:
        path_part, fragment = href.split("#", 1)
    else:
        path_part, fragment = href, None

    target = (md.parent / path_part).resolve()

    if not target.exists():
        print(f"[BROKEN_FILE] {md}: {href}")
        return 1

    # アンカー指定がなければここまで
    if not fragment:
        return 0

    # .md 以外のファイルの #fragment はチェックしない
    if target.suffix.lower() != ".md":
        return 0

    try:
        anchors = collect_anchors(target)
    except OSError as e:
        print(f"[ERROR] failed to read {target}: {e}")
        return 1

    if fragment not in anchors:
        # アンカー候補一覧をデバッグ用に出したければ anchors を併記してもよい
        print(f"[BROKEN_ANCHOR] {md}: {href} (not found in {target.name})")
        local_errors += 1

    return local_errors


def main() -> None:
    errors = 0
    for md in root.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        for m in LINK_RE.finditer(text):
            href = m.group(1)
            errors += check_link(md, href)

    if errors:
        print(f"\nBroken links (files and anchors): {errors}")
        sys.exit(1)
    print("All links OK")


if __name__ == "__main__":
    main()
