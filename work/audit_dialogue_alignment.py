from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = ROOT / "outputs" / "tda_text"
GLOSSARY = ROOT / "outputs" / "glossary" / "muvluv_lunatranslator_full_glossary.csv"
OUT_DIR = ROOT / "outputs" / "qa" / "alignment_review"
DETAIL_OUT = OUT_DIR / "dialogue_alignment_audit_details.csv"
HIGH_OUT = OUT_DIR / "dialogue_alignment_audit_high_risk.csv"
SUMMARY_OUT = OUT_DIR / "dialogue_alignment_audit_summary.txt"

CSV_PATHS = {
    "tda01": TEXT_DIR / "tda01_deepseek_full.csv",
    "tda02": TEXT_DIR / "tda02_deepseek_full.csv",
    "tda03": TEXT_DIR / "tda03_deepseek_full.csv",
}

CORE_TERM_MAP = {
    "ＢＥＴＡ": "BETA",
    "BETA": "BETA",
    "ハイヴ": "HIVE",
    "ＨＩＶＥ": "HIVE",
    "HIVE": "HIVE",
    "ＪＦＫ": "JFK",
    "JFK": "JFK",
    "ウォードッグ": "战犬",
    "ウォードック": "战犬",
    "ワードッグ": "战犬",
    "イーグル": "鹰",
    "カロネード": "卡洛内德",
    "ドレイク": "德雷克",
    "フェザント": "雉鸡",
    "サラマンダー": "蝾螈",
    "ボクサー": "拳师号",
    "ブラックナイヴス": "黑刃",
    "ナイヴス": "黑刃",
    "ホーンド": "号角",
    "クレイン": "鹤",
    "ナイトオウル": "夜枭",
    "ハンター": "猎人",
    "マザーグース": "鹅妈妈",
    "ラトルスネーク": "响尾蛇",
    "大和": "大和",
    "光線級": "光线级",
    "突撃級": "突击级",
    "要撃級": "要击级",
    "要塞級": "要塞级",
    "母艦級": "母舰级",
    "重光線級": "重光线级",
    "戦術機": "战术机",
    "衛士": "卫士",
    "帝国": "帝国",
    "米軍": "美军",
    "米国": "美国",
    "国連": "联合国",
    "欧州派遣軍": "欧洲派遣军",
    "神宮司": "神宫司",
    "龍浪": "龙浪",
    "白銀": "白银",
    "鑑": "鉴",
    "悠陽": "悠阳",
    "まりも": "麻理茉",
}

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*|[0-9]+(?:\.[0-9]+)?")
JP_CONTROL_RE = re.compile(r"\\[A-Za-z0-9_]+")
CN_PUNCT_ONLY_RE = re.compile(r"^[\s　。．\.…・、，,！？!?—ー\-－「」『』（）()\[\]【】]*$")


def norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def visible(text: str) -> str:
    text = JP_CONTROL_RE.sub("", text or "")
    return re.sub(r"\s+", " ", text).strip()


def has_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text or ""))


def load_glossary_terms() -> dict[str, str]:
    terms = dict(CORE_TERM_MAP)
    if GLOSSARY.exists():
        with GLOSSARY.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                src = row.get("source", "") or ""
                dst = row.get("target", "") or ""
                cat = row.get("category", "") or ""
                if not src or not dst:
                    continue
                if not has_japanese(src):
                    continue
                if len(src) < 2:
                    continue
                # Keep terms likely to be semantic anchors. Broad everyday words
                # are noisy for alignment.
                if cat not in {"呼号", "部队名", "舰名", "组织名", "机体/呼称", "BETA", "军政术语", "人物", "地名", "作战术语"}:
                    if src not in CORE_TERM_MAP:
                        continue
                terms.setdefault(src, dst)
    return terms


def extract_ascii_tokens(text: str) -> set[str]:
    text = norm(text)
    out = set()
    for token in TOKEN_RE.findall(text):
        t = token.upper()
        if len(t) == 1 and not t.isdigit():
            continue
        if t in {"W", "P", "N", "A", "I"}:
            continue
        out.add(t)
    return out


def expected_targets(jp: str, terms: dict[str, str]) -> list[tuple[str, str]]:
    jp_norm = norm(jp)
    hits = []
    for src, dst in terms.items():
        if src in jp or norm(src) in jp_norm:
            hits.append((src, dst))
    # Longer anchors first so reports are easier to read.
    hits.sort(key=lambda x: len(x[0]), reverse=True)
    return hits


def score_cn(cn: str, expected: list[tuple[str, str]]) -> int:
    if not expected:
        return 0
    cn_norm = norm(cn)
    score = 0
    seen_targets = set()
    for _src, dst in expected:
        if not dst or dst in seen_targets:
            continue
        seen_targets.add(dst)
        if dst in cn or norm(dst) in cn_norm:
            score += 1
    return score


def row_kind(jp: str, cn: str) -> str:
    jp_v = visible(jp)
    cn_v = visible(cn)
    if not jp_v and not cn_v:
        return "both_empty"
    if not jp_v:
        return "jp_empty"
    if not cn_v:
        return "cn_empty"
    if CN_PUNCT_ONLY_RE.match(jp_v) or CN_PUNCT_ONLY_RE.match(cn_v):
        return "punctuation"
    return "normal"


def add_issue(issues, title, idx, row, severity, issue_type, detail):
    issues.append(
        {
            "severity": severity,
            "issue_type": issue_type,
            "title": title,
            "seq": idx + 1,
            "id": row["id"],
            "file": Path(row.get("file", "")).name,
            "jp": visible(row.get("jp", "")),
            "cn": visible(row.get("zh_deepseek", "")),
            "detail": detail,
        }
    )


def audit_title(title: str, rows: list[dict[str, str]], terms: dict[str, str]) -> list[dict[str, str]]:
    issues = []
    expected_by_row = [expected_targets(row.get("jp", ""), terms) for row in rows]

    for i, row in enumerate(rows):
        jp = row.get("jp", "") or ""
        cn = row.get("zh_deepseek", "") or ""
        jp_v = visible(jp)
        cn_v = visible(cn)
        kind = row_kind(jp, cn)

        if kind == "jp_empty" and cn_v:
            add_issue(issues, title, i, row, "high", "jp_empty_cn_not_empty", "")
        elif kind == "cn_empty" and jp_v:
            add_issue(issues, title, i, row, "high", "jp_not_empty_cn_empty", "")

        jp_dialogue = jp_v.startswith("「")
        cn_dialogue = cn_v.startswith("「")
        if kind == "normal" and jp_dialogue != cn_dialogue:
            # Narration can occasionally be quoted differently, so medium.
            add_issue(issues, title, i, row, "medium", "quote_shape_mismatch", f"jp_dialogue={jp_dialogue} cn_dialogue={cn_dialogue}")

        jp_ascii = extract_ascii_tokens(jp_v)
        cn_ascii = extract_ascii_tokens(cn_v)
        missing_ascii = sorted(t for t in jp_ascii - cn_ascii if t not in {"W"})
        extra_ascii = sorted(t for t in cn_ascii - jp_ascii if t not in {"W"})
        if missing_ascii and len(jp_v) > 4:
            add_issue(issues, title, i, row, "medium", "jp_ascii_missing_in_cn", " ".join(missing_ascii[:8]))
        if extra_ascii and len(cn_v) > 8:
            # Extra ASCII can indicate shifted English/ID leakage.
            add_issue(issues, title, i, row, "low", "cn_extra_ascii_not_in_jp", " ".join(extra_ascii[:8]))

        expected = expected_by_row[i]
        if expected:
            cur_score = score_cn(cn, expected)
            if cur_score == 0 and len(expected) >= 2:
                add_issue(
                    issues,
                    title,
                    i,
                    row,
                    "medium",
                    "multiple_anchor_terms_missing",
                    " / ".join(f"{src}->{dst}" for src, dst in expected[:8]),
                )

            prev_score = score_cn(cn, expected_by_row[i - 1]) if i > 0 else 0
            next_score = score_cn(cn, expected_by_row[i + 1]) if i + 1 < len(rows) else 0
            if max(prev_score, next_score) >= 2 and max(prev_score, next_score) > cur_score:
                where = "prev" if prev_score >= next_score else "next"
                add_issue(
                    issues,
                    title,
                    i,
                    row,
                    "high",
                    "neighbor_anchor_score_higher",
                    f"current={cur_score} prev={prev_score} next={next_score} closer_to={where}",
                )

        if i > 0:
            prev = rows[i - 1]
            prev_cn = visible(prev.get("zh_deepseek", ""))
            prev_jp = visible(prev.get("jp", ""))
            if cn_v and cn_v == prev_cn and jp_v != prev_jp and len(cn_v) >= 8:
                add_issue(issues, title, i, row, "high", "adjacent_duplicate_cn", f"same_as_prev_id={prev.get('id','')}")

        # Very large length swings can be a shift symptom; keep it low unless extreme.
        jp_len = len(jp_v)
        cn_len = len(cn_v)
        if jp_len >= 30 and cn_len <= 6:
            add_issue(issues, title, i, row, "medium", "cn_too_short_for_long_jp", f"jp_len={jp_len} cn_len={cn_len}")
        if cn_len >= 80 and jp_len <= 8:
            add_issue(issues, title, i, row, "medium", "cn_too_long_for_short_jp", f"jp_len={jp_len} cn_len={cn_len}")

    return issues


def main() -> None:
    terms = load_glossary_terms()
    all_issues = []
    counts = Counter()
    for title, path in CSV_PATHS.items():
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        issues = audit_title(title, rows, terms)
        all_issues.extend(issues)
        counts[(title, "rows")] = len(rows)
        for issue in issues:
            counts[(title, issue["severity"])] += 1
            counts[("type", issue["issue_type"])] += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["severity", "issue_type", "title", "seq", "id", "file", "jp", "cn", "detail"]
    with DETAIL_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_issues)

    high = [x for x in all_issues if x["severity"] == "high"]
    with HIGH_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(high)

    lines = [
        f"terms_loaded={len(terms)}",
        f"issues_total={len(all_issues)}",
        f"high={len(high)}",
        "",
        "by_title:",
    ]
    for title in CSV_PATHS:
        lines.append(
            f"{title}: rows={counts[(title, 'rows')]} high={counts[(title, 'high')]} medium={counts[(title, 'medium')]} low={counts[(title, 'low')]}"
        )
    lines.append("")
    lines.append("by_issue_type:")
    for (scope, key), value in sorted(counts.items(), key=lambda x: (str(x[0][0]), str(x[0][1]))):
        if scope == "type":
            lines.append(f"{key}: {value}")
    SUMMARY_OUT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"details={DETAIL_OUT}")
    print(f"high={HIGH_OUT}")


if __name__ == "__main__":
    main()
