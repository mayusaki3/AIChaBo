# common/plugins/dispatcher.py
from __future__ import annotations
import importlib, os, yaml
from typing import List, Optional, Callable
from .base import ProviderPlugin, ReadRequest, ReadResponse, PluginResult

_RunWebRead = Callable[[List[ReadRequest]], "awaitable[List[ReadResponse]]"]

def _load_registry(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        y = yaml.safe_load(f)
    return y.get("providers", [])

def _load_class(spec: str):
    mod, cls = spec.split(":")
    m = importlib.import_module(mod)
    return getattr(m, cls)

async def try_handle_by_plugin(user_text: str, urls: List[str], run_webread: _RunWebRead) -> Optional[PluginResult]:
    reg_path = os.path.join(os.path.dirname(__file__), "registry.yaml")
    registry = _load_registry(reg_path)

    providers: list[ProviderPlugin] = []
    for p in registry:
        cls = _load_class(p["class"])
        inst: ProviderPlugin = cls()
        inst.domains = p.get("domains", getattr(inst, "domains", []))
        providers.append(inst)

    for url in urls:
        for prov in providers:
            if not prov.match(url):
                continue
            plan = prov.plan(url, user_text)
            if not plan:
                continue
            resps = await run_webread(plan)
            result = prov.consume(resps)

            if hasattr(prov, "has_second_stage") and prov.has_second_stage():
                req2 = prov.plan_second_stage(result)
                if req2:
                    resps2 = await run_webread(req2)
                    result = prov.consume_second_stage(result, resps2)
            return result

    return None
