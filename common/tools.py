"""Shared LangChain tools for all agents."""

from __future__ import annotations

from langchain_core.tools import tool

from common.live_search import fetch_latest_context


@tool
async def search_latest_legal_info(query: str) -> str:
    """Tra cứu thông tin pháp lý mới nhất trên internet.

    Dùng khi cần luật, nghị định, thông tư, án lệ hoặc tin tức pháp lý
    cập nhật đến thời điểm hiện tại (không có trong dữ liệu training cũ).

    Args:
        query: Chủ đề hoặc câu hỏi pháp lý cần tra cứu (tiếng Việt hoặc tiếng Anh).
    """
    return await fetch_latest_context(query)
