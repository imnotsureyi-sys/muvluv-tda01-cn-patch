from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ID_RE = re.compile(r"(?:game_[ts]|tda03_[ts]|tda02_staff)\d+(?:_ruby)?")
JP_RUN_RE = re.compile(r"[\u3000-\u9fff\u3040-\u30ff\uff00-\uffef][^\x00\udc80-\udcff]*")
PRINTABLE_RUN_RE = re.compile(r"[^\x00\udc80-\udcff]+")
CONTROL_RE = re.compile(r"\\[A-Za-z]")


def visible_before_id(path: Path) -> list[dict[str, str]]:
    data = path.read_bytes()
    if not data.startswith(b"EPK\0"):
        return []
    text = data.decode("utf-8", "surrogateescape")
    matches = list(ID_RE.finditer(text))
    rows: list[dict[str, str]] = []
    previous_id_end = 0
    for match in matches:
        tid = match.group()
        if tid.endswith("_ruby"):
            previous_id_end = match.end()
            continue
        segment = text[previous_id_end : match.start()]
        previous_id_end = match.end()
        before_p = segment.rsplit("\\p", 1)[0] if "\\p" in segment else segment
        runs = [r.group(0).strip() for r in PRINTABLE_RUN_RE.finditer(before_p)]
        runs = [r for r in runs if is_display_candidate(r)]
        display = runs[-1] if runs else ""
        marker = display.rfind("�")
        if marker >= 0:
            display = display[marker + 1 :]
        rows.append({"file": path.name, "id": tid, "display": normalize(display)})
    return rows


def normalize(text: str) -> str:
    return (text or "").replace("\x00", "").replace("\r", "").replace("\n", "\\n").strip()


def is_display_candidate(text: str) -> bool:
    text = normalize(text)
    if not text or text == "Pg9":
        return False
    if ID_RE.fullmatch(text) or text.startswith(("game_", "tda02_staff", "tda03_")):
        return False
    # Ignore tiny printable fragments that are part of binary/control payloads.
    if len(text) <= 3 and not re.search(r"[\u3000-\u9fff\u3040-\u30ff\uff00-\uffef!?！？…—―]", text):
        return False
    if not re.search(r"[\u3000-\u9fff\u3040-\u30ff\uff00-\uffefA-Za-z0-9!?！？…—―]", text):
        return False
    return True


def compact(text: str) -> str:
    if (text or "").strip() == "Pg9":
        return ""
    text = CONTROL_RE.sub("", text or "")
    for ch in "「」『』":
        text = text.replace(ch, "")
    return re.sub(r"[\s　。．\.、，,！？!?…—―ー～~・\-]+", "", text)


def has_kana(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff]", text or ""))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args()

    original_rows: list[dict[str, str]] = []
    current_rows: list[dict[str, str]] = []
    for path in sorted(args.original.glob("*.egpack")):
        original_rows.extend(visible_before_id(path))
    for path in sorted(args.current.glob("*.egpack")):
        current_rows.extend(visible_before_id(path))

    original = {(r["file"], r["id"]): r for r in original_rows}
    current = {(r["file"], r["id"]): r for r in current_rows}

    findings: list[dict[str, str]] = []
    for key, src in original.items():
        cur = current.get(key)
        if cur is None:
            findings.append({"kind": "missing_id", "file": key[0], "id": key[1], "source": src["display"], "current": ""})
            continue
        source = src["display"]
        text = cur["display"]
        if compact(source) and not compact(text):
            findings.append({"kind": "blank_display", "file": key[0], "id": key[1], "source": source, "current": text})
        if "Text ID Not Found" in text or "□" in text or "�" in text:
            findings.append({"kind": "bad_marker", "file": key[0], "id": key[1], "source": source, "current": text})
        if compact(source) and has_kana(text):
            findings.append({"kind": "japanese_left", "file": key[0], "id": key[1], "source": source, "current": text})

    by_file: dict[str, list[dict[str, str]]] = {}
    for row in current_rows:
        by_file.setdefault(row["file"], []).append(row)
    for file_name, rows in by_file.items():
        for prev, row in zip(rows, rows[1:]):
            if not compact(row["display"]) or row["display"] != prev["display"]:
                continue
            src = original.get((file_name, row["id"]), {}).get("display", "")
            prev_src = original.get((file_name, prev["id"]), {}).get("display", "")
            if compact(src) and compact(prev_src) and src != prev_src:
                findings.append(
                    {
                        "kind": "adjacent_duplicate",
                        "file": file_name,
                        "id": f"{prev['id']} => {row['id']}",
                        "source": src,
                        "current": row["display"],
                    }
                )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.csv_out:
        args.csv_out.parent.mkdir(parents=True, exist_ok=True)
        with args.csv_out.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["file", "id", "display"])
            writer.writeheader()
            writer.writerows(current_rows)

    print(f"original={len(original_rows)} current={len(current_rows)} findings={len(findings)} out={args.out}")
    for item in findings[:80]:
        print(item["kind"], item["file"], item["id"], "=>", item["current"][:120])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
