"""Live web search for up-to-date legal and regulatory information."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

MAX_RESULTS = int(os.getenv("LIVE_SEARCH_MAX_RESULTS", "5"))


def _live_search_enabled() -> bool:
    return os.getenv("ENABLE_LIVE_SEARCH", "true").lower() in {"1", "true", "yes", "on"}


def _search_sync(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS

    year = datetime.now().year
    enriched_query = f"{query} luật pháp {year}"
    with DDGS() as ddgs:
        return list(ddgs.text(enriched_query, max_results=max_results))


def _format_results(query: str, results: list[dict]) -> str:
    if not results:
        return (
            f"Không tìm thấy kết quả web cho: {query}\n"
            "Hãy dựa vào kiến thức nội bộ và ghi rõ giới hạn thời gian."
        )

    today = datetime.now().strftime("%d/%m/%Y")
    lines = [
        f"[Tra cứu internet — {today}]",
        f"Từ khóa: {query}",
        "",
    ]
    for idx, item in enumerate(results, start=1):
        title = (item.get("title") or "Không có tiêu đề").strip()
        body = (item.get("body") or "").strip()
        href = (item.get("href") or "").strip()
        lines.append(f"{idx}. **{title}**")
        if body:
            lines.append(f"   {body[:400]}{'…' if len(body) > 400 else ''}")
        if href:
            lines.append(f"   Nguồn: {href}")
        lines.append("")
    lines.append(
        "Lưu ý: Đối chiếu nhiều nguồn; ưu tiên văn bản chính thức (luatvietnam, thuvienphapluat, "
        "cổng Chính phủ, cơ quan nhà nước)."
    )
    return "\n".join(lines)


async def fetch_latest_context(query: str, max_results: int | None = None) -> str:
    """Search the web for the latest information related to a legal query."""
    if not _live_search_enabled():
        return "Tra cứu internet đang tắt (ENABLE_LIVE_SEARCH=false)."

    limit = max_results or MAX_RESULTS
    try:
        results = await asyncio.to_thread(_search_sync, query, limit)
        return _format_results(query, results)
    except Exception as exc:
        logger.warning("Live search failed for %r: %s", query, exc)
        return (
            f"Không thể tra cứu internet lúc này ({exc}). "
            "Tiếp tục phân tích dựa trên kiến thức có sẵn và ghi rõ giới hạn."
        )
