from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.auth_context import set_auth_token
from app.cashflow.bank_parser import parse_bank_statement_pdf
from app.cashflow.schemas import BankStatementProvider, ParsedBankStatement
from app.statements.pdf_text import extract_text_from_pdf

router = APIRouter(prefix="/api/v1/cashflow", tags=["cashflow"])

MAX_PDF_BYTES = 15 * 1024 * 1024


def _apply_auth(authorization: str | None) -> None:
    if authorization and authorization.startswith("Bearer "):
        set_auth_token(authorization[7:].strip())


@router.post("/parse", response_model=ParsedBankStatement)
async def parse_bank_statement(
    authorization: str | None = Header(default=None),
    provider: BankStatementProvider = Form(...),
    file: UploadFile = File(...),
    pdf_password: str | None = Form(default=None),
) -> ParsedBankStatement:
    _apply_auth(authorization)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF bank statement file.")

    data = await file.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF must be 15 MB or smaller.")
    if len(data) < 100:
        raise HTTPException(status_code=400, detail="PDF file is empty or invalid.")

    try:
        text = extract_text_from_pdf(data, password=pdf_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}") from exc

    try:
        return await parse_bank_statement_pdf(text, provider)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse bank statement: {exc}",
        ) from exc
