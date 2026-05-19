"""Generate Financial Copilot platform testing guide PDF."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DOCS_DIR = Path(__file__).parent
OUTPUT = DOCS_DIR / "Financial_Copilot_Testing_Guide.pdf"
OUTPUT_TMP = DOCS_DIR / "Financial_Copilot_Testing_Guide.new.pdf"


def build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=10,
            textColor=colors.HexColor("#0f172a"),
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            spaceAfter=16,
            textColor=colors.HexColor("#475569"),
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontSize=13,
            leading=16,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor("#0f172a"),
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#1e293b"),
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            spaceAfter=5,
            alignment=TA_LEFT,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=9,
            leading=11,
            leftIndent=12,
            bulletIndent=0,
            spaceAfter=2,
        ),
        "mono": ParagraphStyle(
            "Mono",
            parent=base["Code"],
            fontSize=7.5,
            leading=9.5,
            fontName="Courier",
            backColor=colors.HexColor("#f1f5f9"),
            leftIndent=6,
            rightIndent=6,
            spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            wordWrap="CJK",
        ),
        "cell_header": ParagraphStyle(
            "CellHeader",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            alignment=TA_LEFT,
            wordWrap="CJK",
        ),
    }


# Usable width: letter 8.5" minus 0.6" margins each side
PAGE_WIDTH = letter[0] - 1.2 * inch
COL_3 = [0.9 * inch, 2.45 * inch, PAGE_WIDTH - 0.9 * inch - 2.45 * inch]
COL_4 = [0.38 * inch, 1.22 * inch, 2.28 * inch, PAGE_WIDTH - 0.38 * inch - 1.22 * inch - 2.28 * inch]


def p(text: str, style: str, styles: dict) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), styles[style])


def _cell(text: str, styles: dict, *, header: bool = False) -> Paragraph:
    safe = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    style = "cell_header" if header else "cell"
    return Paragraph(safe, styles[style])


def table(headers: list[str], rows: list[list[str]], col_widths: list, styles: dict) -> Table:
    """Build a table with Paragraph cells so text wraps inside column bounds."""
    ncols = len(headers)
    if len(col_widths) != ncols:
        raise ValueError(f"Expected {ncols} column widths, got {len(col_widths)}")

    header_row = [_cell(h, styles, header=True) for h in headers]
    body_rows = [[_cell(cell, styles) for cell in row] for row in rows]
    data = [header_row] + body_rows

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def build_story(styles: dict) -> list:
    s = []
    cw4 = COL_4

    s.append(p("Financial Copilot Platform", "title", styles))
    s.append(
        p(
            "Capabilities &amp; Testing Guide — May 2026<br/>"
            "Repos: financial-copilot-api · financial-copilot-ai-orchestrator · financial-copilot-web",
            "subtitle",
            styles,
        )
    )

    s.append(p("What exists today", "h1", styles))
    s.append(
        table(
            ["Layer", "Implemented", "Not built / no UI"],
            [
                [
                    "Web",
                    "Dashboard, demo seed, streaming AI chat",
                    "Imports, account forms, auth, extra nav pages",
                ],
                [
                    "API",
                    "Dashboard, accounts, holdings, seed, CSV imports",
                    "Tax API, scenarios, reports, bond optimiser, auth",
                ],
                [
                    "Orchestrator",
                    "Health, chat, stream, session memory, routing",
                    "DB memory, Phase C summarization",
                ],
            ],
            COL_3,
            styles,
        )
    )
    s.append(Spacer(1, 10))

    s.append(p("Recommended test order", "h1", styles))
    s.append(
        p(
            "0. Stack up (ports 8080, 8000, 3000) → 1. Health → 2. Demo seed → "
            "3. Dashboard UI → 4. AI basic → 5. AI memory/streaming → "
            "6. Agent routing → 7. Accounts/holdings (API) → 8. CSV imports (API)",
            "body",
            styles,
        )
    )

    # --- Section 0 ---
    s.append(PageBreak())
    s.append(p("0. Prerequisites", "h1", styles))
    s.append(
        table(
            ["Service", "URL", "Notes"],
            [
                ["API", "http://localhost:8080", "Spring Boot + PostgreSQL"],
                ["Orchestrator", "http://localhost:8000", "GOOGLE_API_KEY in .env"],
                ["Web", "http://localhost:3000", "NEXT_PUBLIC_AI_URL → :8000"],
            ],
            COL_3,
            styles,
        )
    )
    s.append(Spacer(1, 8))
    s.append(p("<b>Pass when:</b> All three URLs respond without connection errors.", "body", styles))

    # --- Section 1 ---
    s.append(p("1. Infrastructure &amp; connectivity", "h1", styles))
    s.append(
        table(
            ["#", "Capability", "How to test", "Pass criteria"],
            [
                ["1.1", "API liveness", "GET /actuator/health", 'status "UP"'],
                ["1.2", "Orchestrator", "GET /health", 'status "ok"'],
                ["1.3", "API from orchestrator", "GET /health/dependencies", 'status "ok"'],
                ["1.4", "Web loads", "Open :3000", "Page renders"],
                ["1.5", "Agents list", "GET /api/v1/agents", "Lists agents"],
            ],
            cw4,
            styles,
        )
    )
    s.append(Spacer(1, 6))
    s.append(p("PowerShell smoke:", "h2", styles))
    s.append(
        p(
            "Invoke-RestMethod http://localhost:8080/actuator/health<br/>"
            "Invoke-RestMethod http://localhost:8000/health<br/>"
            "Invoke-RestMethod http://localhost:8000/health/dependencies<br/>"
            "Invoke-RestMethod http://localhost:8000/api/v1/agents",
            "mono",
            styles,
        )
    )

    # --- Section 2 ---
    s.append(p("2. Demo data (required first)", "h1", styles))
    s.append(
        table(
            ["#", "Capability", "How to test", "Pass criteria"],
            [
                ["2.1", "Seed demo", 'UI: "Seed Demo Data"', "Metrics + holdings populate"],
                ["2.2", "Reseed", "POST /api/v1/demo/seed?reset=true", "No 412 on dashboard"],
            ],
            cw4,
            styles,
        )
    )
    s.append(
        p(
            "<b>Without seed:</b> dashboard and AI fail (412 — demo user not seeded).",
            "body",
            styles,
        )
    )

    # --- Section 3 ---
    s.append(PageBreak())
    s.append(p("3. Dashboard (web UI)", "h1", styles))
    s.append(
        table(
            ["#", "Capability", "How to test", "Pass criteria"],
            [
                ["3.1", "KPI cards", "After seed", "Net worth, assets, liabilities, health /100"],
                ["3.2", "Region chart", "Left pie", "Segments + legend %"],
                ["3.3", "Asset class chart", "Right pie", "Segments + legend %"],
                ["3.4", "Holdings table", "Scroll table", "Symbols, qty, ZAR values"],
                ["3.5", "Errors", "Stop API, refresh", "Error banner + retry"],
                ["3.6", "API parity", "GET /api/v1/dashboard", "Matches UI numbers"],
            ],
            cw4,
            styles,
        )
    )
    s.append(
        p(
            "<b>Placeholder nav:</b> Portfolio, Retirement, Bonds are disabled — no pages.",
            "body",
            styles,
        )
    )

    # --- Section 4 ---
    s.append(p("4. AI chat — basic (web UI)", "h1", styles))
    s.append(
        table(
            ["#", "Capability", "How to test", "Pass criteria"],
            [
                ["4.1", "Send message", "Ask net worth (one sentence)", "User + assistant bubbles"],
                ["4.2", "Streaming", "Watch reply", "Token-by-token growth"],
                ["4.3", "Real data", "Compare to dashboard", "Figures align"],
                ["4.4", "Brevity", "Long question", "2–4 short paragraphs"],
                ["4.5", "Agent label", "After reply", "e.g. portfolio_analysis"],
                ["4.6", "Disclaimer", "Panel footer", "Educational only text"],
                ["4.7", "Suggestions", "Empty-state chips", "Sends prefilled question"],
            ],
            cw4,
            styles,
        )
    )

    # --- Section 5 ---
    s.append(p("5. AI chat — session &amp; streaming", "h1", styles))
    s.append(
        table(
            ["#", "Capability", "How to test", "Pass criteria"],
            [
                ["5.1", "Multi-turn", "Net worth → \"shorter\"", "Context-aware shorter reply"],
                ["5.2", "Refresh", "F5 mid-chat", "Thread restored"],
                ["5.3", "New chat", "New chat button", "Empty thread, new session"],
                ["5.4", "Session API", "PowerShell script below", "History ≥ 2 msgs"],
                ["5.5", "Non-stream API", "POST /api/v1/chat", "reply + active_agent"],
                ["5.6", "Stream API", "POST /api/v1/chat/stream", "token + done events"],
            ],
            cw4,
            styles,
        )
    )
    s.append(p("Session test (PowerShell):", "h2", styles))
    s.append(
        p(
            '$sid = [guid]::NewGuid().ToString()<br/>'
            "Invoke-RestMethod http://localhost:8000/api/v1/chat -Method POST ...<br/>"
            'Invoke-RestMethod "http://localhost:8000/api/v1/chat/session/$sid"<br/>'
            "Second POST with message \"shorter\" and same session_id",
            "mono",
            styles,
        )
    )
    s.append(
        p(
            "<b>Note:</b> Server memory is in-process (MemorySaver). Restarting orchestrator clears server sessions.",
            "body",
            styles,
        )
    )

    # --- Section 6 ---
    s.append(PageBreak())
    s.append(p("6. AI agent routing", "h1", styles))
    s.append(
        p("Keyword routing; portfolio context loaded from API for specialist routes.", "body", styles)
    )
    s.append(
        table(
            ["Agent", "Test prompt", "Pass criteria"],
            [
                ["portfolio_analysis", "How is my allocation?", "Uses holdings/allocation"],
                ["tax", "Explain CGT on my gains", "Agent label tax"],
                ["bond_optimisation", "Pay extra on home loan?", "Uses liabilities"],
                ["risk_analysis", "Concentration risk?", "Risk bullets"],
                ["recommendation", "What next for TFSA?", "2–3 suggestions"],
                ["scenario", "What if rates rise 2%?", "What-if answer"],
                ["report_generation", "Wealth summary report", "Brief snapshot"],
                ["general", "Hello", "Conversational"],
            ],
            COL_3,
            styles,
        )
    )

    # --- Section 7 ---
    s.append(p("7. Accounts &amp; holdings (API only)", "h1", styles))
    s.append(
        table(
            ["#", "Capability", "Endpoint", "Pass"],
            [
                ["7.1", "List accounts", "GET /api/v1/accounts", "Demo accounts array"],
                ["7.2", "Create account", "POST /api/v1/accounts", "201"],
                ["7.3", "List holdings", "GET .../accounts/{id}/holdings", "Holdings list"],
                ["7.4", "Add holding", "POST .../holdings", "201"],
                ["7.5", "Dashboard sync", "Refresh dashboard / AI", "New data visible"],
            ],
            cw4,
            styles,
        )
    )
    s.append(p("Swagger: http://localhost:8080/swagger-ui.html", "body", styles))

    # --- Section 8 ---
    s.append(p("8. CSV import pipeline (API only)", "h1", styles))
    s.append(p("See financial-copilot-api/docs/IMPORTS.md for full workflow.", "body", styles))
    s.append(
        table(
            ["#", "Step", "Endpoint / action", "Pass"],
            [
                ["8.1", "Source types", "GET /imports/source-types", "Lists source types"],
                ["8.2", "Preview", "POST /imports/preview", "Column map suggested"],
                ["8.3", "Upload", "POST /imports/upload", "Job REVIEW"],
                ["8.4", "Records", "GET .../records", "VALID/ERROR rows"],
                ["8.5", "Fix", "PATCH + revalidate", "Errors cleared"],
                ["8.6", "Commit", "POST .../commit", "Data persisted"],
                ["8.7", "Bond CSV", "BOND_STATEMENT sample", "Balance updated"],
                ["8.8", "Profiles", "mapping-profiles GET/POST", "Save/reuse maps"],
                ["8.9", "Cancel", "POST .../cancel", "Job cancelled"],
            ],
            cw4,
            styles,
        )
    )
    s.append(
        p(
            "Samples: backend/portfolio-service/src/main/resources/samples/",
            "mono",
            styles,
        )
    )

    # --- Not implemented ---
    s.append(PageBreak())
    s.append(p("Not implemented yet (skip for current release)", "h1", styles))
    for item in [
        "Login / auth / multi-user",
        "Tax engine REST API (AI discusses tax in prose only)",
        "Monte Carlo / scenarios API",
        "Report PDF generation",
        "Bond optimiser API",
        "Phase C — long-thread summarization",
        "Web UI for imports, accounts, settings",
    ]:
        s.append(p(f"• {item}", "bullet", styles))

    s.append(Spacer(1, 16))
    s.append(p("Gate checklist before Phase C or deploy", "h1", styles))
    for item in [
        "All services healthy; /health/dependencies ok",
        "Demo seeded",
        "Dashboard metrics, charts, holdings correct",
        "Streaming chat + follow-up \"shorter\" + refresh + new chat",
        "At least portfolio + one other agent route",
        "API-only: accounts/holdings/imports if in scope",
    ]:
        s.append(p(f"☐ {item}", "bullet", styles))

    s.append(Spacer(1, 20))
    s.append(
        p(
            "Generated from financial-copilot-ai-orchestrator/docs/generate_testing_guide_pdf.py",
            "subtitle",
            styles,
        )
    )
    return s


def main():
    styles = build_styles()
    out = OUTPUT_TMP if OUTPUT.exists() else OUTPUT
    doc = SimpleDocTemplate(
        str(out),
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Financial Copilot Testing Guide",
        author="Financial Copilot",
    )
    doc.build(build_story(styles))
    if out == OUTPUT_TMP:
        try:
            out.replace(OUTPUT)
            print(f"Wrote {OUTPUT}")
        except OSError:
            print(f"Wrote {OUTPUT_TMP} (close the open PDF, then rename to replace)")
    else:
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
