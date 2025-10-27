# utiltests/store_test.py  ← 内部定数に依存しない版（全置換）
# ------------------------------------------------------------
# SecretStore の動作テスト（Fernet固定版を想定）
#  - 依存: pip install cryptography
#  - 既存データは残します（衝突回避のため毎回ユニークな UID/GID を使う）
#  - 同時実行（スレッド）での競合をテストします。
# ------------------------------------------------------------

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from common.secret.store import store

# 毎回ユニークなIDを使って既存データと衝突しないようにする
def _fresh_ids():
    base = time.time_ns() % 1_000_000_000
    uid = 100000000 + base
    gid = 200000000 + base
    return int(uid), int(gid)

PROVS = ["openai", "anthropic", "google"]

def _keys(tag: str):
    return {p: f"{p}-key-{tag}".encode() for p in PROVS}

def test_basic_user_roundtrip():
    print("== basic: user roundtrip")
    uid, _ = _fresh_ids()
    keys = _keys("AAA")
    for p, k in keys.items():
        store.put_user_key(uid, p, k)
    got = {p: store.get_user_key(uid, p) for p in PROVS}
    assert set(got.keys()) == set(PROVS)
    for p in PROVS:
        assert got[p] == keys[p], f"user key mismatch for {p}"
    print("  OK")

def test_basic_server_roundtrip():
    print("== basic: server roundtrip")
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
    print("  OK")

def test_concurrent_user_puts_last_wins_no_corruption():
    print("== concurrent: user puts (last-writer-wins, no corruption)")
    uid, _ = _fresh_ids()
    keys1 = _keys("AAA")
    keys2 = _keys("BBB")

    def writer(keys):
        for p, k in keys.items():
            store.put_user_key(uid, p, k)

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(writer, keys1), ex.submit(writer, keys2)]
        for _ in as_completed(futs):
            pass

    got = {p: store.get_user_key(uid, p) for p in PROVS}
    assert set(got.keys()) == set(PROVS), f"missing providers after race: {got.keys()}"
    ok_all_aaa = all(got[p] == keys1[p] for p in PROVS)
    ok_all_bbb = all(got[p] == keys2[p] for p in PROVS)
    assert ok_all_aaa or ok_all_bbb, "mixed partial write detected (should be atomic per write)"
    print("  OK")

def test_concurrent_server_puts_last_wins_no_corruption():
    print("== concurrent: server puts (last-writer-wins, no corruption)")
    _, gid = _fresh_ids()
    keys1 = _keys("AAA")
    keys2 = _keys("BBB")

    def writer(keys):
        for p, k in keys.items():
            store.put_server_key(gid, p, k)

    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(writer, keys1), ex.submit(writer, keys2), ex.submit(writer, keys1)]
        for _ in as_completed(futs):
            pass

    got = store.get_server_keys(gid)
    assert set(got.keys()) == set(PROVS), f"missing providers after race: {got.keys()}"
    ok_all_aaa = all(got[p] == keys1[p] for p in PROVS)
    ok_all_bbb = all(got[p] == keys2[p] for p in PROVS)
    assert ok_all_aaa or ok_all_bbb, "mixed partial write detected (should be atomic per write)"
    print("  OK")

def main():
    try:
        print("Secret backend:", store.backend_name())
    except Exception:
        pass
    test_basic_user_roundtrip()
    test_basic_server_roundtrip()
    test_concurrent_user_puts_last_wins_no_corruption()
    test_concurrent_server_puts_last_wins_no_corruption()
    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    main()
