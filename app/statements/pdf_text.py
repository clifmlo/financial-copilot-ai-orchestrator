from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

PASSWORD_MSG = (
    "This PDF is password-protected. Enter the PDF password below, or upload an unlocked copy."
)
INCORRECT_PASSWORD_MSG = "Incorrect PDF password. Check the password and try again."


def _page_text_readable(reader: PdfReader) -> bool:
    try:
        if not reader.pages:
            return False
        return bool((reader.pages[0].extract_text() or "").strip())
    except (FileNotDecryptedError, PdfReadError):
        return False


def _unlock_pdf(reader: PdfReader, password: str | None) -> None:
    """Unlock encrypted PDFs. Many bank statements use an empty user password."""
    if not reader.is_encrypted:
        return

    user_password = (password or "").strip()
    attempts: list[str] = [""]
    if user_password:
        attempts.append(user_password)

    seen: set[str] = set()
    for pwd in attempts:
        if pwd in seen:
            continue
        seen.add(pwd)
        if reader.decrypt(pwd) != 0:
            return
        if _page_text_readable(reader):
            return

    if user_password:
        raise ValueError(INCORRECT_PASSWORD_MSG)
    raise ValueError(PASSWORD_MSG)


def extract_text_from_pdf(data: bytes, max_pages: int = 30, password: str | None = None) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        _unlock_pdf(reader, password)

        parts: list[str] = []
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text)
    except FileNotDecryptedError as exc:
        raise ValueError(PASSWORD_MSG) from exc
    except ValueError:
        raise
    except PdfReadError as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    combined = "\n\n".join(parts).strip()
    if not combined:
        raise ValueError(
            "Could not extract text from this PDF. Use a text-based statement (not a scan), or try unlocking it."
        )
    return combined
