from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "outputs" / "qa"

SLOT_FILES = {
    "tda01": QA / "tda01_current_slots.csv",
    "tda02": QA / "tda02_current_slots.csv",
    "tda03": QA / "tda03_current_slots.csv",
}

BAD_TERMS = {
    "pilot_as_flyer": ["地表飞行员", "美国地表飞行员", "美国飞行员", "飞行员", "驾驶员", "驾驶者", "飞行兵"],
    "miono_as_shizuka": ["结识静", "认识静", "见到静", "感谢静", "和静", "跟静", "对静", "小静", "静少尉"],
    "bad_callsign_chick": ["雏鸡长机", "雏鸡"],
    "unfixed_english_name": ["Miono", "Shizuku", "Yuzuka", "Sendo", "Tatsunami", "Jinguuji", "Marimo"],
    "unknown_speaker": ["【?】", "speaker=?", "speaker=？"],
    "text_not_found": ["Text ID Not Found"],
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def display_text(row: dict[str, str]) -> str:
    jp = row.get("jp") or ""
    if jp.strip():
        return jp
    en = row.get("en") or ""
    # In the JP-baseline package, original English language slots intentionally
    # remain English. Only treat the en field as visible Chinese when it actually
    # contains CJK, such as speaker fallback names.
    if any("\u4e00" <= ch <= "\u9fff" for ch in en):
        return en
    return ""


def main() -> None:
    findings: list[dict[str, str]] = []
    for title, path in SLOT_FILES.items():
        for row in read_rows(path):
            text = display_text(row)
            if not text:
                continue
            for kind, terms in BAD_TERMS.items():
                for term in terms:
                    if term in text:
                        findings.append(
                            {
                                "title": title,
                                "kind": kind,
                                "term": term,
                                "file": row.get("file", ""),
                                "id": row.get("id", ""),
                                "jp": row.get("jp", ""),
                                "en": row.get("en", ""),
                                "display": text,
                            }
                        )

    out = QA / "tda_glossary_findings.json"
    out.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"findings={len(findings)} output={out}")
    counts: dict[tuple[str, str], int] = {}
    for item in findings:
        key = (item["title"], item["kind"])
        counts[key] = counts.get(key, 0) + 1
    for (title, kind), count in sorted(counts.items()):
        print(f"{title} {kind}: {count}")
    for item in findings[:80]:
        print(f"[{item['title']}] {item['kind']} {item['id']} {item['term']} :: {item['display'][:160]}")


if __name__ == "__main__":
    main()
