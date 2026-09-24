"""两级缓存：进程内 LRU（热数据，毫秒级）+ SQLite（跨进程/重启保留，带 TTL）。"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class MemoryLRU:
    """带过期时间的进程内 LRU 缓存。"""

    def __init__(self, capacity: int = 256) -> None:
        self.capacity = max(0, capacity)
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """读取并刷新 LRU 顺序；过期返回 None。"""
        if self.capacity == 0:
            return None
        async with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at and expires_at < time.time():
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """写入并处理容量淘汰。"""
        if self.capacity == 0:
            return
        expires_at = time.time() + ttl if ttl > 0 else 0.0
        async with self._lock:
            self._data[key] = (expires_at, value)
            self._data.move_to_end(key)
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


class CacheStore:
    """SQLite 键值缓存，值统一以 JSON 文本存储。"""

    def __init__(self, path: str, *, enabled: bool = True, memory_size: int = 256) -> None:
        self.path = path
        self.enabled = enabled
        self.memory = MemoryLRU(memory_size)
        self._db: aiosqlite.Connection | None = None
        self._write_count = 0

    async def open(self) -> None:
        """建立连接并建表（WAL 模式，兼顾并发与落盘速度）。"""
        if not self.enabled or self._db is not None:
            return
        db_path = Path(self.path)
        if db_path.parent and str(db_path.parent) not in ("", "."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS kv ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT NOT NULL,"
            "  expires_at REAL NOT NULL"
            ")"
        )
        await self._db.commit()

    async def close(self) -> None:
        """关闭连接。"""
        if self._db is not None:
            await self._db.close()
            self._db = None
        await self.memory.clear()

    async def get(self, key: str) -> Any | None:
        """按 key 读取；先查内存再查 SQLite。"""
        if not self.enabled:
            return None
        # 1) 内存命中：最常见的重复查询走这里，耗时 < 1ms
        mem_value = await self.memory.get(key)
        if mem_value is not None:
            return mem_value
        if self._db is None:
            return None
        try:
            async with self._db.execute(
                "SELECT value, expires_at FROM kv WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
        except Exception as exc:  # 缓存异常不应影响主流程
            logger.warning("缓存读取失败 key=%s: %s", key, exc)
            return None
        if row is None:
            return None
        value_text, expires_at = row
        if expires_at and expires_at < time.time():
            await self._delete(key)
            return None
        try:
            value = json.loads(value_text)
        except json.JSONDecodeError:
            await self._delete(key)
            return None
        await self.memory.set(key, value, max(1, int(expires_at - time.time())))
        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """写入缓存（ttl<=0 表示不缓存）。"""
        if not self.enabled or ttl <= 0:
            return
        await self.memory.set(key, value, ttl)
        if self._db is None:
            return
        expires_at = time.time() + ttl
        try:
            await self._db.execute(
                "INSERT INTO kv(key, value, expires_at) VALUES(?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at",
                (key, json.dumps(value, ensure_ascii=False), expires_at),
            )
            self._write_count += 1
            # 每 100 次写入清理一次过期条目，避免表无限增长
            if self._write_count % 100 == 0:
                await self._db.execute("DELETE FROM kv WHERE expires_at < ?", (time.time(),))
            await self._db.commit()
        except Exception as exc:  # 写缓存失败不影响返回结果
            logger.warning("缓存写入失败 key=%s: %s", key, exc)

    async def _delete(self, key: str) -> None:
        """删除单个 key。"""
        if self._db is None:
            return
        try:
            await self._db.execute("DELETE FROM kv WHERE key = ?", (key,))
            await self._db.commit()
        except Exception as exc:
            logger.warning("缓存删除失败 key=%s: %s", key, exc)

    async def purge_expired(self) -> int:
        """清理全部过期条目，返回删除数量。"""
        if self._db is None:
            return 0
        cursor = await self._db.execute("DELETE FROM kv WHERE expires_at < ?", (time.time(),))
        await self._db.commit()
        return cursor.rowcount or 0

    async def count(self) -> int:
        """当前缓存条目数（用于健康检查与基准报告）。"""
        if self._db is None:
            return 0
        async with self._db.execute("SELECT COUNT(*) FROM kv") as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row else 0