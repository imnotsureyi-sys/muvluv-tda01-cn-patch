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
OUT_DIR = ROOT / "outputs" / "qa" / "name_review"
OUT_CSV = OUT_DIR / "muvluv_tda01-03_military_unit_ship_name_candidates.csv"
OUT_MENTIONS = OUT_DIR / "muvluv_tda01-03_military_unit_ship_name_mentions.csv"
OUT_REVIEW = OUT_DIR / "muvluv_tda01-03_callsign_ship_unit_names_for_decision.csv"
OUT_NAMED_REVIEW = OUT_DIR / "muvluv_tda01-03_named_callsign_ship_unit_names_for_decision.csv"


JP_KEYWORDS = (
    "小隊",
    "中隊",
    "大隊",
    "戦隊",
    "部隊",
    "隊",
    "軍",
    "海兵隊",
    "衛士",
    "兵",
    "艦",
    "艦隊",
    "揚陸艦",
    "母艦",
    "指揮所",
    "基地",
    "ハイヴ",
    "HIVE",
    "ＨＩＶＥ",
    "オペレーター",
    "ＯＰ",
    "OP",
    "リード",
    "長機",
    "フライト",
)

CN_KEYWORDS = (
    "小队",
    "中队",
    "大队",
    "部队",
    "队",
    "军",
    "海军陆战队",
    "卫士",
    "兵",
    "舰",
    "号",
    "指挥所",
    "基地",
    "操作员",
    "长机",
)

CALLSIGN_BASES = (
    "ウォードッグ",
    "イーグル",
    "フェザント",
    "カロネード",
    "デモ隊",
    "ナイトオウル",
    "ブラックナイヴス",
    "ナイヴス",
    "ブラックバード",
    "ブラックナイブス",
    "ボクサー",
    "ホーンド",
    "ホーネット",
    "ハンター",
    "サラマンダー",
    "クレイン",
    "ラトルスネーク",
    "マザーグース",
    "フォックス",
    "ファントム",
    "ラプター",
)

REVIEW_HINTS = (
    "ウォードッグ",
    "イーグル",
    "フェザント",
    "カロネード",
    "デモ隊",
    "ナイトオウル",
    "ブラックナイヴス",
    "ナイヴス",
    "ブラックバード",
    "ブラックナイブス",
    "ボクサー",
    "ホーンド",
    "ホーネット",
    "ハンター",
    "サラマンダー",
    "クレイン",
    "ラトルスネーク",
    "マザーグース",
    "小隊",
    "中隊",
    "大隊",
    "戦隊",
    "揚陸艦",
    "艦",
)

PROPER_HINTS = (
    "第",
    "帝国",
    "米国",
    "国連",
    "フランス",
    "カナダ",
    "欧州",
    "横浜",
    "西雅図",
    "シアトル",
    "大和",
    "JFK",
    "ＪＦＫ",
)

GENERIC_REVIEW_TERMS = {
    "小隊",
    "中隊",
    "大隊",
    "部隊",
    "隊",
    "軍",
    "衛士",
    "兵",
    "艦",
    "艦隊",
    "長機",
    "指揮所",
    "基地",
    "オペレーター",
}

SPLIT_RE = re.compile(r"[\s　、。！？!?「」『』（）()\[\]【】,.;:：；…—―・]+")
TOKEN_RE = re.compile(r"[0-9A-Za-zＡ-Ｚａ-ｚァ-ヴー一-龯々]+")


def clean(text: str) -> str:
    return (text or "").replace("\\w", "").replace("\\p", "").replace("\\n", " ").strip()


def load_rows():
    rows = []
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


def is_speaker(row) -> bool:
    ident = row["id"]
    return "_s" in ident or ident.endswith("_staff00000")


def military_like(jp: str, cn: str) -> bool:
    return any(k in jp for k in JP_KEYWORDS) or any(k in cn for k in CN_KEYWORDS) or any(k in jp for k in CALLSIGN_BASES)


def base_term(term: str) -> str:
    term = re.sub(r"[0-9０-９]+$", "", term)
    term = term.replace("ＯＰ", "オペレーター")
    return term


def extract_text_terms(jp: str) -> set[str]:
    text = clean(jp)
    found: set[str] = set()
    for base in CALLSIGN_BASES:
        if base in text:
            found.add(base)
    for piece in SPLIT_RE.split(text):
        if not piece or len(piece) > 40:
            continue
        if not any(k in piece for k in JP_KEYWORDS):
            continue
        tokens = TOKEN_RE.findall(piece)
        for token in tokens:
            if len(token) < 2 or len(token) > 28:
                continue
            if any(k in token for k in JP_KEYWORDS) or any(base in token for base in CALLSIGN_BASES):
                found.add(token)
    return found


def compact_examples(items, limit=5):
    return " | ".join(items[:limit])


def main():
    rows = load_rows()
    candidates = {}
    mentions = defaultdict(list)

    for row in rows:
        jp = clean(row["jp"])
        cn = clean(row["cn"])
        if not jp:
            continue

        if is_speaker(row) and military_like(jp, cn):
            key = (row["title"], base_term(jp), cn)
            item = candidates.setdefault(
                key,
                {
                    "source_type": "speaker",
                    "title": row["title"],
                    "jp_term": base_term(jp),
                    "current_cn": cn,
                    "ids": [],
                    "files": [],
                    "examples_jp": [],
                    "examples_cn": [],
                },
            )
            item["ids"].append(row["id"])
            item["files"].append(row["file"])
            item["examples_jp"].append(jp)
            item["examples_cn"].append(cn)

        for term in extract_text_terms(jp):
            key = (row["title"], base_term(term), "")
            item = candidates.setdefault(
                key,
                {
                    "source_type": "text_keyword",
                    "title": row["title"],
                    "jp_term": base_term(term),
                    "current_cn": "",
                    "ids": [],
                    "files": [],
                    "examples_jp": [],
                    "examples_cn": [],
                },
            )
            item["ids"].append(row["id"])
            item["files"].append(row["file"])
            item["examples_jp"].append(jp)
            item["examples_cn"].append(cn)
            mentions[(row["title"], base_term(term))].append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_type",
                "title",
                "jp_term",
                "current_cn",
                "count",
                "ids",
                "files",
                "example_jp",
                "example_cn",
            ],
        )
        writer.writeheader()
        for item in sorted(candidates.values(), key=lambda x: (x["title"], x["source_type"], x["jp_term"])):
            writer.writerow(
                {
                    "source_type": item["source_type"],
                    "title": item["title"],
                    "jp_term": item["jp_term"],
                    "current_cn": item["current_cn"],
                    "count": len(set(item["ids"])),
                    "ids": compact_examples(list(dict.fromkeys(item["ids"]))),
                    "files": compact_examples(list(dict.fromkeys(item["files"])), 3),
                    "example_jp": compact_examples(list(dict.fromkeys(item["examples_jp"])), 2),
                    "example_cn": compact_examples(list(dict.fromkeys(item["examples_cn"])), 2),
                }
            )

    with OUT_MENTIONS.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["title", "jp_term", "id", "file", "jp", "cn"],
        )
        writer.writeheader()
        for (title, term), term_rows in sorted(mentions.items()):
            for row in term_rows[:50]:
                writer.writerow(
                    {
                        "title": title,
                        "jp_term": term,
                        "id": row["id"],
                        "file": row["file"],
                        "jp": clean(row["jp"]),
                        "cn": clean(row["cn"]),
                    }
                )

    review_rows = []
    seen_review = set()
    for item in candidates.values():
        jp_term = item["jp_term"]
        current_cn = item["current_cn"]
        if not any(hint in jp_term for hint in REVIEW_HINTS):
            continue
        if len(jp_term) > 24:
            continue
        key = (item["title"], jp_term, current_cn)
        if key in seen_review:
            continue
        seen_review.add(key)
        review_rows.append(item)

    with OUT_REVIEW.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "jp_name",
                "current_cn",
                "kind_hint",
                "count",
                "ids",
                "example_jp",
                "example_cn",
                "decision",
                "note",
            ],
        )
        writer.writeheader()
        for item in sorted(review_rows, key=lambda x: (x["title"], x["jp_term"])):
            jp_term = item["jp_term"]
            kind = "unit_or_call_sign"
            if "艦" in jp_term or "ボクサー" in jp_term:
                kind = "ship"
            elif "小隊" in jp_term or "中隊" in jp_term or "大隊" in jp_term or "戦隊" in jp_term:
                kind = "unit"
            writer.writerow(
                {
                    "title": item["title"],
                    "jp_name": jp_term,
                    "current_cn": item["current_cn"],
                    "kind_hint": kind,
                    "count": len(set(item["ids"])),
                    "ids": compact_examples(list(dict.fromkeys(item["ids"]))),
                    "example_jp": compact_examples(list(dict.fromkeys(item["examples_jp"])), 2),
                    "example_cn": compact_examples(list(dict.fromkeys(item["examples_cn"])), 2),
                    "decision": "",
                    "note": "",
                }
            )

    named_rows = []
    seen_named = set()
    for item in review_rows:
        jp_term = item["jp_term"]
        if jp_term in GENERIC_REVIEW_TERMS:
            continue
        if any(role in jp_term for role in ("長", "リーダー", "メンバー", "先生")) and not any(base in jp_term for base in CALLSIGN_BASES):
            if "艦長" not in jp_term:
                continue
        named = any(base in jp_term for base in CALLSIGN_BASES)
        named = named or any(hint in jp_term for hint in PROPER_HINTS)
        named = named or ("第" in jp_term and any(suffix in jp_term for suffix in ("小隊", "中隊", "大隊", "戦隊")))
        named = named or ("艦" in jp_term and len(jp_term) > 1)
        if not named:
            continue
        key = (item["title"], jp_term, item["current_cn"])
        if key in seen_named:
            continue
        seen_named.add(key)
        named_rows.append(item)

    with OUT_NAMED_REVIEW.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "jp_name",
                "current_cn",
                "kind_hint",
                "count",
                "ids",
                "example_jp",
                "example_cn",
                "decision",
                "note",
            ],
        )
        writer.writeheader()
        for item in sorted(named_rows, key=lambda x: (x["title"], x["jp_term"])):
            jp_term = item["jp_term"]
            kind = "unit_or_call_sign"
            if "艦" in jp_term or "ボクサー" in jp_term or "大和" in jp_term:
                kind = "ship"
            elif "軍" in jp_term or "海兵隊" in jp_term:
                kind = "force"
            elif "小隊" in jp_term or "中隊" in jp_term or "大隊" in jp_term or "戦隊" in jp_term:
                kind = "unit"
            writer.writerow(
                {
                    "title": item["title"],
                    "jp_name": jp_term,
                    "current_cn": item["current_cn"],
                    "kind_hint": kind,
                    "count": len(set(item["ids"])),
                    "ids": compact_examples(list(dict.fromkeys(item["ids"]))),
                    "example_jp": compact_examples(list(dict.fromkeys(item["examples_jp"])), 2),
                    "example_cn": compact_examples(list(dict.fromkeys(item["examples_cn"])), 2),
                    "decision": "",
                    "note": "",
                }
            )

    print(f"candidates={OUT_CSV}")
    print(f"mentions={OUT_MENTIONS}")
    print(f"review={OUT_REVIEW}")
    print(f"named_review={OUT_NAMED_REVIEW}")
    print(f"candidate_count={len(candidates)}")
    print(f"review_count={len(review_rows)}")
    print(f"named_review_count={len(named_rows)}")


if __name__ == "__main__":
    main()
