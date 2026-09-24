"""Provider 抽象：所有搜索源实现同一套接口，便于替换与降级。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchHit:
    """上游返回的一条原始结果。"""

    title: str = ""
    url: str = ""
    snippet: str = ""
    engine: str = ""
    published_date: str | None = None
    raw_score: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseProvider(ABC):
    """搜索源接口。"""

    name: str = "base"

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        max_results: int,
        topic: str = "general",
        time_range: str | None = None,
        engines: list[str] | None = None,
        language: str = "all",
    ) -> list[SearchHit]:
        """执行一次搜索，返回原始结果列表。失败时应抛出异常，由上层决定降级。"""

    async def health(self) -> bool:
        """健康检查：默认返回 True，具体实现可覆盖。"""
        return True