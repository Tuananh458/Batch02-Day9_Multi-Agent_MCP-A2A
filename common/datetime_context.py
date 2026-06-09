"""Current date/time context for grounding agent responses."""

from datetime import datetime


def datetime_context() -> str:
    """Return a Vietnamese date stamp for system prompts."""
    now = datetime.now()
    return (
        f"Hôm nay là {now.strftime('%d/%m/%Y')} "
        f"(năm {now.year}). Ưu tiên thông tin cập nhật đến thời điểm hiện tại."
    )
