# -*- coding: utf-8 -*-
"""
T02_SecretStore_01_store_test.py
目的: SecretStore の基本R/Wと並行書込みの健全性（LWW・非破壊）を検証
実行例: python -m utiltests.T02_SecretStore_01_store_test
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from common.secret.store import store
from utiltests._report import make_reporter

PROVS = ["openai", "anthropic", "google"]

def _fresh_ids():
    base = time.time_ns() % 1_000_000_000
    uid = 100000000 + base
    gid = 200000000 + base
    return int(uid), int(gid)

def _keys(tag: str):
    return {p: f"{p}-key-{tag}".encode() for p in PROVS}

def test_basic_user_roundtrip():
    uid, _ = _fresh_ids()
    keys = _keys("AAA")
    for p, k in keys.items():
        store.put_user_key(uid, p, k)
    got = {p: store.get_user_key(uid, p) for p in PROVS}
    assert set(got.keys()) == set(PROVS)
    for p in PROVS:
        assert got[p] == keys[p]

def test_basic_server_roundtrip():
    _, gid = _fresh_ids()
    keys = _keys("AAA")
    for p, k in keys.items():
        store.put_server_key(gid, p, k)
    got_all = store.get_server_keys(gid)
    assert set(got_all.keys()) == set(PROVS)
    for p in PROVS:
        assert got_all[p] == keys[p]
    assert store.has_server_any_key(gid) is True
    store.delete_server_keys(gid)
    assert store.has_server_any_key(gid) is False

def test_concurrent_user_puts_last_wins_no_corruption():
    uid, _ = _fresh_ids()
    keys1 = _keys("AAA")
    keys2 = _keys("BBB")

    def writer(keys):
        for p, k in keys.items():
            store.put_user_key(uid, p, k)

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(writer, keys1), ex.submit(writer, keys2)]
        for _ in as_completed(futs): pass

    got = {p: store.get_user_key(uid, p) for p in PROVS}
    ok_all_aaa = all(got[p] == keys1[p] for p in PROVS)
    ok_all_bbb = all(got[p] == keys2[p] for p in PROVS)
    assert ok_all_aaa or ok_all_bbb, "mixed partial write detected"

def test_concurrent_server_puts_last_wins_no_corruption():
    _, gid = _fresh_ids()
    keys1 = _keys("AAA")
    keys2 = _keys("BBB")

    def writer(keys):
        for p, k in keys.items():
            store.put_server_key(gid, p, k)

    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(writer, keys1), ex.submit(writer, keys2), ex.submit(writer, keys1)]
        for _ in as_completed(futs): pass

    got = store.get_server_keys(gid)
    ok_all_aaa = all(got[p] == keys1[p] for p in PROVS)
    ok_all_bbb = all(got[p] == keys2[p] for p in PROVS)
    assert ok_all_aaa or ok_all_bbb, "mixed partial write detected"

def main():
    rep = make_reporter("T02-01")
    rep.banner("SecretStore basic & concurrency")
    try:
        print("Secret backend:", store.backend_name())
    except Exception:
        pass
    with rep.case("user roundtrip"): test_basic_user_roundtrip()
    with rep.case("server roundtrip"): test_basic_server_roundtrip()
    with rep.case("user concurrent LWW"): test_concurrent_user_puts_last_wins_no_corruption()
    with rep.case("server concurrent LWW"): test_concurrent_server_puts_last_wins_no_corruption()
    rep.summary()

if __name__ == "__main__":
    main()
