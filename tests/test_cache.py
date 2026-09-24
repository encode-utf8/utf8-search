"""缓存层测试：内存 LRU、SQLite 落盘与过期。"""

from __future__ import annotations

import asyncio

from utf8_search.cache.store import CacheStore


async def test_cache_roundtrip_and_memory_hit(tmp_path) -> None:
    """写入后应能读到；第二次读取应命中内存（SQLite 不再被查询）。"""
    cache = CacheStore(str(tmp_path / "c.db"), memory_size=8)
    await cache.open()
    await cache.set("k1", {"v": 1}, ttl=60)

    assert await cache.get("k1") == {"v": 1}
    # 清掉 SQLite 中的记录，仍应命中内存，证明走的是 LRU
    await cache._delete("k1")
    assert await cache.get("k1") == {"v": 1}

    await cache.close()


async def test_cache_ttl_expiry(tmp_path) -> None:
    """内存条目过期后返回 None。"""
    cache = CacheStore(str(tmp_path / "c.db"), memory_size=8)
    await cache.open()
    await cache.set("k2", "value", ttl=1)
    await asyncio.sleep(1.05)
    assert await cache.get("k2") is None
    await cache.close()


async def test_cache_disabled(tmp_path) -> None:
    cache = CacheStore(str(tmp_path / "c.db"), enabled=False)
    await cache.open()
    await cache.set("k3", "value", ttl=60)
    assert await cache.get("k3") is None
    await cache.close()


async def test_cache_count(tmp_path) -> None:
    cache = CacheStore(str(tmp_path / "c.db"))
    await cache.open()
    await cache.set("a", 1, ttl=60)
    await cache.set("b", 2, ttl=60)
    assert await cache.count() == 2
    assert await cache.purge_expired() == 0
    await cache.close()