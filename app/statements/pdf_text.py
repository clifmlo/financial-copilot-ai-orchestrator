from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

PASSWORD_MSG = (
    "This PDF is password-protected. Enter the PDF password below, or upload an unlocked copy."
)


def extract_text_from_pdf(data: bytes, max_pages: int = 30, password: str | None = None) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            pwd = (password or "").strip()
            if not pwd:
                raise ValueError(PASSWORD_MSG)
            if reader.decrypt(pwd) == 0:
                raise ValueError("Incorrect PDF password. Check the password and try again.")

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
