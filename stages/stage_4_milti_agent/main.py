"""Stage 4: Multi-Agent System (In-Process)

Multiple specialised agents collaborate on a complex legal question.
This mirrors Stage 5's architecture (law_agent/graph.py) but runs
entirely in-process — no HTTP, no A2A protocol, no separate servers.

Graph: analyze_law -> check_routing -> parallel [call_tax, call_compliance] -> aggregate -> END
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from common.llm import get_llm, language_instruction

# ---------------------------------------------------------------------------
# Tools for specialist sub-agents (Công cụ cho các tiểu agent chuyên gia)
# ---------------------------------------------------------------------------

@tool
def search_tax_law(query: str) -> str:
    """Tìm kiếm trong cơ sở dữ liệu luật thuế về các quy định và hình phạt liên quan.

    Args:
        query: Câu truy vấn bằng ngôn ngữ tự nhiên về luật thuế.
    """
    knowledge = [
        (
            ["tax", "evasion", "fraud", "irs", "thuế", "trốn thuế", "gian lận"],
            "Tax evasion (26 U.S.C. § 7201): felony, up to $250K fine and 5 years prison. "
            "Civil fraud penalty: 75% of underpayment (IRC § 6663). Failure to file: up to "
            "$25K fine and 1 year prison.",
        ),
        (
            ["offshore", "overseas", "foreign", "fbar", "fatca", "nước ngoài", "ngoài nước"],
            "FBAR penalties: up to $100K or 50% of account balance per violation. "
            "FATCA non-compliance: 30% withholding on US-source payments. "
            "Willful violations may trigger criminal prosecution.",
        ),
        (
            ["transfer", "pricing", "corporate", "chuyển giá"],
            "Transfer pricing violations (IRC § 482): IRS can reallocate income between "
            "related entities. Penalties: 20-40% of underpayment for substantial/gross "
            "valuation misstatements.",
        ),
    ]
    query_lower = query.lower()
    results = []
    for keywords, text in knowledge:
        if any(kw in query_lower for kw in keywords):
            results.append(text)
    return "\n\n".join(results) if results else "Không tìm thấy điều luật thuế cụ thể nào phù hợp."


@tool
def search_compliance_law(query: str) -> str:
    """Tìm kiếm trong cơ sở dữ liệu luật tuân thủ về các khung quy định và vi phạm của doanh nghiệp.

    Args:
        query: Câu truy vấn bằng ngôn ngữ tự nhiên về luật tuân thủ doanh nghiệp.
    """
    knowledge = [
        (
            ["sox", "sarbanes", "financial", "sec", "reporting", "tài chính", "báo cáo"],
            "SOX § 906: false certification — up to $5M fine, 20 years prison. "
            "§ 802: record destruction — up to 20 years. § 1107: whistleblower "
            "retaliation — up to 10 years. SEC officer/director bars.",
        ),
        (
            ["fcpa", "bribery", "corruption", "foreign", "hối lộ", "tham nhũng"],
            "FCPA anti-bribery: up to $250K fine per violation (individuals), "
            "$2M (corporations). Criminal penalties: up to 5 years prison. "
            "Books and records provisions apply to all SEC-reporting companies.",
        ),
    ]
    query_lower = query.lower()
    results = []
    for keywords, text in knowledge:
        if any(kw in query_lower for kw in keywords):
            results.append(text)
    return "\n\n".join(results) if results else "Không tìm thấy điều luật tuân thủ doanh nghiệp nào phù hợp."


@tool
def search_privacy_law(query: str) -> str:
    """Tìm kiếm trong cơ sở dữ liệu luật bảo mật và quyền riêng tư (GDPR, CCPA) về các vi phạm dữ liệu.

    Args:
        query: Câu truy vấn bằng ngôn ngữ tự nhiên về bảo mật dữ liệu và quyền riêng tư.
    """
    knowledge = [
        (
            ["data", "privacy", "gdpr", "ccpa", "consent", "user", "dữ liệu", "riêng tư", "bảo mật", "rò rỉ"],
            "CCPA: fines up to $7,500 per intentional violation. GDPR: up to 4% of global "
            "revenue or EUR 20M. FTC Act Section 5 for unfair/deceptive practices. "
            "Class action exposure under state privacy laws ($100-$750 per consumer).",
        ),
    ]
    query_lower = query.lower()
    results = []
    for keywords, text in knowledge:
        if any(kw in query_lower for kw in keywords):
            results.append(text)
    return "\n\n".join(results) if results else "Không tìm thấy quy định bảo mật thông tin nào phù hợp."


# ---------------------------------------------------------------------------
# State definition (Định nghĩa trạng thái của Graph)
# ---------------------------------------------------------------------------

from typing import Annotated, TypedDict

from langgraph.constants import Send
from langgraph.graph import END, StateGraph


def _last_wins(a: str, b: str) -> str:
    """Reducer: giữ lại giá trị được ghi gần đây nhất."""
    return b if b else a


class LegalState(TypedDict):
    question: str
    law_analysis: str
    needs_tax: bool
    needs_compliance: bool
    needs_privacy: bool
    tax_result: Annotated[str, _last_wins]
    compliance_result: Annotated[str, _last_wins]
    privacy_result: Annotated[str, _last_wins]
    final_answer: str


# ---------------------------------------------------------------------------
# Node implementations (Triển khai các Node xử lý)
# ---------------------------------------------------------------------------

async def analyze_law(state: LegalState) -> dict:
    """Luật sư trưởng phân tích khía cạnh pháp lý tổng quát của câu hỏi."""
    print("\n  [Node: analyze_law] Luật sư trưởng đang phân tích khía cạnh pháp lý chung...")
    llm = get_llm()
    messages = [
        SystemMessage(
            content=(
                "Bạn là luật sư trưởng chuyên về luật kinh doanh và hợp đồng. Hãy phân tích các khía cạnh pháp lý chung "
                "của câu hỏi một cách rõ ràng. Giới hạn câu trả lời dưới 200 từ."
            )
        ),
        HumanMessage(content=state["question"]),
    ]
    result = await llm.ainvoke(messages)
    print(f"  [Node: analyze_law] Hoàn thành ({len(result.content)} ký tự)")
    return {"law_analysis": result.content}


async def check_routing(state: LegalState) -> dict:
    """Node phân loại định tuyến: quyết định xem các chuyên gia nào cần tham gia."""
    print("\n  [Node: check_routing] Đang xác định các chuyên gia cần thiết...")
    llm = get_llm()
    messages = [
        SystemMessage(
            content=(
                "Bạn là chuyên gia định tuyến hồ sơ pháp lý. Dựa trên câu hỏi và phân tích pháp lý chung, hãy quyết định chuyên gia nào cần tham gia.\n"
                "Trả về duy nhất định dạng JSON hợp lệ — không kèm markdown, không kèm văn bản giải thích phụ:\n"
                '{"needs_tax": <true|false>, "needs_compliance": <true|false>, "needs_privacy": <true|false>}\n\n'
                "needs_tax = true -> câu hỏi liên quan đến thuế, IRS, trốn thuế, phạt thuế quan\n"
                "needs_compliance = true -> câu hỏi liên quan đến tuân thủ tài chính, SEC, SOX, phòng chống hối lộ (FCPA)\n"
                "needs_privacy = true -> câu hỏi liên quan đến bảo mật thông tin khách hàng, rò rỉ dữ liệu, GDPR, CCPA, quyền riêng tư"
            )
        ),
        HumanMessage(content=state["question"]),
    ]
    result = await llm.ainvoke(messages)
    raw = result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"needs_tax": True, "needs_compliance": True, "needs_privacy": True}

    needs_tax = bool(parsed.get("needs_tax", True))
    needs_compliance = bool(parsed.get("needs_compliance", True))
    needs_privacy = bool(parsed.get("needs_privacy", True))
    print(f"  [Node: check_routing] needs_tax={needs_tax}, needs_compliance={needs_compliance}, needs_privacy={needs_privacy}")
    return {"needs_tax": needs_tax, "needs_compliance": needs_compliance, "needs_privacy": needs_privacy}


def route_to_specialists(state: LegalState) -> list[Send]:
    """Hàm định hướng luồng: gửi đồng thời các đối tượng Send đến các node chuyên gia tương ứng."""
    sends: list[Send] = []
    if state.get("needs_tax"):
        sends.append(Send("call_tax_specialist", state))
    if state.get("needs_compliance"):
        sends.append(Send("call_compliance_specialist", state))
    if state.get("needs_privacy"):
        sends.append(Send("call_privacy_specialist", state))
    if not sends:
        sends.append(Send("aggregate", state))
    return sends


async def call_tax_specialist(state: LegalState) -> dict:
    """Chuyên gia thuế (chạy dưới dạng inline ReAct agent)."""
    from langgraph.prebuilt import create_react_agent

    print("\n  [Node: call_tax_specialist] Khởi động agent chuyên gia thuế...")

    tax_prompt = (
        "Bạn là luật sư chuyên gia về thuế và kiểm toán viên CPA. Hãy phân tích chuyên sâu các khía cạnh về thuế, "
        "IRS, trốn thuế, các mức phạt dân sự và hình sự liên quan. "
        "Sử dụng công cụ search_tax_law để tra cứu thông tin chính xác. Giới hạn câu trả lời dưới 200 từ."
    )

    llm = get_llm()
    agent = create_react_agent(model=llm, tools=[search_tax_law], prompt=tax_prompt)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": state["question"]}]})

    final_msg = result["messages"][-1].content
    print(f"  [Node: call_tax_specialist] Hoàn thành ({len(final_msg)} ký tự)")
    return {"tax_result": final_msg}


async def call_compliance_specialist(state: LegalState) -> dict:
    """Chuyên gia tuân thủ doanh nghiệp (chạy dưới dạng inline ReAct agent)."""
    from langgraph.prebuilt import create_react_agent

    print("\n  [Node: call_compliance_specialist] Khởi động agent chuyên gia tuân thủ...")

    compliance_prompt = (
        "Bạn là chuyên viên tuân thủ quy chế doanh nghiệp cấp cao. Hãy phân tích các khía cạnh tuân thủ SEC, SOX, "
        "chống tham nhũng/hối lộ FCPA, rửa tiền và quản trị doanh nghiệp. "
        "Sử dụng công cụ search_compliance_law để tra cứu chính xác. Giới hạn câu trả lời dưới 200 từ."
    )

    llm = get_llm()
    agent = create_react_agent(model=llm, tools=[search_compliance_law], prompt=compliance_prompt)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": state["question"]}]})

    final_msg = result["messages"][-1].content
    print(f"  [Node: call_compliance_specialist] Hoàn thành ({len(final_msg)} ký tự)")
    return {"compliance_result": final_msg}


async def call_privacy_specialist(state: LegalState) -> dict:
    """Chuyên gia bảo mật thông tin và quyền riêng tư (chạy dưới dạng inline ReAct agent)."""
    from langgraph.prebuilt import create_react_agent

    print("\n  [Node: call_privacy_specialist] Khởi động agent chuyên gia bảo mật dữ liệu...")

    privacy_prompt = (
        "Bạn là luật sư chuyên gia về bảo mật thông tin và quyền riêng tư (GDPR, CCPA/CPRA, Luật FTC). "
        "Hãy phân tích các hành vi rò rỉ dữ liệu cá nhân, yêu cầu sự đồng ý của người dùng và các chế tài tài chính liên quan. "
        "Sử dụng công cụ search_privacy_law để tra cứu chính xác. Giới hạn câu trả lời dưới 200 từ."
    )

    llm = get_llm()
    agent = create_react_agent(model=llm, tools=[search_privacy_law], prompt=privacy_prompt)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": state["question"]}]})

    final_msg = result["messages"][-1].content
    print(f"  [Node: call_privacy_specialist] Hoàn thành ({len(final_msg)} ký tự)")
    return {"privacy_result": final_msg}


async def aggregate(state: LegalState) -> dict:
    """Tổng hợp phân tích của tất cả các chuyên gia thành câu trả lời hoàn chỉnh."""
    print("\n  [Node: aggregate] Đang tổng hợp phân tích từ các chuyên gia...")
    llm = get_llm()

    sections: list[str] = []
    if state.get("law_analysis"):
        sections.append(f"## Phân Tích Pháp Lý Chung (Luật Sư Trưởng)\n{state['law_analysis']}")
    if state.get("tax_result"):
        sections.append(f"## Phân Tích Khía Cạnh Thuế (Chuyên Gia Thuế)\n{state['tax_result']}")
    if state.get("compliance_result"):
        sections.append(f"## Phân Tích Khía Cạnh Tuân Thủ Doanh Nghiệp (Chuyên Gia Tuân Thủ)\n{state['compliance_result']}")
    if state.get("privacy_result"):
        sections.append(f"## Phân Tích Khía Cạnh Bảo Mật & Quyền Riêng Tư (Chuyên Gia Bảo Mật)\n{state['privacy_result']}")

    combined = "\n\n---\n\n".join(sections)

    messages = [
        SystemMessage(
            content=(
                "Bạn là luật sư trưởng điều hành, nhiệm vụ của bạn là tổng hợp các ý kiến chuyên gia pháp lý "
                "thành một báo cáo phân tích rủi ro pháp lý toàn diện, mạch lạc, có cấu trúc rõ ràng. Tránh lặp lại ý. "
                "Giới hạn câu trả lời dưới 500 từ. "
                f"{language_instruction()}"
            )
        ),
        HumanMessage(content=combined),
    ]
    result = await llm.ainvoke(messages)
    print(f"  [Node: aggregate] Hoàn thành ({len(result.content)} ký tự)")
    return {"final_answer": result.content}


# ---------------------------------------------------------------------------
# Graph construction (Xây dựng cấu trúc StateGraph)
# ---------------------------------------------------------------------------

def create_graph():
    """Tạo lập và biên dịch luồng StateGraph đa tác tử (Multi-Agent)."""
    graph = StateGraph(LegalState)

    graph.add_node("analyze_law", analyze_law)
    graph.add_node("check_routing", check_routing)
    graph.add_node("call_tax_specialist", call_tax_specialist)
    graph.add_node("call_compliance_specialist", call_compliance_specialist)
    graph.add_node("call_privacy_specialist", call_privacy_specialist)
    graph.add_node("aggregate", aggregate)

    graph.set_entry_point("analyze_law")
    graph.add_edge("analyze_law", "check_routing")
    graph.add_conditional_edges(
        "check_routing",
        route_to_specialists,
        ["call_tax_specialist", "call_compliance_specialist", "call_privacy_specialist", "aggregate"],
    )
    graph.add_edge("call_tax_specialist", "aggregate")
    graph.add_edge("call_compliance_specialist", "aggregate")
    graph.add_edge("call_privacy_specialist", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()


# Câu hỏi phức tạp đa lĩnh vực (Luật hợp đồng + Thuế trốn tránh + Bảo mật rò rỉ dữ liệu)
QUESTION = (
    "Một startup công nghệ vi phạm hợp đồng dịch vụ đám mây, đồng thời bị phát hiện trốn thuế "
    "doanh thu nước ngoài và chia sẻ dữ liệu người dùng không xin phép đối tác. Hậu quả pháp lý là gì?"
)


async def main():
    print("=" * 70)
    print("STAGE 4: Hệ Thống Multi-Agent (In-Process)")
    print("=" * 70)
    print()
    print("[Cách hoạt động]")
    print("  1. Luật sư trưởng phân tích sơ bộ câu hỏi")
    print("  2. Node định tuyến quyết định các chuyên gia nào cần tham gia")
    print("  3. Các chuyên gia (Thuế, Tuân thủ, Bảo mật) chạy SONG SONG (Sử dụng Send API)")
    print("  4. Luật sư trưởng tổng hợp ý kiến thành báo cáo pháp lý cuối cùng")
    print()
    print("[Cấu trúc đồ thị - Graph Topology]")
    print("  analyze_law -> check_routing -> [call_tax + call_compliance + call_privacy] -> aggregate -> END")
    print()
    print(f"Câu hỏi: {QUESTION}")
    print("-" * 70)

    graph = create_graph()

    result = await graph.ainvoke({
        "question": QUESTION,
        "law_analysis": "",
        "needs_tax": False,
        "needs_compliance": False,
        "needs_privacy": False,
        "tax_result": "",
        "compliance_result": "",
        "privacy_result": "",
        "final_answer": "",
    })

    print("\n" + "=" * 70)
    print("BÁO CÁO PHÁP LÝ CUỐI CÙNG")
    print("=" * 70)
    print(result["final_answer"])

    print()
    print("-" * 70)
    print("[Những điểm cải tiến so với Stage 3]")
    print("  + Chuyên môn hóa (Specialisation): mỗi agent có hệ thống prompt và công cụ chuyên biệt sâu")
    print("  + Chạy song song (Parallel execution): các agent chạy độc lập đồng thời nâng cao hiệu suất")
    print("  + Chất lượng cao hơn: sự phân rã giúp LLM đưa ra câu trả lời sâu sắc hơn")
    print("  + Quy trình rõ ràng: luồng điều khiển chặt chẽ thông qua thiết kế StateGraph")
    print()
    print("[So sánh Stage 4 (Nguyên khối) và Stage 5 (Phân tán A2A)]")
    print("  +---------------------------+-------------------------------+")
    print("  | Stage 4 (In-Process)      | Stage 5 (A2A Protocol)        |")
    print("  +---------------------------+-------------------------------+")
    print("  | Chạy trên 1 tiến trình    | Nhiều micro-service độc lập   |")
    print("  | Gọi hàm trực tiếp         | Truyền tin qua giao thức HTTP |")
    print("  | Chia sẻ bộ nhớ trong      | Độc lập tài nguyên hoàn toàn  |")
    print("  | Dễ triển khai thử nghiệm  | Có thể mở rộng quy mô (Scale) |")
    print("  +---------------------------+-------------------------------+")
    print()
    print("Stage 5 sử dụng giao thức A2A để tách rời các agent này thành các thực thể độc lập.")
    print("=" * 70)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())