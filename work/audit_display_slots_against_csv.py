from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
TITLES = ("tda01", "tda02", "tda03")
ID_RE = re.compile(r"(?:game_[ts]|tda03_[ts]|tda02_staff)\d+(?:_ruby)?")
CONTROL_RE = re.compile(r"\\[A-Za-z]+")


def is_surrogate(ch: str) -> bool:
    return 0xDC80 <= ord(ch) <= 0xDCFF


def is_boundary(ch: str) -> bool:
    return ch == "\x00" or is_surrogate(ch) or (ord(ch) < 32 and ch not in "\t\r\n")


def visible_runs(segment: str) -> list[tuple[int, int, str]]:
    runs: list[tuple[int, int, str]] = []
    start: int | None = None
    for index, ch in enumerate(segment):
        if is_boundary(ch):
            if start is not None:
                runs.append((start, index, segment[start:index]))
                start = None
        elif start is None:
            start = index
    if start is not None:
        runs.append((start, len(segment), segment[start:]))
    return runs


def pick_display_span(segment: str) -> tuple[int, int, str] | None:
    candidates = []
    for start, end, value in visible_runs(segment):
        cleaned = value.strip()
        if not cleaned:
            continue
        if ID_RE.fullmatch(cleaned):
            continue
        candidates.append((start, end, cleaned))
    return candidates[-1] if candidates else None


def normalize_replacement(text: str, source: str) -> str:
    zh = CONTROL_RE.sub("", text or "")
    zh = zh.replace("\\n", " ")
    zh = re.sub(r"\s+", " ", zh).strip()
    source_has_quotes = source.strip().startswith("「") and source.strip().endswith("」")
    zh_has_quotes = zh.startswith("「") and zh.endswith("」")
    if source_has_quotes and not zh_has_quotes:
        zh = f"「{zh.strip('「」')}」"
    if not source_has_quotes and zh_has_quotes:
        zh = zh.strip("「」")
    return zh


def simple(text: str) -> str:
    text = CONTROL_RE.sub("", text or "")
    text = text.replace("\\n", "").replace(" ", "").replace("\u3000", "")
    return text.strip()


def cache_root(title: str) -> Path:
    return (
        Path(os.environ["LOCALAPPDATA"])
        / "ancr"
        / title
        / "data"
        / "root"
        / "assets"
        / "data_spec"
        / "adv"
        / "game"
        / "scr"
        / "localized"
    )


def repack_root(title: str, stamp: str) -> Path:
    return ROOT / "outputs" / f"repack_{title}_{stamp}"


def load_rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows[(Path(row.get("file", "")).name, row.get("id", ""))] = row
    return rows


def row_zh(row: dict[str, str]) -> str:
    return row.get("zh_deepseek") or row.get("cn") or row.get("zh") or ""


def audit_title(title: str, root: Path) -> tuple[dict[str, int], list[list[str]]]:
    rows = load_rows(ROOT / "outputs" / "tda_text" / f"{title}_deepseek_full.csv")
    summary = {
        "checked": 0,
        "missing": 0,
        "mismatch": 0,
        "text_id_not_found": 0,
    }
    issues: list[list[str]] = []
    texts: dict[str, str] = {}
    for path in root.rglob("*.egpack"):
        text = path.read_bytes().decode("utf-8", "surrogateescape")
        texts[path.name] = text
        summary["text_id_not_found"] += text.count("Text ID Not Found")

    for (file_name, text_id), row in rows.items():
        if text_id.endswith("_ruby") or file_name.startswith("__staffroll__"):
            continue
        if not row.get("jp", "").strip() or not row_zh(row).strip():
            continue
        expected = normalize_replacement(row_zh(row), row.get("jp", ""))
        text = texts.get(file_name)
        summary["checked"] += 1
        if text is None:
            summary["missing"] += 1
            issues.append([title, "missing_file", file_name, text_id, row.get("jp", ""), row_zh(row), "", expected])
            continue
        if expected not in text:
            summary["mismatch"] += 1
            issues.append([title, "expected_text_not_found", file_name, text_id, row.get("jp", ""), row_zh(row), "", expected])
    return summary, issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("cache", "repack"), default="cache")
    parser.add_argument("--stamp", default="xmlsafe_20260617f")
    parser.add_argument("--titles", nargs="+", choices=TITLES, default=list(TITLES))
    parser.add_argument(
        "--report",
        default=str(ROOT / "outputs" / "qa" / "alignment_review" / "display_slot_audit_latest.csv"),
    )
    args = parser.parse_args()

    summaries: dict[str, dict[str, int]] = {}
    all_issues: list[list[str]] = []
    for title in args.titles:
        root = cache_root(title) if args.mode == "cache" else repack_root(title, args.stamp)
        summary, issues = audit_title(title, root)
        summaries[title] = summary
        all_issues.extend(issues)

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "kind", "file", "id", "jp", "csv_cn", "actual", "expected"])
        writer.writerows(all_issues)

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    print(f"issues={len(all_issues)} report={report}")
    return 1 if all_issues or any(s["text_id_not_found"] for s in summaries.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
