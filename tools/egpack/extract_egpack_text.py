from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ID_RE = re.compile(r"(?:game_[ts]|tda03_[ts]|tda02_staff)\d+(?:_ruby)?")
ASCII_TEXT_RE = re.compile(r"[A-Za-z0-9.?!(*'\"][ -~]{2,}")
CJK_TEXT_RE = re.compile(r"[\u3000-\u9fff\uff00-\uffef][^\x00\ufffd]*")


def clean_jp(chunk: str) -> str:
    before_p = chunk.rsplit("\\p", 1)[0] if "\\p" in chunk else chunk
    start = before_p.rfind("\ufffd")
    text = before_p[start + 1 :] if start >= 0 else before_p
    text = text.strip("\x00\r\n\t ?\ufffd")

    quote = text.rfind("「")
    if quote >= 0:
        text = text[quote:]
    else:
        # Keep the final printable run. This handles narration lines without quotes.
        m = list(re.finditer(r"[\u3000-\u9fff\u3040-\u30ff\uff00-\uffefA-Za-z0-9「『（(].*", text))
        if m:
            text = m[-1].group(0)

    return normalize_text(text)


def clean_en(chunk: str) -> str:
    quote = chunk.find("「")
    if quote >= 0:
        text = chunk[quote:]
        end = text.find("」", 1)
        if end >= 0:
            return normalize_text(text[: end + 1])

    # English narration may not be quoted. Localized fallback slots may also contain
    # Chinese; read either ASCII or CJK-visible runs and stop at control/binary data.
    m = ASCII_TEXT_RE.search(chunk)
    if m:
        start = m.start()
    else:
        visible = CJK_TEXT_RE.search(chunk)
        if not visible:
            return ""
        start = visible.start()
    text = chunk[start:]
    stop_candidates = []
    for marker in ("\ufffd", "\x00", "\\p"):
        idx = text.find(marker)
        if idx > 0:
            stop_candidates.append(idx)
    if stop_candidates:
        text = text[: min(stop_candidates)]
    text = normalize_text(text)
    if text == "Pg9":
        return ""
    return normalize_text(text)


def normalize_text(text: str) -> str:
    return (
        text.replace("\x00", "")
        .replace("\r", "")
        .replace("\n", "\\n")
        .replace("\ufffd", "")
        .strip()
    )


def extract_file(path: Path) -> list[dict[str, str]]:
    data = path.read_bytes()
    if not data.startswith(b"EPK\0"):
        return []

    decoded = data.decode("utf-8", "replace")
    ids = list(ID_RE.finditer(decoded))
    rows: list[dict[str, str]] = []
    previous_id_end = 0

    for index, match in enumerate(ids):
        next_start = ids[index + 1].start() if index + 1 < len(ids) else len(decoded)
        jp = clean_jp(decoded[previous_id_end : match.start()])
        en = clean_en(decoded[match.end() : next_start])
        previous_id_end = match.end()

        if match.group().endswith("_ruby"):
            continue

        rows.append(
            {
                "file": str(path),
                "id": match.group(),
                "jp": jp,
                "en": en,
            }
        )

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract rough jp/en text rows from EPK egpack files.")
    parser.add_argument("input", type=Path, help="An .egpack file or a directory containing .egpack files")
    parser.add_argument("--output", type=Path, required=True, help="CSV output path")
    args = parser.parse_args()

    inputs = [args.input] if args.input.is_file() else sorted(args.input.rglob("*.egpack"))
    rows: list[dict[str, str]] = []
    for path in inputs:
        rows.extend(extract_file(path))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "id", "jp", "en"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"files={len(inputs)} rows={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
