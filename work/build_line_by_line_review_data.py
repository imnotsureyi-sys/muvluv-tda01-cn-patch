from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "outputs" / "tda_text"
QA_DIR = ROOT / "outputs" / "qa" / "line_by_line_jp_cn_review"
STRICT_DIR = ROOT / "outputs" / "qa" / "strict_jp_cn_audit"
OUT_JSON = QA_DIR / "review_rows.json"
OUT_SUMMARY = QA_DIR / "summary.json"
DECISIONS_CSV = QA_DIR / "review_decisions.csv"


CONTROL_RE = re.compile(r"\\[A-Za-z][A-Za-z0-9_]*(?:\[[^\]]*\])?")
JP_KANA_RE = re.compile(r"[\u3040-\u30ff]")
MOJIBAKE_RE = re.compile(r"[�\ufffd鈻]")
ASCII_WORD_RE = re.compile(r"[A-Za-z]{4,}")

BAD_TEXT_PATTERNS = [
    "Text ID Not Found",
    "沃德狗",
    "战狗",
    "地表飞行员",
    "表面飞行员",
    "飞行员徽章",
    "希望亡命",
    "巴别塔作战",
    "大尉",
    "龍浪",
    "龍浪中尉",
]

KANJI_OR_TRADITIONAL_CANDIDATES = [
    "大隊長",
    "正規",
    "情報",
    "神宮司",
    "軍人優遇反対",
    "可憐",
    "関係",
    "駒木",
    "斑鳩",
    "這種",
]


def clean_visible(text: str) -> str:
    text = text or ""
    text = CONTROL_RE.sub("", text)
    text = text.replace("\\n", "").replace("\\r", "").replace("\\t", "")
    return text.strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_strict_findings() -> dict[tuple[str, str, str], list[str]]:
    findings: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    path = STRICT_DIR / "all_findings.csv"
    if not path.exists():
        return findings
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (row.get("title", ""), row.get("file", ""), row.get("text_id", ""))
            kind = row.get("kind", "")
            note = row.get("note", "")
            if note:
                findings[key].append(f"{kind}: {note}")
            elif kind:
                findings[key].append(kind)
    return findings


def load_decisions() -> dict[tuple[str, str], dict[str, str]]:
    decisions: dict[tuple[str, str], dict[str, str]] = {}
    if not DECISIONS_CSV.exists():
        return decisions
    with DECISIONS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            title = (row.get("title") or "").lower()
            text_id = row.get("id") or ""
            if title and text_id:
                decisions[(title, text_id)] = row
    return decisions


def has_long_english_residue(jp: str, cn: str) -> bool:
    visible = clean_visible(cn)
    if not visible:
        return False
    words = ASCII_WORD_RE.findall(visible)
    if not words:
        return False
    ascii_chars = sum(1 for ch in visible if ch.isascii() and ch.isalpha())
    # Keep call signs and product-like strings such as OSP-1400/Eagle from being flagged.
    return ascii_chars >= 24 and ascii_chars / max(len(visible), 1) > 0.45 and bool(JP_KANA_RE.search(jp))


def hard_review(jp: str, cn: str) -> tuple[str, str, str]:
    jp_visible = clean_visible(jp)
    cn_visible = clean_visible(cn)
    reasons: list[str] = []
    fixes: list[str] = []

    if not jp_visible and cn_visible:
        reasons.append("jp 字段为空，但 cn 字段不为空。按规则必须清空。")
        fixes.append("清空 cn 字段。")
    if jp_visible and not cn_visible:
        reasons.append("jp 字段有内容，但 cn 字段为空。")
        fixes.append("按该 jp 字段补译中文。")
    if "Text ID Not Found" in cn:
        reasons.append("cn 中出现 Text ID Not Found。")
        fixes.append("按对应 jp 字段重写该中文，或在 jp 为空时清空。")
    if JP_KANA_RE.search(cn_visible):
        reasons.append("cn 中残留日文假名。")
        fixes.append("把残留日文按 jp 原文翻成中文。")
    if MOJIBAKE_RE.search(cn_visible):
        reasons.append("cn 中疑似存在乱码/替换符。")
        fixes.append("回到 jp 原文重新翻译该行。")
    if has_long_english_residue(jp, cn):
        reasons.append("cn 中疑似残留英文长句。")
        fixes.append("不用英文，按 jp 原文重译该行。")

    for pat in BAD_TEXT_PATTERNS:
        if pat in cn_visible:
            reasons.append(f"cn 中残留已禁止或旧译词：{pat}。")
            fixes.append("按术语表替换为当前固定译名。")
    for pat in KANJI_OR_TRADITIONAL_CANDIDATES:
        if pat in cn_visible:
            reasons.append(f"cn 中疑似残留日文汉字/繁体：{pat}。")
            fixes.append("改为简体中文固定写法。")

    if reasons:
        return "否", "；".join(dict.fromkeys(fixes)), "；".join(dict.fromkeys(reasons))
    return "待核对", "", ""


def main() -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    strict_findings = load_strict_findings()
    decisions = load_decisions()
    rows: list[dict[str, str | int]] = []
    summary: dict[str, dict[str, int]] = {}

    for title in ("tda01", "tda02", "tda03"):
        csv_path = CSV_DIR / f"{title}_deepseek_full.csv"
        source_rows = read_csv(csv_path)
        counts = defaultdict(int)
        for index, row in enumerate(source_rows, start=1):
            file_name = Path(row.get("file", "")).name
            text_id = row.get("id", "")
            jp = row.get("jp", "")
            cn = row.get("zh_deepseek", "")
            correct, planned, reason = hard_review(jp, cn)
            decision = decisions.get((title, text_id))
            if decision:
                correct = decision.get("correct") or correct
                planned = decision.get("planned_change") or planned
                reason = decision.get("reason") or reason
            flags = strict_findings.get((title, file_name, text_id), [])
            counts["rows"] += 1
            counts[correct] += 1
            if flags:
                counts["strict_flags"] += 1
            rows.append(
                {
                    "title": title.upper(),
                    "seq": index,
                    "id": text_id,
                    "jp": jp,
                    "cn": cn,
                    "是否正确": correct,
                    "如果否，打算怎么修改": planned,
                    "理由": reason,
                    "脚本文件": file_name,
                    "审计提示": " | ".join(flags),
                }
            )
        summary[title] = dict(counts)

    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT_JSON)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
