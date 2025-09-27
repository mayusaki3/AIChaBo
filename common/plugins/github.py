# common/plugins/github.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
import re, json
from .base import ProviderPlugin, ReadRequest, ReadResponse, PluginResult, domain_matches

_API_ACCEPT = "application/vnd.github+json"
_API_VER = "2022-11-28"
_ALLOW_EXTS = (".py", ".md", ".txt", ".yml", ".yaml", ".json")
_MAX_RAW = 8

_RE_OWNER_REPO = re.compile(r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)")
_RE_TREE = re.compile(r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)/tree/(?P<ref>[^/#?]+)")

class GitHubPlugin:
    name = "github"
    domains = ["github.com", "api.github.com", "raw.githubusercontent.com"]

    def match(self, url: str) -> bool:
        return domain_matches(url, self.domains)

    def _parse_owner_repo_ref(self, url: str) -> Dict[str, Optional[str]]:
        m = _RE_TREE.match(url)
        if m:
            return {"owner": m.group("owner"), "repo": m.group("repo"), "ref": m.group("ref")}
        m = _RE_OWNER_REPO.match(url)
        if m:
            return {"owner": m.group("owner"), "repo": m.group("repo"), "ref": None}
        return {"owner": None, "repo": None, "ref": None}

    def plan(self, url: str, user_text: Optional[str]) -> List[ReadRequest]:
        ids = self._parse_owner_repo_ref(url)
        owner, repo, ref = ids["owner"], ids["repo"], ids["ref"]
        if not owner or not repo:
            return []
        base = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {"Accept": _API_ACCEPT, "X-GitHub-Api-Version": _API_VER}

        reqs: List[ReadRequest] = [
            ReadRequest(url=base, headers=headers, tag="repo"),
            ReadRequest(url=f"{base}/branches", headers=headers, tag="branches"),
        ]
        # ref 指定あれば優先、無ければ default→develop→main→master を後段で選ぶ
        for r in [ref] + [x for x in ["develop", "main", "master"] if x is not None]:
            if r:
                reqs.append(ReadRequest(url=f"{base}/git/trees/{r}?recursive=1", headers=headers, tag=f"tree:{r}"))
        return reqs

    def consume(self, responses: List[ReadResponse]) -> PluginResult:
        by = {r.tag: r for r in responses if r and r.tag}
        repo_meta = {}
        default_branch = None
        if "repo" in by and by["repo"].body_text:
            repo_meta = json.loads(by["repo"].body_text)
            default_branch = repo_meta.get("default_branch")

        # tree 選択（default→develop→main→master 優先）
        pref = [f"tree:{default_branch}", "tree:develop", "tree:main", "tree:master"]
        tree_json = None
        for t in pref:
            r = by.get(t)
            if r and r.status == 200 and r.body_text:
                try:
                    tree_json = json.loads(r.body_text)
                    break
                except Exception:
                    pass

        raw_paths: List[str] = []
        if tree_json and "tree" in tree_json:
            for node in tree_json["tree"]:
                p = node.get("path", "")
                if node.get("type") == "blob" and p.endswith(_ALLOW_EXTS):
                    raw_paths.append(p)
                    if len(raw_paths) >= _MAX_RAW:
                        break

        items = [{
            "type": "github_context",
            "owner": (repo_meta.get("owner") or {}).get("login"),
            "repo": repo_meta.get("name"),
            "ref": default_branch,
            "raw_paths": raw_paths,
        }]
        cites = [r.url for r in responses if r and r.url]
        return PluginResult(items=items, citations=cites)

    # 二段目（raw 取得）
    def has_second_stage(self) -> bool:
        return True

    def plan_second_stage(self, result: PluginResult) -> List[ReadRequest]:
        if not result.items:
            return []
        ctx = result.items[0]
        owner, repo, ref = ctx.get("owner"), ctx.get("repo"), ctx.get("ref")
        if not all([owner, repo, ref]):
            return []
        headers = {}
        reqs: List[ReadRequest] = []
        for p in ctx.get("raw_paths", [])[:_MAX_RAW]:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{p}"
            reqs.append(ReadRequest(url=url, headers=headers, tag=f"raw:{p}"))
        return reqs

    def consume_second_stage(self, result: PluginResult, responses: List[ReadResponse]) -> PluginResult:
        # ここでは本文を返すだけ（要約は既存のサマライザに任せるのがシンプル）
        raw_files: List[Dict[str, Any]] = []
        for r in responses:
            if not r or r.status != 200:
                continue
            path = (r.tag or "").replace("raw:", "", 1)
            raw_files.append({"path": path, "url": r.url, "content": r.body_text or ""})
        # 画面用テキストはここで整形しても、呼び出し側に任せてもOK
        result.items.append({"type": "github_raw_files", "files": raw_files})
        result.citations.extend([r.url for r in responses if r and r.url])
        return result
