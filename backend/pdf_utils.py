import io

import fitz
import pdfplumber


def extract_text_from_pdf_bytes(data: bytes) -> tuple[str, str, int]:
    text_parts: list[str] = []
    page_count = 0

    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            page_count = len(doc)
            for page in doc:
                text_parts.append(page.get_text("text"))
        text = "\n".join(text_parts).strip()
        if len(text) >= 300:
            return text, "pymupdf", page_count
    except Exception:
        pass

    text_parts = []
    page_count = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")

    text = "\n".join(text_parts).strip()
    return text, "pdfplumber", page_count
