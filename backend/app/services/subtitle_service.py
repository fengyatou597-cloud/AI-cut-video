import re
from dataclasses import dataclass
from fastapi import HTTPException, UploadFile


@dataclass
class SubtitleCue:
    index: int
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.2, self.end - self.start)


def read_srt_upload(file: UploadFile) -> str:
    filename = file.filename or "subtitles.srt"
    if not filename.lower().endswith(".srt"):
        raise HTTPException(status_code=400, detail="字幕暂只支持 .srt 文件")
    raw = file.file.read()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="字幕文件编码无法识别，请保存为 UTF-8 后再上传")


def parse_srt(content: str) -> list[SubtitleCue]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    blocks = re.split(r"\n{2,}", normalized)
    cues: list[SubtitleCue] = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        time_line_index = next((idx for idx, line in enumerate(lines) if "-->" in line), -1)
        if time_line_index < 0:
            continue
        time_line = lines[time_line_index]
        try:
            start_text, end_text = [part.strip() for part in time_line.split("-->", 1)]
            start = srt_time_to_seconds(start_text)
            end = srt_time_to_seconds(end_text.split(" ")[0])
        except ValueError:
            continue
        text = " ".join(lines[time_line_index + 1 :]).strip()
        if not text or end <= start:
            continue
        cues.append(SubtitleCue(index=len(cues) + 1, start=start, end=end, text=text))
    return cues


def srt_duration(content: str) -> float | None:
    cues = parse_srt(content)
    if not cues:
        return None
    return round(max(cue.end for cue in cues), 3)


def srt_time_to_seconds(value: str) -> float:
    match = re.match(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})", value.strip())
    if not match:
        raise ValueError(f"Invalid SRT time: {value}")
    hours, minutes, seconds, millis = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis.ljust(3, "0")[:3]) / 1000
