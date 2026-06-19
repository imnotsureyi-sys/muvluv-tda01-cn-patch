from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "qa" / "alignment_review"

TITLES = {
    "tda01": {
        "src": ROOT / "outputs" / "tda_fpd_extract" / "tda01" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "csv": ROOT / "outputs" / "tda_text" / "tda01_deepseek_full.csv",
        "id_re": re.compile(r"(game_[ts]\d+)"),
    },
    "tda02": {
        "src": ROOT / "outputs" / "tda_fpd_extract" / "tda02" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "csv": ROOT / "outputs" / "tda_text" / "tda02_deepseek_full.csv",
        "id_re": re.compile(r"(game_[ts]\d+)"),
    },
    "tda03": {
        "src": ROOT / "outputs" / "tda_fpd_extract" / "tda03" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "csv": ROOT / "outputs" / "tda_text" / "tda03_deepseek_full.csv",
        "id_re": re.compile(r"(tda03_[ts]\d+)"),
    },
}


def is_surrogate(ch: str) -> bool:
    return 0xDC80 <= ord(ch) <= 0xDCFF


def is_boundary(ch: str) -> bool:
    return ch == "\x00" or is_surrogate(ch) or (ord(ch) < 32 and ch not in "\t\r\n")


def visible_runs(segment: str) -> list[str]:
    runs: list[str] = []
    start: int | None = None
    for i, ch in enumerate(segment):
        if is_boundary(ch):
            if start is not None:
                runs.append(segment[start:i])
                start = None
        elif start is None:
            start = i
    if start is not None:
        runs.append(segment[start:])
    return runs


def clean_text(text: str) -> str:
    return (text or "").replace("\\p", "").replace("\\f", "").strip()


def looks_japanese(text: str) -> bool:
    return any("\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff" for ch in text or "")


def normalize(text: str) -> str:
    return (
        (text or "")
        .replace("\\w", "")
        .replace("\\p", "")
        .replace("\\f", "")
        .replace(" ", "")
        .replace("　", "")
        .strip()
    )


def extract_file(path: Path, id_re: re.Pattern[str]) -> list[dict[str, str]]:
    raw = path.read_bytes().decode("utf-8", "surrogateescape")
    matches = list(id_re.finditer(raw))
    records: list[dict[str, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        seg = raw[m.start():end]
        runs = visible_runs(seg)
        en_current = clean_text(runs[4]) if len(runs) > 4 else ""
        jp_for_next = clean_text(runs[13]) if len(runs) > 13 and looks_japanese(runs[13]) else ""
        records.append(
            {
                "file": str(path),
                "file_name": path.name,
                "id": m.group(1),
                "en_current": en_current,
                "jp_for_next": jp_for_next,
            }
        )
    for i, rec in enumerate(records):
        rec["jp_shifted_from_prev"] = records[i - 1]["jp_for_next"] if i > 0 else ""
        rec["prev_id"] = records[i - 1]["id"] if i > 0 else ""
    return records


def audit_title(title: str, cfg: dict[str, object]) -> dict[str, int]:
    src = cfg["src"]  # type: ignore[assignment]
    csv_path = cfg["csv"]  # type: ignore[assignment]
    id_re = cfg["id_re"]  # type: ignore[assignment]

    extracted: list[dict[str, str]] = []
    for path in sorted(Path(src).glob("*.egpack")):
        extracted.extend(extract_file(path, id_re))  # type: ignore[arg-type]
    by_id = {row["id"]: row for row in extracted}

    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as f:
        current = list(csv.DictReader(f))

    diffs: list[dict[str, str]] = []
    empty_jp_with_reextracted: list[dict[str, str]] = []
    exact_mismatch: list[dict[str, str]] = []

    for row in current:
        rid = row.get("id", "")
        if rid not in by_id or rid.endswith("_ruby") or "_staff" in rid:
            continue
        csv_jp = row.get("jp", "")
        rex = by_id[rid].get("jp_shifted_from_prev", "")
        if normalize(csv_jp) != normalize(rex):
            rec = {
                "file": row.get("file", ""),
                "id": rid,
                "prev_id": by_id[rid].get("prev_id", ""),
                "csv_jp": csv_jp,
                "reextracted_jp": rex,
                "cn": row.get("zh_deepseek", "") or row.get("cn", ""),
                "en_current": by_id[rid].get("en_current", ""),
            }
            diffs.append(rec)
            if not csv_jp and rex:
                empty_jp_with_reextracted.append(rec)
            elif csv_jp and rex:
                exact_mismatch.append(rec)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix, rows in [
        ("all_diffs", diffs),
        ("empty_jp_with_reextracted", empty_jp_with_reextracted),
        ("exact_mismatch", exact_mismatch),
    ]:
        out = OUT_DIR / f"{title}_reextracted_jp_{suffix}_20260617.csv"
        fields = ["file", "id", "prev_id", "csv_jp", "reextracted_jp", "cn", "en_current"]
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    return {
        "records": len(extracted),
        "diffs": len(diffs),
        "empty_jp_with_reextracted": len(empty_jp_with_reextracted),
        "exact_mismatch": len(exact_mismatch),
    }


def main() -> None:
    summary = {}
    for title, cfg in TITLES.items():
        summary[title] = audit_title(title, cfg)
    for title, data in summary.items():
        print(title, data)


if __name__ == "__main__":
    main()
