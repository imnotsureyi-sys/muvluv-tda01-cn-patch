from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from opencc import OpenCC


ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "outputs" / "qa"
PROJECT_GLOSSARY = ROOT / "outputs" / "glossary" / "muvluv_lunatranslator_full_glossary.csv"
PROJECT_PROPER_NOUNS = ROOT / "outputs" / "glossary" / "muvluv_lunatranslator_proper_nouns.tsv"
GLOSSARY = PROJECT_GLOSSARY if PROJECT_GLOSSARY.exists() else ROOT / "workspace_full_copy_20260615" / "outputs" / "muvluv_lunatranslator_full_glossary.csv"
PROPER_NOUNS = PROJECT_PROPER_NOUNS if PROJECT_PROPER_NOUNS.exists() else ROOT / "workspace_full_copy_20260615" / "outputs" / "muvluv_lunatranslator_proper_nouns.tsv"

TITLE_CSVS = {
    "tda01": ROOT / "outputs" / "tda_text" / "tda01_deepseek_full.csv",
    "tda02": ROOT / "outputs" / "tda_text" / "tda02_deepseek_full.csv",
    "tda03": ROOT / "outputs" / "tda_text" / "tda03_deepseek_full.csv",
}

CURRENT_DISPLAY = {
    "tda01": QA / "tda01_display_current_v0.9.csv",
    "tda02": QA / "tda02_display_current_v0.9.csv",
    "tda03": QA / "tda03_display_current_v0.9.csv",
}

CURRENT_PACKS = {
    "tda01": ROOT / "outputs" / "repack_tda01_xmlsafe_20260615",
    "tda02": ROOT / "outputs" / "repack_tda02_xmlsafe_20260615",
    "tda03": ROOT / "outputs" / "repack_tda03_xmlsafe_20260615",
}

SOURCE_PACKS = {
    "tda01": ROOT / "outputs" / "tda_fpd_extract" / "tda01" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
    "tda02": ROOT / "outputs" / "tda_fpd_extract" / "tda02" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
    "tda03": ROOT / "outputs" / "tda_fpd_extract" / "tda03" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
}

ID_RE = re.compile(r"(?:game_[ts]|tda03_[ts]|tda02_staff)\d+(?:_ruby)?")
XML_TEXT_RE = re.compile(r'text="\$([^"]+)"')
CONTROL_RE = re.compile(r"\\[A-Za-z]+")
KANA_RE = re.compile(r"[\u3040-\u30ff]")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
LONG_ASCII_RE = re.compile(r"[A-Za-z][A-Za-z'’.-]{2,}(?:\s+[A-Za-z][A-Za-z'’.-]{2,}){2,}")

ALLOWED_ASCII_WORDS = {
    "BETA",
    "HIVE",
    "JFK",
    "NORAD",
    "TSF",
    "OSP",
    "XM3",
    "AMWS",
    "GL",
    "CP",
    "HQ",
    "PX",
    "OS",
    "DNA",
    "Muv-Luv",
    "Total",
    "Eclipse",
}

MOJIBAKE_MARKERS = (
    "\ufffd",
    "锟",
    "鈥",
    "銆",
    "鐨",
    "涓",
    "绋",
    "閫",
    "闆",
    "娴",
    "缁",
)

TERM_OVERRIDES = {
    "ウォードッグ": "战犬",
    "ウォードッグス": "战犬",
    "Wardog": "战犬",
    "Wardogs": "战犬",
    "surface pilot": "卫士",
    "TSF pilot": "卫士",
    "pilot": "卫士",
    "衛士": "卫士",
    "斯衛": "斯卫",
    "斯衛軍": "斯卫军",
    "龍浪": "龙浪",
    "大尉": "上尉",
    "希望亡命": "寻求庇护",
}


@dataclass
class Finding:
    title: str
    kind: str
    severity: str
    file: str
    text_id: str
    source: str
    current: str
    expected: str = ""
    term: str = ""
    context_before: str = ""
    context_after: str = ""
    note: str = ""
    visible: str = "yes"


def read_csv(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean_text(text: str) -> str:
    text = CONTROL_RE.sub("", text or "")
    text = text.replace("Pg9", "")
    text = text.replace("\x00", "")
    text = text.replace("\r", "")
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def compact(text: str) -> str:
    text = clean_text(text)
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] not in "PSZ")
    for ch in "「」『』（）()[]【】、。，！？!?—…－-～~・·：:；;\"'":
        text = text.replace(ch, "")
    return text.strip()


def has_japanese_source(text: str) -> bool:
    return bool(KANA_RE.search(text or "")) or any(ch in (text or "") for ch in "ー・々")


def is_meaningful_term(source: str, target: str) -> bool:
    source = (source or "").strip()
    target = (target or "").strip()
    if not source or not target or source == target:
        return False
    if len(source) < 2:
        return False
    if source in {"The", "Day", "After", "A", "B", "C", "D", "E", "F", "I", "II"}:
        return False
    if source.isascii() and len(source) < 4:
        return False
    return True


def load_terms() -> list[dict[str, str]]:
    terms: dict[tuple[str, str], dict[str, str]] = {}

    for source, target in TERM_OVERRIDES.items():
        terms[(source, target)] = {
            "source": source,
            "target": target,
            "category": "manual_override",
            "note": "high-priority project rule",
        }

    for row in read_csv(GLOSSARY):
        source = (row.get("source") or "").strip()
        target = (row.get("target") or "").strip()
        if is_meaningful_term(source, target):
            terms[(source, target)] = {
                "source": source,
                "target": target,
                "category": row.get("category", ""),
                "note": row.get("note", ""),
            }

    for row in read_csv(PROPER_NOUNS, delimiter="\t"):
        # The TSV header is itself a sample pair from the original export.
        source = (row.get("マブラヴ") or "").strip()
        target = (row.get("Muv-Luv") or "").strip()
        if is_meaningful_term(source, target):
            terms[(source, target)] = {
                "source": source,
                "target": target,
                "category": "proper_noun",
                "note": "proper nouns TSV",
            }

    return sorted(terms.values(), key=lambda item: len(item["source"]), reverse=True)


def xml_visible_ids(title: str) -> set[tuple[str, str]] | None:
    if title != "tda01":
        return None
    visible: set[tuple[str, str]] = set()
    for xml in CURRENT_PACKS[title].glob("*.xml"):
        refs = [ref for ref in XML_TEXT_RE.findall(xml.read_text(encoding="utf-8", errors="ignore")) if ID_RE.fullmatch(ref)]
        for ref in refs:
            if not ref.endswith("_ruby"):
                visible.add((xml.with_suffix(".egpack").name, ref))
    return visible


def row_key(row: dict[str, str]) -> tuple[str, str]:
    return Path(row.get("file", "")).name, row.get("id", "")


def build_context(rows: list[dict[str, str]]) -> dict[tuple[str, str], tuple[str, str]]:
    by_file: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_file[Path(row.get("file", "")).name].append(row)
    context: dict[tuple[str, str], tuple[str, str]] = {}
    for file_name, file_rows in by_file.items():
        for i, row in enumerate(file_rows):
            prev_text = file_rows[i - 1].get("zh_deepseek", "") if i > 0 else ""
            next_text = file_rows[i + 1].get("zh_deepseek", "") if i + 1 < len(file_rows) else ""
            context[(file_name, row.get("id", ""))] = (clean_text(prev_text), clean_text(next_text))
    return context


def current_display_rows(title: str) -> dict[tuple[str, str], str]:
    rows = read_csv(CURRENT_DISPLAY[title])
    return {(row.get("file", ""), row.get("id", "")): row.get("display", "") for row in rows}


def check_terms(title: str, terms: list[dict[str, str]]) -> list[Finding]:
    rows = read_csv(TITLE_CSVS[title])
    current = current_display_rows(title)
    visible_ids = xml_visible_ids(title)
    context = build_context(rows)
    findings: list[Finding] = []

    for row in rows:
        file_name, text_id = row_key(row)
        visible = visible_ids is None or (file_name, text_id) in visible_ids
        source = row.get("jp", "") or ""
        display = current.get((file_name, text_id), row.get("zh_deepseek", "") or "")
        display_clean = clean_text(display)
        before, after = context.get((file_name, text_id), ("", ""))

        if not source.strip() or not display_clean:
            continue

        for term in terms:
            src = term["source"]
            dst = term["target"]
            if src not in source:
                continue

            source_is_jp = has_japanese_source(src) or bool(CJK_RE.search(src))
            target_is_cjk = bool(CJK_RE.search(dst))
            current_compact = compact(display_clean)
            expected_compact = compact(dst)

            if source_is_jp and src in display_clean and src != dst:
                findings.append(
                    Finding(
                        title,
                        "source_term_residual",
                        "error" if visible else "info",
                        file_name,
                        text_id,
                        clean_text(source),
                        display_clean,
                        dst,
                        src,
                        before,
                        after,
                        term.get("category", ""),
                        "yes" if visible else "no",
                    )
                )
            elif target_is_cjk and expected_compact and expected_compact not in current_compact:
                # ASCII callsigns and very short generic terms create noise; keep this as a warning.
                if len(expected_compact) >= 2 and visible:
                    findings.append(
                        Finding(
                            title,
                            "expected_term_missing",
                            "warn",
                            file_name,
                            text_id,
                            clean_text(source),
                            display_clean,
                            dst,
                            src,
                            before,
                            after,
                            term.get("category", ""),
                            "yes",
                        )
                    )
    return findings


def check_language_quality(title: str) -> list[Finding]:
    rows = read_csv(TITLE_CSVS[title])
    current = current_display_rows(title)
    visible_ids = xml_visible_ids(title)
    context = build_context(rows)
    cc = OpenCC("t2s")
    findings: list[Finding] = []

    for row in rows:
        file_name, text_id = row_key(row)
        visible = visible_ids is None or (file_name, text_id) in visible_ids
        display = clean_text(current.get((file_name, text_id), row.get("zh_deepseek", "") or ""))
        if not display:
            continue
        before, after = context.get((file_name, text_id), ("", ""))

        if visible and KANA_RE.search(display):
            findings.append(Finding(title, "kana_residual", "error", file_name, text_id, clean_text(row.get("jp", "")), display, context_before=before, context_after=after))

        simplified = cc.convert(display)
        if visible and simplified != display and CJK_RE.search(display):
            findings.append(
                Finding(
                    title,
                    "traditional_or_kanji_residual",
                    "warn",
                    file_name,
                    text_id,
                    clean_text(row.get("jp", "")),
                    display,
                    expected=simplified,
                    context_before=before,
                    context_after=after,
                )
            )

        if visible and any(marker in display for marker in MOJIBAKE_MARKERS):
            findings.append(Finding(title, "mojibake_suspect", "error", file_name, text_id, clean_text(row.get("jp", "")), display, context_before=before, context_after=after))

        if visible and re.search(r"\\[A-Za-z]", display):
            findings.append(Finding(title, "visible_control_code", "error", file_name, text_id, clean_text(row.get("jp", "")), display, context_before=before, context_after=after))

        if visible and display.count("「") != display.count("」"):
            findings.append(Finding(title, "unbalanced_quote", "warn", file_name, text_id, clean_text(row.get("jp", "")), display, context_before=before, context_after=after))

        if visible and re.search(r"(.{1,4})\1\1", compact(display)):
            findings.append(Finding(title, "repetition_suspect", "warn", file_name, text_id, clean_text(row.get("jp", "")), display, context_before=before, context_after=after))

        ascii_match = LONG_ASCII_RE.search(display)
        if visible and ascii_match:
            words = {word.strip(".,!?;:'\"()[]").upper() for word in re.findall(r"[A-Za-z][A-Za-z'’.-]*", ascii_match.group(0))}
            allowed = {word.upper() for word in ALLOWED_ASCII_WORDS}
            if not words <= allowed:
                findings.append(Finding(title, "long_english_fragment", "warn", file_name, text_id, clean_text(row.get("jp", "")), display, context_before=before, context_after=after))

    return findings


def visible_runs(segment: str) -> list[str]:
    runs: list[str] = []
    start: int | None = None
    for index, ch in enumerate(segment):
        boundary = ch == "\x00" or (ord(ch) < 32 and ch not in "\t\r\n") or (0xDC80 <= ord(ch) <= 0xDCFF)
        if boundary:
            if start is not None:
                runs.append(segment[start:index])
                start = None
        elif start is None:
            start = index
    if start is not None:
        runs.append(segment[start:])
    return runs


def display_before_id(path: Path) -> list[tuple[str, str]]:
    data = path.read_bytes()
    if not data.startswith(b"EPK\0"):
        return []
    text = data.decode("utf-8", "surrogateescape")
    matches = list(ID_RE.finditer(text))
    rows: list[tuple[str, str]] = []
    prev = 0
    for match in matches:
        text_id = match.group()
        if text_id.endswith("_ruby"):
            prev = match.end()
            continue
        segment = text[prev : match.start()]
        prev = match.end()
        runs = [clean_text(run) for run in visible_runs(segment)]
        runs = [run for run in runs if run and run != "Pg9" and not ID_RE.fullmatch(run)]
        rows.append((text_id, runs[-1] if runs else ""))
    return rows


def check_speakers(title: str, terms: list[dict[str, str]]) -> list[Finding]:
    source_path = SOURCE_PACKS[title] / "__speakers__.egpack"
    current_path = CURRENT_PACKS[title] / "__speakers__.egpack"
    if not source_path.exists() or not current_path.exists():
        return []

    source_rows = display_before_id(source_path)
    current_rows = display_before_id(current_path)
    source_by_id = dict(source_rows)
    current_by_id = dict(current_rows)
    cc = OpenCC("t2s")
    findings: list[Finding] = []

    if [item[0] for item in source_rows] != [item[0] for item in current_rows]:
        findings.append(Finding(title, "speaker_id_order_mismatch", "error", "__speakers__.egpack", "", "", "", note="speaker ID order differs from original"))

    speaker_terms = [term for term in terms if len(term["source"]) >= 2 and (has_japanese_source(term["source"]) or CJK_RE.search(term["source"]))]
    for text_id, source in source_by_id.items():
        current = clean_text(current_by_id.get(text_id, ""))
        source_clean = clean_text(source)
        if not current:
            findings.append(Finding(title, "speaker_empty_name", "error", "__speakers__.egpack", text_id, source_clean, current))
            continue
        if KANA_RE.search(current):
            findings.append(Finding(title, "speaker_kana_residual", "error", "__speakers__.egpack", text_id, source_clean, current))
        simplified = cc.convert(current)
        if simplified != current and CJK_RE.search(current):
            findings.append(Finding(title, "speaker_traditional_or_kanji_residual", "warn", "__speakers__.egpack", text_id, source_clean, current, expected=simplified))
        if any(marker in current for marker in MOJIBAKE_MARKERS):
            findings.append(Finding(title, "speaker_mojibake_suspect", "error", "__speakers__.egpack", text_id, source_clean, current))
        for term in speaker_terms:
            if term["source"] in source_clean and compact(term["target"]) and compact(term["target"]) not in compact(current):
                findings.append(
                    Finding(
                        title,
                        "speaker_expected_term_missing",
                        "warn",
                        "__speakers__.egpack",
                        text_id,
                        source_clean,
                        current,
                        expected=term["target"],
                        term=term["source"],
                        note=term.get("category", ""),
                    )
                )

    return findings


def main() -> int:
    QA.mkdir(parents=True, exist_ok=True)
    terms = load_terms()
    reports: dict[str, list[Finding]] = {
        "term": [],
        "language": [],
        "speaker": [],
    }

    for title in TITLE_CSVS:
        reports["term"].extend(check_terms(title, terms))
        reports["language"].extend(check_language_quality(title))
        reports["speaker"].extend(check_speakers(title, terms))

    all_findings = reports["term"] + reports["language"] + reports["speaker"]
    json_path = QA / "first_round_audit_tda01_tda03.json"
    json_path.write_text(json.dumps([asdict(item) for item in all_findings], ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = QA / "first_round_audit_tda01_tda03.csv"
    fieldnames = list(asdict(Finding("", "", "", "", "", "", "")).keys())
    write_csv(csv_path, [asdict(item) for item in all_findings], fieldnames)

    summary = {
        "total_terms_loaded": len(terms),
        "total_findings": len(all_findings),
        "by_kind": dict(Counter(item.kind for item in all_findings)),
        "by_title": dict(Counter(item.title for item in all_findings)),
        "by_severity": dict(Counter(item.severity for item in all_findings)),
        "visible_findings": sum(item.visible == "yes" for item in all_findings),
        "non_visible_findings": sum(item.visible == "no" for item in all_findings),
        "json": str(json_path),
        "csv": str(csv_path),
    }
    summary_path = QA / "first_round_audit_tda01_tda03_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for item in all_findings[:120]:
        print(f"[{item.severity}] {item.title} {item.kind} {item.file} {item.text_id} term={item.term} expected={item.expected} current={item.current[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
