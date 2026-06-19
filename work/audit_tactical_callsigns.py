from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = ROOT / "outputs" / "tda_text"
OUT = ROOT / "outputs" / "qa" / "tactical_callsign_audit.csv"

CSV_PATHS = {
    "tda01": TEXT_DIR / "tda01_deepseek_full.csv",
    "tda02": TEXT_DIR / "tda02_deepseek_full.csv",
    "tda03": TEXT_DIR / "tda03_deepseek_full.csv",
}

JP_PATTERNS = [
    re.compile(r"([ァ-ヴー・]+)(?:[１２３４５６７８９０0-9]+|・リード|リード|隊|小隊|中隊|各機|ス)"),
    re.compile(r"(ブラック・ナイヴス|ブラックナイヴス|ナイトオウル|ウォードッグ|フェザント|クレイン|ハンターズ|ハンター|ホーネット|ホーン|ロレーヌ|ナイヴス|サラマンダー|マザーグース|ラットルスネイク|ボクサー)"),
]

EN_PATTERNS = [
    re.compile(r"\b(Wardogs?|Crane|Hunters?|Black Knives|Night Owl|Pheasant|Horn|Lorraine|Knives|Salamander|Mother Goose|Rattlesnake|Boxer|Carronade|Drake)(?:\s*(?:Leader|Lead|Flight|Squadron|Squad|Company|Team|[0-9]+|Flight))?\b", re.I),
]

KNOWN = {
    "ウォードッグ", "クレイン", "ハンター", "ハンターズ", "ブラック・ナイヴス",
    "ブラックナイヴス", "ナイトオウル", "フェザント", "ホーン", "ホーネット",
    "ロレーヌ", "ナイヴス", "サラマンダー", "マザーグース", "ラットルスネイク",
    "ボクサー",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    audit_rows: list[dict[str, str]] = []
    counts: Counter[tuple[str, str, str]] = Counter()
    examples: dict[tuple[str, str, str], dict[str, str]] = {}

    for title, path in CSV_PATHS.items():
        for row in read_rows(path):
            jp = row.get("jp", "")
            en = row.get("en", "")
            zh = row.get("zh_deepseek", "")
            found: set[tuple[str, str]] = set()
            for pattern in JP_PATTERNS:
                for match in pattern.finditer(jp):
                    term = match.group(1)
                    if term in KNOWN:
                        found.add(("jp", term))
            for pattern in EN_PATTERNS:
                for match in pattern.finditer(en):
                    found.add(("en", match.group(1)))

            for lang, term in sorted(found):
                key = (title, lang, term)
                counts[key] += 1
                examples.setdefault(key, row)
                audit_rows.append(
                    {
                        "title": title,
                        "lang": lang,
                        "term": term,
                        "file": row.get("file", ""),
                        "id": row.get("id", ""),
                        "jp": jp,
                        "en": en,
                        "zh": zh,
                    }
                )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "lang", "term", "file", "id", "jp", "en", "zh"])
        writer.writeheader()
        writer.writerows(audit_rows)

    for key, count in sorted(counts.items()):
        row = examples[key]
        print(f"{key[0]} {key[1]} {key[2]} count={count} example={row.get('id')} zh={row.get('zh_deepseek','')[:100]}")
    print(f"audit={OUT} rows={len(audit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
