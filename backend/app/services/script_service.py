from pathlib import Path
from fastapi import HTTPException, UploadFile

ALLOWED_SCRIPT_SUFFIXES = {".txt", ".md", ".docx"}


def read_script_upload(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SCRIPT_SUFFIXES:
        raise HTTPException(status_code=400, detail="当前支持 txt / md / docx 文稿")
    if suffix == ".docx":
        return _read_docx(file)
    raw = file.file.read()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="无法识别文稿编码，请转换为 UTF-8 后重试")


def _read_docx(file: UploadFile) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="后端未安装 python-docx，无法读取 docx 文稿") from exc
    try:
        document = Document(file.file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="docx 文稿读取失败，请确认文件未损坏") from exc
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    if not paragraphs:
        raise HTTPException(status_code=400, detail="docx 文稿中没有读取到正文")
    return "\n\n".join(paragraphs)


def split_script_into_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in normalized.split("\n") if line.strip()]

    blocks: list[str] = []
    for paragraph in paragraphs:
        cleaned = " ".join(paragraph.split())
        if len(cleaned) <= 220:
            blocks.append(cleaned)
            continue
        blocks.extend(_split_long_paragraph(cleaned))
    return [block for block in blocks if block]


def _split_long_paragraph(text: str, target_chars: int = 170) -> list[str]:
    pieces: list[str] = []
    current = ""
    for char in text:
        current += char
        if char in "。！？!?；;" and len(current) >= target_chars:
            pieces.append(current.strip())
            current = ""
    if current.strip():
        pieces.append(current.strip())
    return pieces


def estimate_duration_seconds(text: str) -> int:
    # 中文口播常见速度约 4-5 字/秒，这里取偏稳妥值并限制段落时长。
    duration = round(len(text) / 4.2)
    return max(12, min(45, duration))
