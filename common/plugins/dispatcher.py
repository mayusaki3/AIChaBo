# common/plugins/dispatcher.py

from __future__ import annotations
import importlib, importlib.util, inspect, os, sys, pathlib
from typing import List, Optional, Callable, Awaitable
from .base import ProviderPlugin, ReadRequest, ReadResponse, PluginResult

_RunWebRead = Callable[[List[ReadRequest]], Awaitable[List[ReadResponse]]]
_PROVIDERS_CACHE: Optional[List[ProviderPlugin]] = None

def _load_providers_from_dir(directory: str) -> List[ProviderPlugin]:
    providers: List[ProviderPlugin] = []
    pdir = pathlib.Path(directory)
    if not pdir.exists():
        return providers
    for path in pdir.glob("*.py"):
        if path.name in ("__init__.py",):
            continue
        mod_name = f"common.plugins.providers.{path.stem}"
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
        else:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if not spec or not spec.loader:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)  # type: ignore
        # 優先: register_plugins()
        if hasattr(mod, "register_plugins"):
            for cls in mod.register_plugins():  # type: ignore
                providers.append(cls())
            continue
        # 次: PROVIDERS = [Class, ...]
        if hasattr(mod, "PROVIDERS"):
            for cls in getattr(mod, "PROVIDERS"):
                providers.append(cls())
            continue
        # 最後: ProviderPlugin サブクラス探索
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            try:
                if issubclass(obj, ProviderPlugin) and obj is not ProviderPlugin:
                    providers.append(obj())
            except Exception:
                pass
    return providers

def _get_all_providers() -> List[ProviderPlugin]:
    global _PROVIDERS_CACHE
    if _PROVIDERS_CACHE is None:
        base = pathlib.Path(__file__).parent
        _PROVIDERS_CACHE = _load_providers_from_dir(str(base / "providers"))
    return _PROVIDERS_CACHE

def refresh_providers_cache():
    global _PROVIDERS_CACHE
    _PROVIDERS_CACHE = None

def list_providers() -> List[str]:
    """現在登録されているプラグイン名の一覧（未登録なら空）"""
    return [getattr(p, "name", p.__class__.__name__) for p in _get_all_providers()]

def _load_system_prompt_if_exists(plugin_name: str) -> Optional[str]:
    # system_prompts/<plugin>.txt があれば読み込み
    root = pathlib.Path(__file__).parents[2]  # common/ から見てプロジェクトルート想定
    p = root / "system_prompts" / f"{plugin_name}.txt"
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return None
    return None

async def try_handle_by_plugin(user_text: str, urls: List[str], run_webread: _RunWebRead) -> Optional[PluginResult]:
    # providers/ 配下を自動登録
    providers = _get_all_providers()

    for url in urls or []:
        for prov in providers:
            if not prov.match(url):
                continue
            plan = prov.plan(url, user_text)
            if not plan:
                continue
            resps = await run_webread(plan)
            result = prov.consume(resps)
            # system prompt をメタに添付（あれば）
            sp = _load_system_prompt_if_exists(getattr(prov, "name", prov.__class__.__name__).lower())
            if sp:
                if result.meta is None:
                    result.meta = {}
                result.meta.update({
                    "plugin_name": getattr(prov, "name", prov.__class__.__name__),
                    "system_prompt": sp,
                })
            if hasattr(prov, "has_second_stage") and prov.has_second_stage():
                req2 = prov.plan_second_stage(result)
                if req2:
                    resps2 = await run_webread(req2)
                    result = prov.consume_second_stage(result, resps2)
            return result

    return None
