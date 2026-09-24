"""Bing 结果页解析测试（离线，使用样例 HTML）。"""

from __future__ import annotations

from utf8_search.providers.bing_html import BingHtmlProvider, _unwrap_bing_redirect

SAMPLE = """
<html><body><ol id="b_results">
  <li class="b_algo"><h2><a href="https://www.example.com/first">第一个结果标题</a></h2>
      <div class="b_caption"><p>这里是第一条摘要内容。</p></div></li>
  <li class="b_algo"><h2><a href="https://www.example.com/second">第二个结果标题</a></h2>
      <p>第二条摘要。</p></li>
  <li class="b_ans">不是搜索结果</li>
</ol></body></html>
"""


def test_parse_extracts_results() -> None:
    """应只解析 b_algo 块，并正确取出标题/链接/摘要。"""
    hits = BingHtmlProvider.parse(SAMPLE, max_results=10)
    assert [h.title for h in hits] == ["第一个结果标题", "第二个结果标题"]
    assert hits[0].url == "https://www.example.com/first"
    assert "第一条摘要内容" in hits[0].snippet
    assert hits[0].engine == "bing"


def test_parse_respects_max_results() -> None:
    assert len(BingHtmlProvider.parse(SAMPLE, max_results=1)) == 1


def test_unwrap_redirect_keeps_normal_url() -> None:
    assert _unwrap_bing_redirect("https://example.com/a") == "https://example.com/a"