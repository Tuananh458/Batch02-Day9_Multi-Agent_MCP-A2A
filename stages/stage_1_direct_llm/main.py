"""Stage 1: Gọi LLM trực tiếp

Cách đơn giản nhất dùng LLM — gửi message, nhận response.
Không tools, không memory, không agent. Chỉ là một API call.

Stateless: LLM không truy cập nguồn dữ liệu bên ngoài,
không tra cứu được, chỉ dựa vào dữ liệu training.
"""

import asyncio
import os
import sys

# Allow running directly: python stages/stage_1_direct_llm/main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from common.llm import get_llm, language_instruction

QUESTION = (
    "Công ty vi phạm thỏa thuận bảo mật thông tin (NDA) thì chịu "
    "hậu quả pháp lý gì?"
)


async def main():
    print("=" * 70)
    print("STAGE 1: Gọi LLM trực tiếp (Direct LLM Calling)")
    print("=" * 70)
    print()
    print("[Cách hoạt động]")
    print("  1. Gửi system prompt + câu hỏi trực tiếp tới LLM")
    print("  2. LLM trả lời chỉ dựa trên dữ liệu training")
    print("  3. Không tools, không retrieval, không kiến thức ngoài")
    print()
    print(f"Câu hỏi: {QUESTION}")
    print("-" * 70)

    llm = get_llm()

    messages = [
        SystemMessage(
            content=(
                "Bạn là chuyên gia pháp lý. Phân tích rõ ràng, súc tích "
                "câu hỏi pháp lý được đặt ra. Giữ câu trả lời dưới 300 từ. "
                f"{language_instruction()}"
            )
        ),
        HumanMessage(content=QUESTION),
    ]

    print("\n>>> Đang gọi LLM trực tiếp (không tools, không RAG)...\n")
    response = await llm.ainvoke(messages)
    print(response.content)

    print()
    print("-" * 70)
    print("[Hạn chế của Stage 1]")
    print("  - Stateless: không nhớ hội thoại giữa các lần gọi")
    print("  - Không tools: không tra cứu database hay tính thiệt hại")
    print("  - Knowledge cutoff: chỉ biết dữ liệu trong training")
    print("  - Không grounding: khó trích dẫn điều luật/án lệ cụ thể")
    print()
    print("Tiếp theo: Stage 2 thêm RAG và tools để căn cứ vào dữ liệu thực.")
    print("=" * 70)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
