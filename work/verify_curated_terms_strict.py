from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATHS = {
    "tda01": ROOT / "outputs" / "tda_text" / "tda01_deepseek_full.csv",
    "tda02": ROOT / "outputs" / "tda_text" / "tda02_deepseek_full.csv",
    "tda03": ROOT / "outputs" / "tda_text" / "tda03_deepseek_full.csv",
}
CACHE_PATHS = {
    "tda01": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda01\data\root\assets\data_spec\adv\game\scr\localized"),
    "tda02": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda02\data\root\assets\data_spec\adv\game\scr\localized"),
    "tda03": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda03\data\root\assets\data_spec\adv\game\scr\localized"),
}
FULL_GLOSSARY = ROOT / "outputs" / "glossary" / "muvluv_lunatranslator_full_glossary.csv"
PROPER_NOUNS = ROOT / "outputs" / "glossary" / "muvluv_lunatranslator_proper_nouns.tsv"
OUT_DIR = ROOT / "outputs" / "qa" / "name_review"
MISS_OUT = OUT_DIR / "curated_terms_strict_source_misses.csv"
CACHE_OUT = OUT_DIR / "curated_terms_strict_cache_residuals.csv"
SUMMARY_OUT = OUT_DIR / "curated_terms_strict_summary.txt"


TERM_RULES = [
    ("イーグル", ("イーグル",), ("鹰",)),
    ("ウォードッグ", ("ウォードッグ", "ウォードック", "ワードッグ"), ("战犬",)),
    ("ウォードッグ小隊", ("ウォードッグ小隊",), ("战犬小队",)),
    ("ウォードッグ隊", ("ウォードッグ隊",), ("战犬队", "战犬")),
    ("カロネード", ("カロネード",), ("卡洛内德",)),
    ("カロネード隊", ("カロネード隊",), ("卡洛内德队", "卡洛内德")),
    ("ドレイク", ("ドレイク",), ("德雷克",)),
    ("ドレイク・カロネード", ("ドレイク・カロネード",), ("德雷克", "卡洛内德")),
    ("クレイン", ("クレイン", "クレインズ"), ("鹤",)),
    ("クレイン中隊", ("クレイン中隊",), ("鹤中队",)),
    ("サラマンダー", ("サラマンダー", "サラマンダーズ"), ("蝾螈",)),
    ("サラマンダー隊", ("サラマンダー隊",), ("蝾螈队", "蝾螈")),
    ("ナイトオウル", ("ナイトオウル",), ("夜枭",)),
    ("ナイトオウル隊", ("ナイトオウル隊",), ("夜枭飞行队", "夜枭队", "夜枭")),
    ("ナイヴス", ("ナイヴス",), ("黑刃",)),
    ("ブラックナイヴス", ("ブラックナイヴス",), ("黑刃",)),
    ("ブラックナイヴス小隊", ("ブラックナイヴス小隊",), ("黑刃小队", "黑刃")),
    ("ブラックバード", ("ブラックバード",), ("黑鸟",)),
    ("ホーンド", ("ホーンド",), ("号角",)),
    ("ホーンド中隊", ("ホーンド中隊",), ("号角中队", "号角")),
    ("ハンター", ("ハンター", "ハンターズ"), ("猎人",)),
    ("ハンターズ", ("ハンターズ",), ("猎人队", "猎人")),
    ("フェザント", ("フェザント",), ("雉鸡",)),
    ("フェザント中隊", ("フェザント中隊",), ("雉鸡中队", "雉鸡")),
    ("ボクサー", ("ボクサー",), ("拳师号",)),
    ("強襲揚陸艦ボクサー", ("強襲揚陸艦ボクサー",), ("强袭登陆舰拳师号", "拳师号")),
    ("マザーグース", ("マザーグース",), ("鹅妈妈",)),
    ("装甲駆逐艦マザーグース", ("装甲駆逐艦マザーグース",), ("装甲驱逐舰鹅妈妈号", "鹅妈妈")),
    ("ラトルスネーク", ("ラトルスネーク",), ("响尾蛇",)),
    ("ラプター", ("ラプター",), ("猛禽",)),
    ("大和", ("大和",), ("大和",)),
    ("ＪＦＫ", ("ＪＦＫ",), ("JFK",)),
    ("JFK", ("JFK",), ("JFK",)),
    ("帝国連合艦隊", ("帝国連合艦隊",), ("帝国联合舰队",)),
    ("日本帝国欧州派遣軍", ("日本帝国欧州派遣軍",), ("日本帝国欧洲派遣军",)),
    ("日本帝国欧州派遣軍イーグル中隊", ("日本帝国欧州派遣軍イーグル中隊",), ("日本帝国欧洲派遣军鹰中队", "鹰中队")),
    ("帝国陸軍特殊作戦団第一歩兵連隊第一中隊", ("帝国陸軍特殊作戦団第一歩兵連隊第一中隊",), ("帝国陆军特殊作战团第一步兵连第一中队",)),
    ("米国海兵隊戦術機部隊ブラックナイヴス", ("米国海兵隊戦術機部隊ブラックナイヴス",), ("美国海军陆战队战术机部队黑刃队", "黑刃队")),
    ("米国海軍戦術機母艦", ("米国海軍戦術機母艦",), ("美国海军战术机母舰",)),
    ("米国陸軍第１軍団第６６戦術機甲大隊", ("米国陸軍第１軍団第６６戦術機甲大隊",), ("美国陆军第1军团第66战术机甲大队",)),
    ("米国陸軍第６６戦術機甲大隊", ("米国陸軍第６６戦術機甲大隊",), ("美国陆军第66战术机甲大队",)),
    ("国連宇宙総軍第６軌道降下兵団", ("国連宇宙総軍第６軌道降下兵団",), ("联合国宇宙总军第6轨道降下兵团",)),
]


OLD_BAD_TERMS = [
    "博克瑟",
    "拳击手号",
    "拳击手",
    "伊格尔",
    "菲桑特",
    "费桑特",
    "野鸡",
    "火蜥蜴",
    "萨拉曼达",
    "ＪＦＫ",
    "ＨＩＶＥ",
    "ＢＥＴＡ",
    "肯尼迪HIVE",
    "美国陆军第1军第66战术机甲大队",
    "卡洛纳德",
    "卡隆炮",
    "德莱克",
]

GLOSSARY_EXPECTED = {
    "イーグル": "鹰",
    "ウォードッグ": "战犬",
    "ウォードッグ小隊": "战犬小队",
    "ウォードッグ隊": "战犬队",
    "カロネード": "卡洛内德",
    "カロネード隊": "卡洛内德队",
    "ドレイク": "德雷克",
    "ドレイク・カロネード": "德雷克、卡洛内德",
    "クレイン": "鹤",
    "クレイン中隊": "鹤中队",
    "サラマンダー": "蝾螈",
    "サラマンダー隊": "蝾螈队",
    "ナイトオウル": "夜枭",
    "ナイトオウル隊": "夜枭飞行队",
    "ナイヴス": "黑刃",
    "ブラックナイヴス": "黑刃队",
    "ブラックナイヴス小隊": "黑刃小队",
    "ブラックバード": "黑鸟",
    "ホーンド": "号角",
    "ホーンド中隊": "号角中队",
    "ハンター": "猎人",
    "ハンターズ": "猎人队",
    "フェザント": "雉鸡",
    "フェザント中隊": "雉鸡中队",
    "ボクサー": "拳师号",
    "強襲揚陸艦ボクサー": "强袭登陆舰拳师号",
    "マザーグース": "鹅妈妈号",
    "装甲駆逐艦マザーグース": "装甲驱逐舰鹅妈妈号",
    "ラトルスネーク": "响尾蛇",
    "ラプター": "猛禽",
    "大和": "大和",
    "ＪＦＫ": "JFK",
    "JFK": "JFK",
    "帝国連合艦隊": "帝国联合舰队",
    "日本帝国欧州派遣軍": "日本帝国欧洲派遣军",
    "日本帝国欧州派遣軍イーグル中隊": "日本帝国欧洲派遣军鹰中队",
    "帝国陸軍特殊作戦団第一歩兵連隊第一中隊": "帝国陆军特殊作战团第一步兵连第一中队",
    "米国海兵隊戦術機部隊ブラックナイヴス": "美国海军陆战队战术机部队黑刃队",
    "米国海軍戦術機母艦": "美国海军战术机母舰",
    "米国陸軍第１軍団第６６戦術機甲大隊": "美国陆军第1军团第66战术机甲大队",
    "米国陸軍第６６戦術機甲大隊": "美国陆军第66战术机甲大队",
    "国連宇宙総軍第６軌道降下兵団": "联合国宇宙总军第6轨道降下兵团",
}


def load_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for title, path in CSV_PATHS.items():
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rows.append(
                    {
                        "title": title,
                        "file": Path(row.get("file", "")).name,
                        "id": row.get("id", ""),
                        "jp": row.get("jp", "") or "",
                        "cn": row.get("zh_deepseek", "") or "",
                    }
                )
    return rows


def verify_source(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], Counter]:
    misses = []
    counts: Counter = Counter()
    for row in rows:
        jp = row["jp"]
        cn = row["cn"]
        for rule_name, markers, targets in TERM_RULES:
            if any(marker in jp for marker in markers):
                counts[rule_name] += 1
                if not any(target in cn for target in targets):
                    misses.append(
                        {
                            "title": row["title"],
                            "id": row["id"],
                            "rule": rule_name,
                            "expected_any": " / ".join(targets),
                            "jp": jp,
                            "cn": cn,
                        }
                    )
    return misses, counts


def scan_bad_source(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    hits = []
    for row in rows:
        cn = row["cn"]
        for term in OLD_BAD_TERMS:
            if term in cn:
                hits.append({"scope": "source", "title": row["title"], "id_or_file": row["id"], "term": term, "text": cn})
    return hits


def scan_bad_cache() -> list[dict[str, str]]:
    hits = []
    for title, root in CACHE_PATHS.items():
        if not root.exists():
            hits.append({"scope": "cache_missing", "title": title, "id_or_file": str(root), "term": "", "text": ""})
            continue
        for path in root.glob("*.egpack"):
            data = path.read_bytes()
            text = data.decode("utf-8", "ignore")
            for term in OLD_BAD_TERMS:
                if term in text:
                    hits.append({"scope": "cache", "title": title, "id_or_file": path.name, "term": term, "text": ""})
    return hits


def load_full_glossary() -> dict[str, str]:
    with FULL_GLOSSARY.open(encoding="utf-8-sig", newline="") as f:
        return {row["source"]: row["target"] for row in csv.DictReader(f) if row.get("source")}


def load_proper_nouns() -> dict[str, str]:
    out = {}
    with PROPER_NOUNS.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) >= 2:
                out[row[0]] = row[1]
    return out


def verify_glossaries() -> list[dict[str, str]]:
    full = load_full_glossary()
    proper = load_proper_nouns()
    misses = []
    for source, target in GLOSSARY_EXPECTED.items():
        # For more specific names, the first target can intentionally be shorter
        # in source rows; glossary itself should match the canonical table.
        for label, table in (("full_glossary", full), ("proper_nouns", proper)):
            got = table.get(source)
            if got != target:
                misses.append({"scope": label, "title": "", "id_or_file": source, "term": target, "text": got or ""})
    return misses


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = load_rows()
    misses, counts = verify_source(rows)
    bad_source = scan_bad_source(rows)
    bad_cache = scan_bad_cache()
    glossary_misses = verify_glossaries()

    write_csv(MISS_OUT, misses, ["title", "id", "rule", "expected_any", "jp", "cn"])
    write_csv(CACHE_OUT, bad_source + bad_cache + glossary_misses, ["scope", "title", "id_or_file", "term", "text"])

    lines = [
        f"source_rows={len(rows)}",
        f"source_term_misses={len(misses)}",
        f"old_bad_source_hits={len(bad_source)}",
        f"old_bad_cache_hits={len(bad_cache)}",
        f"glossary_misses={len(glossary_misses)}",
        "",
        "term_occurrence_counts:",
    ]
    for name, count in sorted(counts.items()):
        lines.append(f"{name}: {count}")
    SUMMARY_OUT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines[:5]))
    print(f"misses={MISS_OUT}")
    print(f"residuals={CACHE_OUT}")
    print(f"summary={SUMMARY_OUT}")


if __name__ == "__main__":
    main()
