from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import re
import shutil
from pathlib import Path


ID_RE = re.compile(r"(?:game_[ts]|tda03_[ts]|tda02_staff)\d+(?:_ruby)?")
ASCII_TEXT_RE = re.compile(r"[A-Za-z0-9.?!(*'\"][ -~]{2,}")
SURROGATE_RE = re.compile("[\udc80-\udcff]")
CJK_RUN_RE = re.compile(r"[\u3000-\u9fff\u3040-\u30ff\uff00-\uffef][^\x00\udc80-\udcff]*")


@dataclass(frozen=True)
class Translation:
    jp: str
    en: str
    zh: str


def normalize_path_key(path: str) -> str:
    return Path(path.replace("\\", "/")).name


def load_translations(csv_path: Path, column: str) -> dict[tuple[str, str], Translation]:
    table: dict[tuple[str, str], Translation] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            text = normalize_replacement_text((row.get(column) or "").strip())
            if not text or text == "Pg9":
                continue
            key = (normalize_path_key(row.get("file", "")), row["id"])
            table[key] = Translation(
                jp=(row.get("jp") or "").strip(),
                en=(row.get("en") or "").strip(),
                zh=text,
            )
    return table


def normalize_replacement_text(text: str) -> str:
    # DeepSeek sometimes preserves the visible "w" from a stripped \w wait
    # marker. That "w" is not text; remove it before writing to the game.
    text = re.sub(r"(^|[「『（(])w(?=[.…。])", r"\1", text)
    text = re.sub(r"(?<![A-Za-z])w(?=[.…。])", "", text)
    return text


def find_en_span(segment: str) -> tuple[int, int] | None:
    quote = segment.find("「")
    ascii_match = ASCII_TEXT_RE.search(segment)
    ascii_start = ascii_match.start() if ascii_match else -1

    if quote >= 0 and (ascii_start < 0 or quote < ascii_start):
        end = segment.find("」", quote + 1)
        if end >= 0:
            return quote, end + 1

    if not ascii_match:
        return None
    start = ascii_start
    tail = segment[start:]
    stops = []
    for marker in ("\x00", "\\p"):
        idx = tail.find(marker)
        if idx > 0:
            stops.append(idx)
    sm = SURROGATE_RE.search(tail)
    if sm and sm.start() > 0:
        stops.append(sm.start())
    end = start + (min(stops) if stops else len(tail))
    return start, end


def find_jp_span(segment: str, jp: str, *, extend_to_boundary: bool = True) -> tuple[int, int] | None:
    if jp:
        candidates = [jp]
        # The rough extractor can accidentally keep the "w" from a preceding
        # \w wait marker, e.g. "w…\w。", while the real file text starts at
        # "…\w。". Try that visible form before falling back.
        if jp.startswith("w") and len(jp) > 1 and jp[1] in "…。、！？「『":
            candidates.append(jp[1:])
        for candidate in candidates:
            idx = segment.rfind(candidate)
            if idx >= 0:
                start = idx
                if extend_to_boundary:
                    # The rough extractor sometimes captures only the quoted tail of a
                    # Japanese line. Extend to the previous binary/control boundary so
                    # the whole visible line is replaced, not just the quoted fragment.
                    while start > 0:
                        ch = segment[start - 1]
                        if ch == "\x00" or SURROGATE_RE.match(ch):
                            break
                        start -= 1
                    while start < idx and segment[start].isspace():
                        start += 1
                return start, idx + len(candidate)

    end = segment.rfind("\\p")
    if end < 0:
        pg9 = segment.rfind("Pg9")
        search_end = pg9 if pg9 >= 0 else len(segment)
        nul = segment.rfind("\x00", 0, search_end)
        end = nul if nul >= 0 else search_end

    if end <= 0:
        return None

    prefix = segment[:end]
    quote = prefix.rfind("「")
    if quote >= 0:
        return quote, end

    cjk_matches = list(CJK_RUN_RE.finditer(prefix))
    if cjk_matches:
        match = cjk_matches[-1]
        return match.start(), match.end()

    # Speaker names and unquoted narration are plain printable text immediately
    # before the control bytes.
    start = end
    while start > 0:
        ch = segment[start - 1]
        if ch == "\x00" or SURROGATE_RE.match(ch):
            break
        start -= 1
    while start < end and segment[start].isspace():
        start += 1
    return (start, end) if start < end else None


def clean_dangling_control_prefixes(text: str) -> str:
    # Some extracted JP strings start in the middle of wait markers, e.g.
    # "...\\wText" can be extracted as "wText". If the replacement begins at
    # that "w", the engine-visible prefix becomes "...\\Chinese". Remove those
    # invalid leftovers while preserving valid control codes such as \\p/\\w.
    def is_text_start(ch: str) -> bool:
        return ch in "「『“" or "\u4e00" <= ch <= "\u9fff"

    out: list[str] = []
    i = 0
    while i < len(text):
        if (
            text[i] == "…"
            and i + 2 < len(text)
            and text[i + 1] == "\\"
            and is_text_start(text[i + 2])
        ):
            i += 2
            continue
        if text[i] == "\\" and i + 1 < len(text) and is_text_start(text[i + 1]):
            i += 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def repack_one(
    src: Path,
    dst: Path,
    translations: dict[tuple[str, str], Translation],
    target: str,
) -> tuple[int, int]:
    data = src.read_bytes()
    if not data.startswith(b"EPK\0"):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return 0, 0

    text = data.decode("utf-8", "surrogateescape")
    matches = list(ID_RE.finditer(text))
    replacements: list[tuple[int, int, str]] = []
    filename = src.name
    previous_id_end = 0

    for i, match in enumerate(matches):
        text_id = match.group()
        if text_id.endswith("_ruby"):
            previous_id_end = match.end()
            continue
        tr = translations.get((filename, text_id))
        if not tr:
            previous_id_end = match.end()
            continue
        if target == "jp":
            segment = text[previous_id_end : match.start()]
            span = find_jp_span(segment, tr.jp, extend_to_boundary=filename != "__staffroll__.egpack")
            base = previous_id_end
        else:
            next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            segment = text[match.end() : next_start]
            span = find_en_span(segment)
            base = match.end()
        if not span:
            previous_id_end = match.end()
            continue
        start, end = span
        replacements.append((base + start, base + end, tr.zh))
        previous_id_end = match.end()

    if not replacements:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return 0, len(matches)

    rebuilt = []
    cursor = 0
    for start, end, zh in replacements:
        rebuilt.append(text[cursor:start])
        rebuilt.append(zh)
        cursor = end
    rebuilt.append(text[cursor:])
    out_text = clean_dangling_control_prefixes("".join(rebuilt))
    out = out_text.encode("utf-8", "surrogateescape")
    out = out[:8] + len(out).to_bytes(4, "little") + out[12:]

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(out)
    return len(replacements), len(matches)


def main() -> int:
    parser = argparse.ArgumentParser(description="Replace EPK text with translated Chinese from CSV.")
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--column", default="zh_deepseek")
    parser.add_argument("--target", choices=["en", "jp"], default="en")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    translations = load_translations(args.csv, args.column)
    total_files = 0
    total_replaced = 0
    total_ids = 0
    for src in sorted(args.source_dir.rglob("*.egpack")):
        rel = src.relative_to(args.source_dir)
        dst = args.output_dir / rel
        replaced, ids = repack_one(src, dst, translations, args.target)
        total_files += 1
        total_replaced += replaced
        total_ids += ids
        print(f"{rel} replaced={replaced} ids={ids}")

    print(f"done files={total_files} replaced={total_replaced} ids={total_ids} output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
