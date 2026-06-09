"""Customer Agent LangGraph definition.

Uses create_react_agent with a `delegate_to_legal_agent` tool that:
1. Discovers the Law Agent via the registry
2. Sends the question to it via A2A
3. Returns the comprehensive legal response to the user

Conversation history is persisted via LangGraph MemorySaver (thread_id = context_id).
"""

from __future__ import annotations

import logging

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from common.datetime_context import datetime_context
from common.llm import get_llm, language_instruction
from common.tools import search_latest_legal_info
from customer_agent.context import context_id_var, depth_var, trace_id_var
from customer_agent.memory import checkpointer

logger = logging.getLogger(__name__)

def _customer_system_prompt() -> str:
    return f"""You are a helpful legal assistant at the front desk of a multi-agent
legal services platform. Your job is to:

1. Understand the user's legal question, including follow-ups in an ongoing conversation.
2. Use prior messages in this thread when the user refers to earlier answers
   (e.g. "giải thích thêm", "phần thuế", "tóm tắt lại").
3. Khi cần luật/nghị định/thông tư MỚI NHẤT, gọi `search_latest_legal_info` trước
   để tra cứu internet cập nhật đến thời điểm hiện tại.
4. For a substantive NEW legal topic, use `delegate_to_legal_agent` EXACTLY ONCE to get
   specialist analysis from the Law Agent network (kèm ngữ cảnh từ tra cứu nếu có).
5. For follow-ups that only need clarification of an answer you already have in this thread,
   respond directly without calling delegate again.
6. Present responses clearly to the user, trích dẫn nguồn khi dùng dữ liệu web.

CRITICAL:
- Do NOT call `delegate_to_legal_agent` more than once per user message.
- After receiving a tool result, summarize it for the user and stop.
- {datetime_context()}
- {language_instruction()}
"""


@tool
async def delegate_to_legal_agent(question: str) -> str:
    """Send a legal question to the Law Agent for comprehensive analysis.

    The Law Agent will coordinate Tax and Compliance sub-agents in parallel
    and return a synthesised response covering all relevant legal dimensions.

    Args:
        question: The legal question to analyse (include brief prior context if needed).

    Returns:
        A comprehensive legal analysis from the multi-agent system.
    """
    from common.a2a_client import delegate
    from common.registry_client import discover

    trace_id = trace_id_var.get()
    context_id = context_id_var.get()
    depth = depth_var.get()

    logger.info(
        "Customer delegate_to_legal_agent | trace=%s context=%s depth=%d",
        trace_id, context_id, depth,
    )

    try:
        endpoint = await discover("legal_question")
        result = await delegate(
            endpoint=endpoint,
            question=question,
            context_id=context_id,
            trace_id=trace_id,
            depth=depth + 1,
        )
        if not result:
            return "The Law Agent returned an empty response. Please try again."
        return result
    except Exception as exc:
        logger.exception("delegate_to_legal_agent failed: %s", exc)
        return f"Could not reach the Law Agent: {exc}"


def create_graph():
    """Build and compile the Customer Agent graph with conversation memory."""
    llm = get_llm()
    return create_react_agent(
        model=llm,
        tools=[search_latest_legal_info, delegate_to_legal_agent],
        prompt=_customer_system_prompt(),
        checkpointer=checkpointer,
    )


# Single compiled graph shared across requests (memory via thread_id)
_graph = create_graph()


def get_graph():
    return _graph
