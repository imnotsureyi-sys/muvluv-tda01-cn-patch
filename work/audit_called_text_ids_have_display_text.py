from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "qa" / "alignment_review"

TEXT_ATTR_RE = re.compile(r'\btext(?:\d*)="\$([^"]+)"')
ID_RE_BY_TITLE = {
    "tda01": re.compile(r"(game_[ts]\d+)"),
    "tda02": re.compile(r"(game_[ts]\d+)"),
    "tda03": re.compile(r"(tda03_[ts]\d+)"),
}


def is_surrogate(ch: str) -> bool:
    return 0xDC80 <= ord(ch) <= 0xDCFF


def is_boundary(ch: str) -> bool:
    return ch == "\x00" or is_surrogate(ch) or (ord(ch) < 32 and ch not in "\t\r\n")


def visible_runs(segment: str) -> list[str]:
    runs: list[str] = []
    start: int | None = None
    for i, ch in enumerate(segment):
        if is_boundary(ch):
            if start is not None:
                runs.append(segment[start:i])
                start = None
        elif start is None:
            start = i
    if start is not None:
        runs.append(segment[start:])
    return runs


def clean(text: str) -> str:
    return (text or "").replace("\\p", "").replace("\\f", "").strip()


def display_run(runs: list[str]) -> str:
    if "_" in runs:
        marker = runs.index("_")
        for idx in range(marker - 1, -1, -1):
            text = clean(runs[idx])
            if text and text not in {"P", "U", ")", "}", "4w", "Pg9", "\u038e"}:
                return text
    for item in reversed(runs):
        text = clean(item)
        if text and text not in {"P", "U", ")", "}", "_", "4w", "Pg9", "\u038e"}:
            return text
    return ""


def build_shifted_display_map(egpack_dir: Path, id_re: re.Pattern[str]) -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    for path in sorted(egpack_dir.glob("*.egpack")):
        if path.name.startswith("__"):
            continue
        raw = path.read_bytes().decode("utf-8", "surrogateescape")
        matches = list(id_re.finditer(raw))
        records: list[tuple[str, str]] = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
            records.append((match.group(1), display_run(visible_runs(raw[match.start():end]))))
        for index in range(1, len(records)):
            current_id = records[index][0]
            previous_text = records[index - 1][1]
            mapping[(path.name, current_id)] = previous_text
    return mapping


def audit_title(title: str, repack_dir: Path) -> list[dict[str, str]]:
    id_re = ID_RE_BY_TITLE[title]
    display_map = build_shifted_display_map(repack_dir, id_re)
    rows: list[dict[str, str]] = []
    for xml_path in sorted(repack_dir.glob("*.xml")):
        if xml_path.name.startswith("__"):
            continue
        xml = xml_path.read_text("utf-8", errors="replace")
        egpack_name = xml_path.with_suffix(".egpack").name
        for line_no, line in enumerate(xml.splitlines(), start=1):
            if "<message" not in line:
                continue
            for text_id in TEXT_ATTR_RE.findall(line):
                if text_id.endswith("_ruby"):
                    continue
                actual = display_map.get((egpack_name, text_id), "")
                if not actual:
                    rows.append(
                        {
                            "title": title,
                            "file": egpack_name,
                            "xml_line": str(line_no),
                            "text_id": text_id,
                            "xml": line.strip(),
                            "actual_display_text": actual,
                        }
                    )
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, str]] = []
    for title in ["tda01", "tda02", "tda03"]:
        repack_dir = ROOT / "outputs" / f"repack_{title}_xmlsafe_20260617b"
        rows = audit_title(title, repack_dir)
        all_rows.extend(rows)
        print(title, len(rows))
    out = OUT_DIR / "called_text_ids_empty_display_20260617b.csv"
    fields = ["title", "file", "xml_line", "text_id", "xml", "actual_display_text"]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_rows)
    print(out)


if __name__ == "__main__":
    main()
