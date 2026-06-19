import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "outputs" / "qa" / "name_review" / "muvluv_tda01-03_exhaustive_unit_ship_callsign_audit.csv"
OUT = ROOT / "outputs" / "qa" / "name_review" / "muvluv_tda01-03_proper_nouns_only_for_decision.csv"


PROPER_BASES = {
    "ウォードッグ",
    "ウォードック",
    "ワードッグ",
    "イーグル",
    "カロネード",
    "ドレイク・カロネード",
    "フェザント",
    "ナイトオウル",
    "ブラックナイヴス",
    "ナイヴス",
    "ブラックバード",
    "ホーンド",
    "ボクサー",
    "クレイン",
    "クレインズ",
    "ハンター",
    "ハンターズ",
    "サラマンダー",
    "サラマンダーズ",
    "ラトルスネーク",
    "マザーグース",
    "大和",
    "JFK",
    "ＪＦＫ",
    "ラプター",
    "ファントム",
    "デモ隊",
}

PROPER_PHRASE_MARKERS = (
    "日本帝国欧州派遣軍",
    "米国海兵隊戦術機部隊",
    "帝国陸軍特殊作戦団",
    "国連宇宙総軍",
    "帝国連合艦隊",
    "帝国艦隊",
    "日本艦隊",
    "米国艦隊",
    "米国海軍戦術機母艦",
    "米国陸軍第",
    "強襲揚陸艦ボクサー",
    "装甲駆逐艦マザーグース",
)

DROP_IF_CONTAINS = (
    "了解",
    "被弾",
    "大破",
    "準備完了",
    "出撃",
    "発進",
    "各員",
    "各機",
    "全機",
    "両機",
    "両隊",
    "全艦",
    "斉射",
    "艦砲射撃",
    "乗艦",
    "揚陸艦",
    "戦艦",
    "艦長",
    "副長",
    "オペレーター",
    "リード",
    "隊メンバー",
    "隊リーダー",
    "直接デモ隊",
    "一番デモ隊",
)

GENERIC_EXACT = {
    "デモ隊",
    "艦隊",
    "帝国艦隊",
    "日本艦隊",
    "米国艦隊",
    "戦術機母艦",
    "大型揚陸艦",
    "最上級大型巡洋艦",
    "旧式艦",
    "退役艦",
    "母艦級",
    "潜水母艦",
    "潜水艦",
    "駆逐艦",
    "装甲駆逐艦",
}


def normalize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[１２３４５６７８９０0-9]+$", "", name)
    name = name.replace("ウォードック", "ウォードッグ")
    name = name.replace("ワードッグ", "ウォードッグ")
    name = name.replace("ウォードッグス", "ウォードッグ")
    name = name.replace("クレインズ", "クレイン")
    name = name.replace("ハンターズ", "ハンター")
    name = name.replace("サラマンダーズ", "サラマンダー")
    if name.startswith("オール・"):
        name = name.removeprefix("オール・")
    if name.endswith("小隊"):
        return name
    if name.endswith("隊") and name[:-1] in PROPER_BASES:
        return name
    return name


def base_hit(name: str) -> str | None:
    for base in sorted(PROPER_BASES, key=len, reverse=True):
        if base in name:
            return base
    return None


def keep(row: dict) -> tuple[bool, str]:
    name = row["jp_name"]
    if name in GENERIC_EXACT:
        return False, ""
    if any(x in name for x in DROP_IF_CONTAINS):
        return False, ""
    marker = next((x for x in PROPER_PHRASE_MARKERS if x in name), "")
    if marker:
        return True, normalize_name(name)
    hit = base_hit(name)
    if not hit:
        return False, ""
    if name in PROPER_BASES:
        return True, normalize_name(name)
    if name.endswith(("小隊", "中隊", "隊")) and hit in name:
        return True, normalize_name(name)
    if "・" in name and hit in name:
        return True, normalize_name(name)
    if row["priority"] == "high_named" and hit in name and len(name) <= len(hit) + 2:
        return True, normalize_name(hit)
    return False, ""


def compact(values, limit=5):
    return " | ".join(list(dict.fromkeys(v for v in values if v))[:limit])


def main():
    grouped = defaultdict(lambda: {
        "titles": [],
        "jp_names": [],
        "current_cn": [],
        "kind_hint": [],
        "ids": [],
        "examples_jp": [],
        "examples_cn": [],
    })

    with SRC.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ok, canonical = keep(row)
            if not ok:
                continue
            item = grouped[canonical]
            item["titles"].append(row["title"])
            item["jp_names"].append(row["jp_name"])
            item["current_cn"].append(row.get("current_speaker_cn", ""))
            item["kind_hint"].append(row["kind_hint"])
            item["ids"].extend((row.get("ids") or "").split(" | "))
            item["examples_jp"].append(row.get("example_jp", ""))
            item["examples_cn"].append(row.get("example_cn", ""))

    rows = []
    for canonical, item in grouped.items():
        rows.append({
            "jp_name": canonical,
            "titles": compact(item["titles"], 3),
            "current_cn_variants": compact(item["current_cn"], 8),
            "kind_hint": compact(item["kind_hint"], 3),
            "count_ids": len(set(i for i in item["ids"] if i)),
            "all_jp_variants_seen": compact(item["jp_names"], 10),
            "sample_ids": compact(item["ids"], 10),
            "sample_jp": compact(item["examples_jp"], 3),
            "sample_cn": compact(item["examples_cn"], 3),
            "decision": "",
            "note": "",
        })

    rows.sort(key=lambda r: (r["jp_name"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"out={OUT}")
    print(f"rows={len(rows)}")


if __name__ == "__main__":
    main()
