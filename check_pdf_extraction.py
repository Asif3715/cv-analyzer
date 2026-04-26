#!/usr/bin/env python3
"""Quick PDF text extraction checker for TALASH.

Usage:
  python check_pdf_extraction.py /path/to/file.pdf
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

try:
    import fitz
except ModuleNotFoundError:
    fitz = None

import pdfplumber


def extract_with_pymupdf(data: bytes) -> tuple[str, int]:
    if fitz is None:
        raise ModuleNotFoundError("fitz is not installed")
    with fitz.open(stream=data, filetype="pdf") as doc:
        page_count = len(doc)
        text = "\n".join(page.get_text("text") for page in doc).strip()
    return text, page_count


def extract_with_pdfplumber(data: bytes) -> tuple[str, int]:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        text = "\n".join((page.extract_text() or "") for page in pdf.pages).strip()
    return text, page_count


def research_like_lines(text: str) -> list[str]:
    lines = []
    patterns = [
        re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I),
        re.compile(r"\bdoi\b", re.I),
        re.compile(r"\bproceedings\b|\bjournal\b|\bconference\b|\bvol\.?\b|\bpp\.?\b", re.I),
    ]
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if any(p.search(clean) for p in patterns):
            lines.append(clean)
    return lines


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python check_pdf_extraction.py /path/to/file.pdf")
        return 1

    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()

    if fitz is not None:
        try:
            text, pages = extract_with_pymupdf(data)
            method = "pymupdf"
        except Exception as exc:
            print(f"PyMuPDF failed: {exc}")
            text, pages = extract_with_pdfplumber(data)
            method = "pdfplumber"
    else:
        text, pages = extract_with_pdfplumber(data)
        method = "pdfplumber"

    print(f"Method: {method}")
    print(f"Pages: {pages}")
    print(f"Characters: {len(text)}")
    out_base = Path(path)
    out_file = out_base.with_name(f"{out_base.stem}_extracted.txt")
    out_file.write_text(text, encoding="utf-8")
    print(f"Saved extracted text to: {out_file}")
    print("\n--- Likely research lines ---")
    lines = research_like_lines(text)
    print(f"Count: {len(lines)}")
    for line in lines[:50]:
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
