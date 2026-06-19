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
OUT = OUT_DIR / "muvluv_tda01-03_exhaustive_unit_ship_callsign_audit.csv"
OUT_SUMMARY = OUT_DIR / "muvluv_tda01-03_exhaustive_unit_ship_callsign_summary.csv"
OUT_HIGH = OUT_DIR / "muvluv_tda01-03_high_priority_named_unit_ship_callsign_review.csv"

CONTROL_RE = re.compile(r"\\[A-Za-z0-9_]+")
KATAKANA_RE = re.compile(r"[ァ-ヴー・Ａ-ＺA-Z][ァ-ヴー・Ａ-ＺA-Z０-９0-9・＆&ー]*")
JP_WORD_RE = re.compile(r"[一-龯々ァ-ヴーＡ-ＺA-Z０-９0-9・＆&ー]+")

UNIT_WORDS = (
    "小隊",
    "中隊",
    "大隊",
    "戦隊",
    "隊",
    "部隊",
    "軍",
    "海兵隊",
    "衛士",
    "各機",
    "全機",
    "長機",
    "リード",
    "フライト",
    "オール",
    "ＯＰ",
    "OP",
    "オペレーター",
    "指揮所",
    "HQ",
    "ＨＱ",
    "CP",
    "ＣＰ",
)

SHIP_WORDS = (
    "艦",
    "艦隊",
    "艦艇",
    "艦船",
    "母艦",
    "揚陸艦",
    "駆逐艦",
    "戦艦",
    "巡洋艦",
    "潜水艦",
    "大和",
    "ボクサー",
    "マザーグース",
    "JFK",
    "ＪＦＫ",
)

CALL_CONTEXT = (
    "より",
    "から",
    "へ",
    "全機",
    "各機",
    "了解",
    "呼叫",
    "通達",
    "通信",
    "発進",
    "出撃",
    "隊",
    "中隊",
    "小隊",
)

KNOWN_CALLSIGN_FRAGMENTS = (
    "ウォードッグ",
    "ウォードック",
    "ワードッグ",
    "イーグル",
    "カロネード",
    "フェザント",
    "ナイトオウル",
    "ブラックナイヴス",
    "ナイヴス",
    "ブラックバード",
    "ホーンド",
    "ホーネット",
    "ハンター",
    "ハンターズ",
    "クレイン",
    "クレインズ",
    "サラマンダー",
    "サラマンダーズ",
    "ラトルスネーク",
    "マザーグース",
    "ボクサー",
    "フォックス",
    "ファントム",
    "ラプター",
    "デモ隊",
)

GENERIC_ONLY = {
    "小隊",
    "中隊",
    "大隊",
    "隊",
    "軍",
    "部隊",
    "衛士",
    "兵",
    "艦",
    "艦隊",
    "艦艇",
    "艦船",
    "母艦",
    "長機",
    "各機",
    "全機",
    "指揮所",
    "基地",
    "オペレーター",
}


def clean(text: str) -> str:
    text = text or ""
    text = CONTROL_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def is_speaker_id(text_id: str) -> bool:
    return "_s" in text_id or text_id.endswith("_staff00000")


def normalize_term(term: str) -> str:
    term = term.strip("「」『』（）()[]【】、。！？!?…—―　 ")
    term = re.sub(r"[0-9０-９]+$", "", term)
    return term


def kind_for(term: str) -> str:
    if any(w in term for w in SHIP_WORDS):
        return "ship"
    if any(w in term for w in ("小隊", "中隊", "大隊", "戦隊", "隊", "部隊")):
        return "unit"
    if any(w in term for w in ("軍", "海兵隊", "衛士")):
        return "force"
    return "callsign_or_name"


def priority_for(term: str, reason: str) -> str:
    if term in GENERIC_ONLY:
        return "low_generic"
    if any(x in term for x in KNOWN_CALLSIGN_FRAGMENTS):
        return "high_named"
    if any(x in term for x in SHIP_WORDS):
        return "high_ship"
    if "speaker" in reason:
        return "medium_speaker"
    if any(x in term for x in UNIT_WORDS):
        return "medium_unit"
    return "low_context"


def add_candidate(cands, row, term: str, reason: str):
    term = normalize_term(term)
    if len(term) < 2 or len(term) > 40:
        return
    if term in {"ＨＱ", "HQ", "ＣＰ", "CP", "ＯＫ", "OK"}:
        return
    key = (row["title"], term)
    item = cands[key]
    item["title"] = row["title"]
    item["jp_name"] = term
    item["kind_hint"] = kind_for(term)
    item["priority"] = priority_for(term, reason)
    item["reasons"].add(reason)
    item["ids"].append(row["id"])
    item["files"].append(row["file"])
    item["examples_jp"].append(row["jp_clean"])
    item["examples_cn"].append(row["cn_clean"])
    if is_speaker_id(row["id"]) and row["cn_clean"]:
        item["speaker_cn"].add(row["cn_clean"])


def phrase_around(text: str, start: int, end: int) -> str:
    left = max(0, start - 18)
    right = min(len(text), end + 18)
    frag = text[left:right]
    parts = JP_WORD_RE.findall(frag)
    if not parts:
        return text[start:end]
    best = ""
    target = text[start:end]
    for part in parts:
        if target in part and len(part) > len(best):
            best = part
    return best or target


def extract_candidates(row, cands):
    jp = row["jp_clean"]
    cn = row["cn_clean"]
    if not jp:
        return

    if is_speaker_id(row["id"]):
        if any(w in jp for w in UNIT_WORDS + SHIP_WORDS + KNOWN_CALLSIGN_FRAGMENTS) or KATAKANA_RE.search(jp):
            add_candidate(cands, row, jp, "speaker")

    for known in KNOWN_CALLSIGN_FRAGMENTS:
        start = 0
        while True:
            idx = jp.find(known, start)
            if idx < 0:
                break
            add_candidate(cands, row, known, "known_callsign_fragment")
            add_candidate(cands, row, phrase_around(jp, idx, idx + len(known)), "known_callsign_phrase")
            start = idx + len(known)

    for word in UNIT_WORDS + SHIP_WORDS:
        start = 0
        while True:
            idx = jp.find(word, start)
            if idx < 0:
                break
            add_candidate(cands, row, phrase_around(jp, idx, idx + len(word)), "keyword_phrase")
            start = idx + len(word)

    for match in KATAKANA_RE.finditer(jp):
        term = match.group(0)
        window = jp[max(0, match.start() - 15) : min(len(jp), match.end() + 15)]
        if any(ctx in window for ctx in CALL_CONTEXT) or re.search(r"[１２３４５６７８９０0-9]$", term):
            add_candidate(cands, row, term, "katakana_callsign_context")

    # If Chinese already contains likely translated unit/ship names in a line
    # with JP unit markers, keep the JP phrase even when it is noisy.
    if any(x in cn for x in ("小队", "中队", "大队", "舰", "号", "队", "长机")):
        for part in JP_WORD_RE.findall(jp):
            if any(w in part for w in UNIT_WORDS + SHIP_WORDS + KNOWN_CALLSIGN_FRAGMENTS):
                add_candidate(cands, row, part, "cn_unit_context")


def main():
    cands = defaultdict(lambda: {
        "title": "",
        "jp_name": "",
        "kind_hint": "",
        "priority": "",
        "reasons": set(),
        "ids": [],
        "files": [],
        "examples_jp": [],
        "examples_cn": [],
        "speaker_cn": set(),
    })

    for title, path in CSV_PATHS.items():
        with path.open(encoding="utf-8-sig", newline="") as f:
            for raw in csv.DictReader(f):
                row = {
                    "title": title,
                    "file": Path(raw.get("file", "")).name,
                    "id": raw.get("id", ""),
                    "jp_clean": clean(raw.get("jp", "")),
                    "cn_clean": clean(raw.get("zh_deepseek", "")),
                }
                extract_candidates(row, cands)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in cands.values():
        ids = list(dict.fromkeys(item["ids"]))
        files = list(dict.fromkeys(item["files"]))
        examples_jp = list(dict.fromkeys(item["examples_jp"]))
        examples_cn = list(dict.fromkeys(item["examples_cn"]))
        speaker_cn = list(dict.fromkeys(item["speaker_cn"]))
        rows.append({
            "title": item["title"],
            "jp_name": item["jp_name"],
            "current_speaker_cn": " / ".join(speaker_cn),
            "kind_hint": item["kind_hint"],
            "priority": item["priority"],
            "count": len(ids),
            "reasons": " / ".join(sorted(item["reasons"])),
            "ids": " | ".join(ids[:8]),
            "files": " | ".join(files[:4]),
            "example_jp": " | ".join(examples_jp[:3]),
            "example_cn": " | ".join(examples_cn[:3]),
            "decision": "",
            "note": "",
        })

    priority_order = {"high_named": 0, "high_ship": 1, "medium_speaker": 2, "medium_unit": 3, "low_context": 4, "low_generic": 5}
    rows.sort(key=lambda r: (r["title"], priority_order.get(r["priority"], 9), r["kind_hint"], r["jp_name"]))

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    with OUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "priority", "kind_hint", "count"])
        writer.writeheader()
        summary = defaultdict(int)
        for r in rows:
            summary[(r["title"], r["priority"], r["kind_hint"])] += 1
        for (title, priority, kind), count in sorted(summary.items()):
            writer.writerow({"title": title, "priority": priority, "kind_hint": kind, "count": count})

    high_rows = [r for r in rows if r["priority"] in {"high_named", "high_ship"}]
    with OUT_HIGH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(high_rows)

    print(f"out={OUT}")
    print(f"summary={OUT_SUMMARY}")
    print(f"high={OUT_HIGH}")
    print(f"rows={len(rows)}")
    print(f"high_rows={len(high_rows)}")


if __name__ == "__main__":
    main()
