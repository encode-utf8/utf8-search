"""正文抽取测试：句子压缩 + 抓取/缓存链路（用 respx 模拟网络）。"""

from __future__ import annotations

import httpx
import respx

from utf8_search.cache.store import CacheStore
from utf8_search.extract.extractor import PageExtractor, condense_text

ARTICLE = (
    "<html><head><title>示例标题</title></head><body><article>"
    + "<p>这是一段与主题无关的寒暄内容，用来占位。</p>"
    + "<p>OpenAI 发布了 GPT-6 模型，上下文窗口大幅提升，价格下降三成。</p>"
    + "<p>另一段无关内容，天气不错，适合散步。</p>"
    * 6
    + "</article></body></html>"
)


def test_condense_keeps_query_relevant_sentences() -> None:
    """压缩后应保留与查询相关的句子，并遵守长度上限。"""
    text = "无关内容。" * 50 + "OpenAI 发布 GPT-6，价格下降。" + "无关内容。" * 50
    condensed = condense_text(text, "GPT-6 价格", 120)
    assert len(condensed) <= 120
    assert "GPT-6" in condensed


def test_condense_falls_back_to_head_when_no_terms() -> None:
    text = "句子一。" * 100
    assert condense_text(text, "", 50) == text[:50]


@respx.mock
async def test_extractor_uses_cache_on_second_call(settings, tmp_path) -> None:
    """首次抓取走网络，第二次应命中页面缓存。"""
    route = respx.get("https://example.com/page").mock(
        return_value=httpx.Response(
            200, text=ARTICLE, headers={"content-type": "text/html; charset=utf-8"}
        )
    )
    cache = CacheStore(str(tmp_path / "c.db"))
    await cache.open()
    async with httpx.AsyncClient() as client:
        extractor = PageExtractor(settings, client, cache)
        first = await extractor.extract("https://example.com/page", fmt="text", max_chars=500, query="GPT-6")
        assert first is not None and first.raw_content
        assert "GPT-6" in first.raw_content
        assert route.call_count == 1

        second = await extractor.extract("https://example.com/page", fmt="text", max_chars=500, query="GPT-6")
        assert second is not None
        assert route.call_count == 1  # 命中缓存，没有再次请求
    await cache.close()


@respx.mock
async def test_extractor_returns_none_on_http_error(settings, tmp_path) -> None:
    """目标页面返回 5xx 时返回 None，不抛异常。"""
    respx.get("https://example.com/broken").mock(return_value=httpx.Response(503))
    cache = CacheStore(str(tmp_path / "c.db"))
    await cache.open()
    async with httpx.AsyncClient() as client:
        extractor = PageExtractor(settings, client, cache)
        assert await extractor.extract("https://example.com/broken") is None
    await cache.close()