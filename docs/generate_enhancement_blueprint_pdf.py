"""Generate a product enhancement blueprint PDF for agent execution."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DOCS_DIR = Path(__file__).parent
OUTPUT = DOCS_DIR / "Financial_Copilot_Enhancement_Blueprint.pdf"
OUTPUT_TMP = DOCS_DIR / "Financial_Copilot_Enhancement_Blueprint.new.pdf"


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontSize=9,
            leading=11,
            leftIndent=12,
            bulletIndent=0,
            spaceAfter=2,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontSize=8.5,
            leading=10.5,
            wordWrap="CJK",
        ),
        "cell_head": ParagraphStyle(
            "cell_head",
            parent=base["Normal"],
            fontSize=8.5,
            leading=10.5,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            wordWrap="CJK",
        ),
    }


def p(text: str, style: str, st: dict) -> Paragraph:
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
    return Paragraph(safe, st[style])


def make_table(st: dict) -> Table:
    page_width = letter[0] - 1.2 * inch
    col_widths = [0.9 * inch, 2.1 * inch, page_width - 0.9 * inch - 2.1 * inch]
    rows = [
        [p("Phase", "cell_head", st), p("Workstream", "cell_head", st), p("Agent Instructions", "cell_head", st)],
        [
            p("1", "cell", st),
            p("Stability and Trust", "cell", st),
            p(
                "Implement session timeout UX, proactive stale-data warnings, and import reliability checks. "
                "Ship with tests for auth expiry and chat fallback behavior.",
                "cell",
                st,
            ),
        ],
        [
            p("2", "cell", st),
            p("Decision Support", "cell", st),
            p(
                "Add goals, scenario comparison, and risk alerts. "
                "Every recommendation must include data source and assumptions.",
                "cell",
                st,
            ),
        ],
        [
            p("3", "cell", st),
            p("Operational Intelligence", "cell", st),
            p(
                "Add monthly report export, scheduled reminders, and account-level data freshness dashboard. "
                "Prioritize low-friction weekly user habits.",
                "cell",
                st,
            ),
        ],
    ]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build():
    st = styles()
    story = [
        p("Financial Copilot Enhancement Blueprint", "title", st),
        p("Agent-Ready Execution Document • Version 1.0 • 28 May 2026", "subtitle", st),
        p("Objective", "h1", st),
        p(
            "Improve Financial Copilot from a dashboard tool into a guided financial operating system "
            "that helps users decide, act, and stay consistent.",
            "body",
            st,
        ),
        p("Primary Outcomes", "h1", st),
        p("• Increase weekly active usage via actionable alerts and next-step guidance.", "bullet", st),
        p("• Improve trust with explicit freshness and source confidence indicators.", "bullet", st),
        p("• Reduce decision friction with one-click scenarios and explainable AI recommendations.", "bullet", st),
        Spacer(1, 8),
        make_table(st),
        p("Top Priority Features (Order of Implementation)", "h1", st),
        p("1) Goal tracking: emergency fund, bond payoff date, retirement target.", "bullet", st),
        p("2) Cashflow and budgeting: monthly inflow/outflow with surplus signals.", "bullet", st),
        p("3) Smart alerts: stale data, risk concentration, debt threshold breaches.", "bullet", st),
        p("4) Scenario workspace: compare current vs what-if outcomes side by side.", "bullet", st),
        p("5) Data confidence layer: source, age, and confidence badge per metric.", "bullet", st),
        p("6) Monthly report export: PDF summary with actions and trend commentary.", "bullet", st),
        p("Agent Instructions (Must Follow)", "h1", st),
        p("• Work in small PRs by phase; each PR must include test evidence.", "bullet", st),
        p("• Do not merge UI changes without matching API/typing updates.", "bullet", st),
        p("• Each feature requires acceptance criteria and rollback notes.", "bullet", st),
        p("• Preserve backward compatibility for existing routes and stored data.", "bullet", st),
        p("• Add clear empty/loading/error states in every new view.", "bullet", st),
        p("Definition of Done", "h1", st),
        p("• Feature is visible in UI, wired to live data, and covered by tests.", "bullet", st),
        p("• Build succeeds and no new lint/type errors are introduced.", "bullet", st),
        p("• Tooltips, labels, and microcopy are reviewed for financial clarity.", "bullet", st),
        p("• Product owner can demo the workflow end-to-end in under 3 minutes.", "bullet", st),
    ]

    doc = SimpleDocTemplate(
        str(OUTPUT_TMP),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="Financial Copilot Enhancement Blueprint",
        author="Financial Copilot Team",
        subject="Implementation blueprint for AI agent execution",
    )
    doc.build(story)
    OUTPUT_TMP.replace(OUTPUT)
    print(f"Generated: {OUTPUT}")


if __name__ == "__main__":
    build()

