import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATHS = {
    "tda01": ROOT / "outputs" / "tda_text" / "tda01_deepseek_full.csv",
    "tda02": ROOT / "outputs" / "tda_text" / "tda02_deepseek_full.csv",
    "tda03": ROOT / "outputs" / "tda_text" / "tda03_deepseek_full.csv",
}
OUT = ROOT / "outputs" / "qa" / "name_review" / "muvluv_tda01-03_proper_nouns_only_curated.csv"


PROPER_NAMES = [
    "イーグル",
    "ウォードッグ",
    "ウォードッグ小隊",
    "ウォードッグ隊",
    "カロネード",
    "カロネード隊",
    "ドレイク・カロネード",
    "クレイン",
    "クレイン中隊",
    "サラマンダー",
    "サラマンダー隊",
    "ナイトオウル",
    "ナイトオウル隊",
    "ナイヴス",
    "ブラックナイヴス",
    "ブラックナイヴス小隊",
    "ブラックバード",
    "ホーンド",
    "ホーンド中隊",
    "ハンター",
    "ハンターズ",
    "フェザント",
    "フェザント中隊",
    "ボクサー",
    "強襲揚陸艦ボクサー",
    "マザーグース",
    "装甲駆逐艦マザーグース",
    "ラトルスネーク",
    "ラプター",
    "大和",
    "ＪＦＫ",
    "JFK",
    "帝国連合艦隊",
    "日本帝国欧州派遣軍",
    "日本帝国欧州派遣軍イーグル中隊",
    "帝国陸軍特殊作戦団第一歩兵連隊第一中隊",
    "米国海兵隊戦術機部隊ブラックナイヴス",
    "米国海軍戦術機母艦",
    "米国陸軍第１軍団第６６戦術機甲大隊",
    "米国陸軍第６６戦術機甲大隊",
    "国連宇宙総軍第６軌道降下兵団",
]

ALIASES = {
    "ウォードック": "ウォードッグ",
    "ワードッグ": "ウォードッグ",
    "ウォードッグス": "ウォードッグ",
    "クレインズ": "クレイン",
    "サラマンダーズ": "サラマンダー",
    "ホーンド３": "ホーンド",
    "ナイヴス１": "ナイヴス",
    "ナイヴス２": "ナイヴス",
    "ナイヴス３": "ナイヴス",
    "ナイヴス４": "ナイヴス",
}

CONTROL_RE = re.compile(r"\\[A-Za-z0-9_]+")


def clean(text: str) -> str:
    return CONTROL_RE.sub("", text or "").strip()


def kind(name: str) -> str:
    if any(x in name for x in ("艦", "ボクサー", "マザーグース", "大和", "ＪＦＫ", "JFK")):
        return "ship_or_operation"
    if any(x in name for x in ("軍", "兵団", "艦隊")):
        return "organization"
    if any(x in name for x in ("小隊", "中隊", "隊")):
        return "unit"
    return "callsign"


def compact(values, limit=6):
    return " | ".join(list(dict.fromkeys(v for v in values if v))[:limit])


def main():
    names = set(PROPER_NAMES)
    names.update(ALIASES)
    grouped = defaultdict(lambda: {
        "titles": [],
        "ids": [],
        "jp_variants": [],
        "cn_examples": [],
        "jp_examples": [],
    })

    for title, path in CSV_PATHS.items():
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                jp = clean(row.get("jp", ""))
                cn = clean(row.get("zh_deepseek", ""))
                if not jp:
                    continue
                for name in names:
                    if name in jp:
                        canonical = ALIASES.get(name, name)
                        item = grouped[canonical]
                        item["titles"].append(title)
                        item["ids"].append(row.get("id", ""))
                        item["jp_variants"].append(name)
                        item["jp_examples"].append(jp)
                        item["cn_examples"].append(cn)

    rows = []
    for name in PROPER_NAMES:
        if name in ALIASES:
            continue
        item = grouped.get(name)
        if not item:
            continue
        rows.append({
            "jp_name": name,
            "kind": kind(name),
            "titles": compact(item["titles"], 3),
            "count_ids": len(set(item["ids"])),
            "jp_variants_seen": compact(item["jp_variants"], 12),
            "sample_ids": compact(item["ids"], 12),
            "sample_jp": compact(item["jp_examples"], 3),
            "sample_cn": compact(item["cn_examples"], 3),
            "decision": "",
            "note": "",
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"out={OUT}")
    print(f"rows={len(rows)}")


if __name__ == "__main__":
    main()
