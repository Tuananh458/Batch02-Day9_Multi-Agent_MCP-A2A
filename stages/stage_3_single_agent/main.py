"""Stage 3: Single Agent (ReAct Loop)

Wraps the LLM + tools in an autonomous agent that can reason, act,
and observe in a loop. The agent decides which tools to call, evaluates
the results, and may call more tools before giving a final answer.

Uses LangGraph's create_react_agent for the Think -> Act -> Observe loop.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(r"d:\solution\Day08_RAG_pipeline_cohort2\group_project")
from src.task5_semantic_search import semantic_search

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_core.tools import tool

from common.llm import get_llm, language_instruction

# ---------------------------------------------------------------------------
# Expanded knowledge base (law + tax + compliance entries)
# ---------------------------------------------------------------------------

LEGAL_KNOWLEDGE = [
    {
        "id": "nda_breach",
        "keywords": ["nda", "non-disclosure", "confidential", "trade secret", "breach"],
        "text": (
            "NDA breaches trigger contractual and statutory liability. Under the DTSA "
            "(18 U.S.C. § 1836): injunctive relief, actual damages + unjust enrichment, "
            "exemplary damages up to 2x for willful misappropriation, and attorney's fees. "
            "Criminal prosecution possible under Economic Espionage Act (18 U.S.C. § 1832)."
        ),
    },
    {
        "id": "contract_remedies",
        "keywords": ["breach", "contract", "remedies", "damages", "ucc"],
        "text": (
            "UCC Article 2 remedies: expectation damages, consequential damages (Hadley v. "
            "Baxendale), specific performance for unique goods, cover damages. Statute of "
            "limitations: 4 years (UCC § 2-725)."
        ),
    },
    {
        "id": "tax_evasion",
        "keywords": ["tax", "evasion", "irs", "penalty", "fraud", "revenue"],
        "text": (
            "Tax evasion (26 U.S.C. § 7201): felony with up to $250K fine and 5 years prison. "
            "Civil fraud penalty: 75% of underpayment (IRC § 6663). Failure to file: up to "
            "$25K fine and 1 year prison. IRS can assess back taxes + interest going back 6 years "
            "(unlimited for fraud). Officers may be personally liable as 'responsible persons'."
        ),
    },
    {
        "id": "offshore_tax",
        "keywords": ["offshore", "overseas", "foreign", "tax", "fbar", "fatca"],
        "text": (
            "Unreported overseas income: FBAR penalties up to $100K or 50% of account balance "
            "per violation. FATCA non-compliance: 30% withholding on US-source payments. "
            "Willful violations may trigger criminal prosecution. Voluntary Disclosure Program "
            "may reduce penalties."
        ),
    },
    {
        "id": "data_privacy",
        "keywords": ["data", "privacy", "user", "consent", "gdpr", "ccpa", "sharing"],
        "text": (
            "Sharing user data without consent violates: CCPA (fines up to $7,500 per intentional "
            "violation), GDPR (fines up to 4% of global revenue or EUR 20M), FTC Act Section 5 "
            "(unfair/deceptive practices). Class action lawsuits under state privacy laws. "
            "Individual right of action under CCPA for data breaches ($100-$750 per consumer)."
        ),
    },
    {
        "id": "sox_compliance",
        "keywords": ["sox", "sarbanes", "compliance", "sec", "financial", "reporting"],
        "text": (
            "SOX violations: CEO/CFO certification of false financials — up to $5M fine and "
            "20 years prison (§ 906). Destruction of records — up to 20 years (§ 802). "
            "Whistleblower retaliation — up to 10 years (§ 1107). SEC can bar individuals "
            "from serving as officers or directors."
        ),
    },
]


# ---------------------------------------------------------------------------
# Tools (Công cụ hỗ trợ)
# ---------------------------------------------------------------------------

@tool
def search_legal_database(query: str) -> str:
    """Tìm kiếm trong cơ sở dữ liệu tri thức luật (ChromaDB) từ dự án Day 8."""
    try:
        results = semantic_search(query, top_k=2)
        if not results:
            return "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu luật."
        
        formatted = []
        for r in results:
            source = r['metadata'].get('source', 'unknown')
            formatted.append(f"[Nguồn: {source}] (Score: {r['score']:.4f})\n{r['content']}")
        return "\n\n---\n\n".join(formatted)
    except Exception as e:
        return f"Lỗi khi truy vấn cơ sở dữ liệu: {str(e)}"


@tool
def calculate_penalty(violation_type: str, severity: str, annual_revenue: float) -> str:
    """Tính toán mức phạt pháp lý ước tính dựa trên loại vi phạm, mức độ nghiêm trọng và doanh thu công ty.

    Args:
        violation_type: Loại vi phạm (ví dụ: 'tax_evasion', 'data_privacy', 'contract_breach').
        severity: Mức độ nghiêm trọng ('low', 'medium', 'high').
        annual_revenue: Doanh thu hàng năm của công ty bằng USD.
    """
    severity_multipliers = {"low": 0.01, "medium": 0.05, "high": 0.10}
    multiplier = severity_multipliers.get(severity.lower(), 0.05)

    base_penalty = annual_revenue * multiplier

    type_lower = violation_type.lower()
    if "tax" in type_lower:
        extra = "Có thể bị truy cứu trách nhiệm hình sự (lên đến 5 năm tù) và phạt 75% dân sự do gian lận thuế."
    elif "privacy" in type_lower or "data" in type_lower:
        extra = "Có thể bị phạt thêm theo GDPR lên tới 4% doanh thu toàn cầu và đối mặt vụ kiện tập thể."
    elif "contract" in type_lower:
        extra = "Phải chịu thêm thiệt hại hệ quả, chi phí luật sư và có thể bị lệnh đình chỉ/áp chế."
    else:
        extra = "Có thể áp dụng thêm các biện pháp trừng phạt pháp lý khác."

    return (
        f"Ước tính mức phạt cho {violation_type} (Mức độ nghiêm trọng: {severity}):\n"
        f"  Phạt cơ bản: ${base_penalty:,.2f}\n"
        f"  Doanh thu cơ sở: ${annual_revenue:,.2f}\n"
        f"  Lưu ý thêm: {extra}"
    )


@tool
def check_compliance_requirements(industry: str, company_size: str) -> str:
    """Kiểm tra các khung tuân thủ pháp lý áp dụng cho công ty.

    Args:
        industry: Ngành nghề kinh doanh (ví dụ: 'technology', 'finance', 'healthcare').
        company_size: Quy mô công ty ('startup', 'mid-size', 'enterprise').
    """
    frameworks = {
        "technology": ["CCPA/CPRA", "GDPR (nếu có người dùng EU)", "FTC Act Section 5", "SOC 2"],
        "finance": ["SOX", "BSA/AML", "Dodd-Frank", "Quy định SEC", "FCPA"],
        "healthcare": ["HIPAA", "HITECH Act", "Thông báo vi phạm dữ liệu sức khỏe của FTC", "AKS"],
    }

    size_extras = {
        "startup": "Khuyến nghị: SOC 2 Type II để tăng lòng tin với nhà đầu tư.",
        "mid-size": "Khuyến nghị: Có nhân sự phụ trách tuân thủ chuyên trách và thực hiện kiểm toán hàng năm.",
        "enterprise": "Yêu cầu bắt buộc: Chương trình tuân thủ đầy đủ, giám sát của hội đồng quản trị, đường dây nóng tố giác.",
    }

    industry_lower = industry.lower()
    applicable = frameworks.get(industry_lower, ["FTC Act Section 5", "Luật bảo vệ người tiêu dùng của bang"])
    size_note = size_extras.get(company_size.lower(), "")

    return (
        f"Khung tuân thủ áp dụng cho ngành {industry} ({company_size}):\n"
        f"  {', '.join(applicable)}\n"
        f"  {size_note}"
    )


@tool
def search_case_law(keywords: str) -> str:
    """Tìm kiếm án lệ pháp lý theo từ khóa hoặc chủ đề pháp lý liên quan.

    Args:
        keywords: Từ khóa tìm kiếm án lệ (ví dụ: 'breach', 'contract', 'negligence', 'vi phạm', 'hợp đồng', 'bất cẩn').
    """
    cases = {
        "breach": "Hadley v. Baxendale (1854) - Consequential damages (Thiệt hại hệ quả do vi phạm hợp đồng)",
        "vi phạm": "Hadley v. Baxendale (1854) - Consequential damages (Thiệt hại hệ quả do vi phạm hợp đồng)",
        "negligence": "Donoghue v. Stevenson (1932) - Duty of care (Nghĩa vụ cẩn trọng)",
        "bất cẩn": "Donoghue v. Stevenson (1932) - Duty of care (Nghĩa vụ cẩn trọng)",
        "contract": "Carlill v. Carbolic Smoke Ball Co (1893) - Unilateral contract (Hợp đồng đơn phương)",
        "hợp đồng": "Carlill v. Carbolic Smoke Ball Co (1893) - Unilateral contract (Hợp đồng đơn phương)",
    }
    
    keywords_lower = keywords.lower()
    found_cases = []
    
    for key, case in cases.items():
        if key in keywords_lower:
            found_cases.append(case)
            
    if found_cases:
        return "\n".join(list(set(found_cases)))
        
    return "Không tìm thấy án lệ phù hợp cho từ khóa: " + keywords


TOOLS = [search_legal_database, calculate_penalty, check_compliance_requirements, search_case_law]

# Câu hỏi phức tạp tích hợp ma túy, phạt rò rỉ dữ liệu, tuân thủ công nghệ startup và án lệ vi phạm hợp đồng
QUESTION = (
    "Một người bị cáo buộc tội tàng trữ trái phép chất ma túy. Đồng thời, doanh nghiệp của họ "
    "là một startup công nghệ có doanh thu hàng năm là 5 triệu USD bị nghi ngờ rò rỉ dữ liệu người dùng "
    "ở mức độ nghiêm trọng cao (high severity), và vi phạm hợp đồng (breach of contract) dịch vụ với đối tác. "
    "Hãy tra cứu hình phạt tội tàng trữ ma túy trong cơ sở dữ liệu luật, tính toán mức phạt tài chính ước tính "
    "cho vi phạm 'data_privacy', kiểm tra các khung tuân thủ áp dụng cho công ty, và tìm kiếm án lệ liên quan."
)

SYSTEM_PROMPT = (
    "Bạn là một trợ lý phân tích pháp lý chuyên nghiệp. Bạn có quyền truy cập vào các công cụ để tìm kiếm cơ sở dữ liệu luật, "
    "tìm kiếm án lệ liên quan, tính toán mức phạt hành chính và kiểm tra yêu cầu tuân thủ. Hãy sử dụng những công cụ này "
    "để xây dựng một phân tích toàn diện. Tìm kiếm thông tin cho từng lĩnh vực pháp lý riêng biệt — ma túy, bảo mật thông tin, "
    "tuân thủ và vi phạm hợp đồng. Hãy tóm tắt câu trả lời cuối cùng của bạn dưới 500 từ. "
    f"{language_instruction()}"
)


async def main():
    from langgraph.prebuilt import create_react_agent

    print("=" * 70)
    print("STAGE 3: Single Agent (Vòng lặp ReAct)")
    print("=" * 70)
    print()
    print("[Cách hoạt động]")
    print("  1. Agent tự trị nhận được một câu hỏi phức tạp gồm nhiều phần")
    print("  2. Agent suy nghĩ về công cụ cần gọi (Think)")
    print("  3. Agent tiến hành gọi công cụ (Act)")
    print("  4. Agent quan sát kết quả trả về và quyết định bước tiếp theo (Observe)")
    print("  5. Lặp lại cho đến khi có đủ thông tin để đưa ra câu trả lời cuối cùng")
    print()
    print(f"Câu hỏi: {QUESTION}")
    print("-" * 70)

    llm = get_llm()
    # Kích hoạt debug=True để hiển thị chi tiết quá trình suy nghĩ trong vòng lặp ReAct của LangGraph
    graph = create_react_agent(model=llm, tools=TOOLS, prompt=SYSTEM_PROMPT, debug=True)

    inputs = {"messages": [{"role": "user", "content": QUESTION}]}

    step = 0
    async for chunk in graph.astream(inputs, stream_mode="updates"):
        for node_name, update in chunk.items():
            step += 1
            messages = update.get("messages", [])
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    print(f"\n[Bước {step}] SUY NGHĨ + HÀNH ĐỘNG (node: {node_name})")
                    for tc in msg.tool_calls:
                        print(f"  Gọi Tool: {tc['name']}")
                        print(f"  Đối số (Args): {tc['args']}")
                elif msg.type == "tool":
                    print(f"\n[Bước {step}] QUAN SÁT (node: {node_name})")
                    content = msg.content
                    print(f"  Kết quả: {content[:300]}{'...' if len(content) > 300 else ''}")
                elif msg.type == "ai" and msg.content:
                    print(f"\n[Bước {step}] CÂU TRẢ LỜI CUỐI CÙNG (node: {node_name})")
                    print("-" * 70)
                    print(msg.content)

    print()
    print("-" * 70)
    print("[Những điểm cải tiến so với Stage 2]")
    print("  + Tự trị (Autonomous): agent tự quyết định gọi tool nào và gọi khi nào")
    print("  + Suy luận nhiều bước (Multi-step reasoning): có thể tìm kiếm, tính toán rồi lại tìm kiếm tiếp")
    print("  + Xử lý câu hỏi phức tạp: chia nhỏ bài toán thành các tác vụ thành phần")
    print()
    print("[Hạn chế của Stage 3]")
    print("  - Agent đơn lẻ (Single agent): một LLM duy nhất xử lý mọi lĩnh vực (luật chung, thuế, tuân thủ)")
    print("  - Không có tính chuyên môn hóa cao: cùng một system prompt cho tất cả các mảng luật khác nhau")
    print("  - Điểm nghẽn cổ chai (Bottleneck): các lượt gọi tool chạy tuần tự, chưa thể chạy song song")
    print()
    print("Tiếp theo: Stage 4 chia tách hệ thống này thành các sub-agent chuyên môn hóa hoạt động song song.")
    print("=" * 70)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())