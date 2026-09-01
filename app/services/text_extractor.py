from pathlib import Path


class TextExtractionError(Exception):
    """Raised when text extraction cannot be completed."""


def extract_text(path: Path, extension: str) -> str:
    if extension in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if extension == ".pdf":
        return extract_pdf_text(path)
    if extension == ".docx":
        return extract_docx_text(path)
    if extension in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        return extract_image_text(path)
    raise TextExtractionError(f"지원하지 않는 파일 형식입니다: {extension}")


def extract_pdf_text(path: Path) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise TextExtractionError("PDF 추출 라이브러리 PyMuPDF가 설치되어 있지 않습니다.") from exc

    parts: list[str] = []
    try:
        with fitz.open(path) as document:
            for page in document:
                parts.append(page.get_text())
    except Exception as exc:
        raise TextExtractionError("PDF 텍스트 추출에 실패했습니다.") from exc

    return "\n".join(parts).strip()


def extract_docx_text(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise TextExtractionError("DOCX 추출 라이브러리 python-docx가 설치되어 있지 않습니다.") from exc

    try:
        document = Document(path)
    except Exception as exc:
        raise TextExtractionError("DOCX 텍스트 추출에 실패했습니다.") from exc

    return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()


def extract_image_text(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise TextExtractionError("이미지 OCR 라이브러리 Pillow 또는 pytesseract가 설치되어 있지 않습니다.") from exc

    try:
        with Image.open(path) as image:
            return pytesseract.image_to_string(image, lang="kor+eng").strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise TextExtractionError("Tesseract OCR 실행 파일을 찾을 수 없습니다.") from exc
    except Exception as exc:
        raise TextExtractionError("이미지 OCR 처리에 실패했습니다.") from exc
