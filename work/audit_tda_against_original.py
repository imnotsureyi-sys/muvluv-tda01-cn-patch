from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "tools" / "extract_egpack_text.py"

TITLES = {
    "tda01": {
        "original": ROOT / "outputs" / "tda_fpd_extract" / "tda01" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda01\data\root\assets\data_spec\adv\game\scr\localized"),
    },
    "tda02": {
        "original": ROOT / "outputs" / "tda_fpd_extract" / "tda02" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda02\data\root\assets\data_spec\adv\game\scr\localized"),
    },
    "tda03": {
        "original": ROOT / "outputs" / "tda_fpd_extract" / "tda03" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda03\data\root\assets\data_spec\adv\game\scr\localized"),
    },
}

ALLOWED_ASCII_WORDS = {
    "A-01",
    "A-6",
    "AMWS",
    "BETA",
    "CP",
    "ECM",
    "F-22A",
    "HQ",
    "HIVE",
    "IJMDF",
    "JFK",
    "MIA",
    "NATO",
    "NORAD",
    "OSP",
    "PX",
    "S-11",
    "TDA",
    "TSF",
    "UN",
    "USA",
    "XM3",
}

MOJIBAKE_SNIPPETS = (
    "\ufffd",
    "\u00c3",
    "\u00c2",
    "\u00e2",
    "\u00ef",
    "\u00bf",
    "\u00e3",
    "\u9286",
    "\u9225",
    "\u923e",
)

TEXT_ID_RE = re.compile(r"\*\*\*\s*Text ID Not Found\s*\*\*\*", re.I)
VISIBLE_CONTROL_RE = re.compile(r"\\[A-Za-z]")
QUESTION_RUN_RE = re.compile(r"\?{3,}")
ASCII_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'.-]*")
LONG_ASCII_PHRASE_RE = re.compile(r"[A-Za-z][A-Za-z0-9'.-]*(?:\s+[A-Za-z][A-Za-z0-9'.-]*){2,}")


@dataclass
class Finding:
    title: str
    severity: str
    kind: str
    file: str
    text_id: str
    jp: str = ""
    en: str = ""
    zh: str = ""
    note: str = ""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_slots(title: str, loc: Path, label: str, out_dir: Path) -> Path:
    out = out_dir / f"{title}_{label}_slots.csv"
    subprocess.run(
        [sys.executable, str(EXTRACTOR), str(loc), "--output", str(out)],
        cwd=str(ROOT),
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return out


def sample(text: str, limit: int = 220) -> str:
    text = (text or "").replace("\r", "").replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


def kana_count(text: str) -> int:
    return sum(0x3040 <= ord(c) <= 0x30FF for c in text or "")


def hira_count(text: str) -> int:
    return sum(0x3040 <= ord(c) <= 0x309F for c in text or "")


def cjk_count(text: str) -> int:
    return sum(0x4E00 <= ord(c) <= 0x9FFF for c in text or "")


def has_mojibake(text: str) -> bool:
    if not text:
        return False
    if any(s in text for s in MOJIBAKE_SNIPPETS):
        return True
    weird = sum(text.count(ch) for ch in "绺鸿瓉鑽宠瓫铦ｇ恭铚烽柧")
    return weird >= 3


def punctuation_only(text: str) -> bool:
    stripped = re.sub(r"\\[A-Za-z]", "", text or "")
    stripped = stripped.replace("Pg9", "")
    stripped = re.sub(r"[\s\"'「」『』（）()\[\]{}]+", "", stripped)
    return bool(stripped) and not re.search(r"[\w\u3040-\u30ff\u3400-\u9fff]", stripped)


def ignorable_empty_current(text: str) -> bool:
    stripped = (text or "").strip()
    return not stripped or stripped == "Pg9" or punctuation_only(stripped)


def ascii_tokens(text: str) -> set[str]:
    return {w.strip(".-,!?;:'\"()[]{}").upper() for w in ASCII_WORD_RE.findall(text or "")}


def is_allowed_ascii_only(text: str) -> bool:
    tokens = ascii_tokens(text)
    return bool(tokens) and tokens <= ALLOWED_ASCII_WORDS


def rows_by_key(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(Path(r.get("file", "")).name, r.get("id", "")): r for r in rows}


def real_source_text(row: dict[str, str]) -> bool:
    jp = (row.get("jp") or "").strip()
    en = (row.get("en") or "").strip()
    if not jp and not en:
        return False
    if en == "Pg9" and not jp:
        return False
    if punctuation_only(jp) and (not en or en == "Pg9" or punctuation_only(en)):
        return False
    return True


def audit_pair(title: str, original_rows: list[dict[str, str]], installed_rows: list[dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    original = rows_by_key(original_rows)
    installed = rows_by_key(installed_rows)

    for key, src in original.items():
        file_name, text_id = key
        if file_name in {"__speakers__.egpack", "__staffroll__.egpack"}:
            continue
        jp = src.get("jp", "") or ""
        en = src.get("en", "") or ""
        dst = installed.get(key)
        if dst is None:
            findings.append(Finding(title, "error", "missing_current_id", file_name, text_id, jp, en))
            continue

        zh = dst.get("jp", "") or ""
        current_en = dst.get("en", "") or ""
        display_text = zh if zh.strip() else current_en
        if real_source_text(src) and not zh.strip():
            if not jp.strip() and en.strip():
                if not ignorable_empty_current(current_en) and (
                    current_en.strip() == en.strip() or cjk_count(current_en) == 0
                ):
                    findings.append(Finding(title, "warn", "english_slot_only_untranslated", file_name, text_id, jp, en, current_en))
            else:
                findings.append(Finding(title, "error", "empty_current_cn", file_name, text_id, jp, en, zh))
        if TEXT_ID_RE.search(display_text):
            findings.append(Finding(title, "error", "text_id_not_found", file_name, text_id, jp, en, display_text))
        if QUESTION_RUN_RE.search(display_text):
            findings.append(Finding(title, "error", "question_run", file_name, text_id, jp, en, display_text))
        if VISIBLE_CONTROL_RE.search(display_text):
            findings.append(Finding(title, "error", "visible_control", file_name, text_id, jp, en, display_text))
        if has_mojibake(display_text):
            findings.append(Finding(title, "error", "mojibake", file_name, text_id, jp, en, display_text))
        if hira_count(display_text) >= 1 and not punctuation_only(jp):
            findings.append(Finding(title, "error", "hiragana_left", file_name, text_id, jp, en, display_text))
        elif kana_count(display_text) >= 3 and not punctuation_only(jp):
            findings.append(Finding(title, "warn", "katakana_left", file_name, text_id, jp, en, display_text))

        if zh.strip() == jp.strip() and real_source_text(src) and kana_count(jp) >= 1:
            findings.append(Finding(title, "error", "same_as_original_japanese", file_name, text_id, jp, en, zh))
        if display_text.strip() == en.strip() and len(en.strip()) > 8 and not is_allowed_ascii_only(en):
            findings.append(Finding(title, "warn", "same_as_original_english", file_name, text_id, jp, en, display_text))
        m = LONG_ASCII_PHRASE_RE.search(display_text)
        if m and not is_allowed_ascii_only(m.group(0)):
            findings.append(Finding(title, "warn", "long_english_left", file_name, text_id, jp, en, display_text))
        if (
            cjk_count(display_text) == 0
            and real_source_text(src)
            and display_text.strip()
            and not ignorable_empty_current(display_text)
            and not punctuation_only(display_text)
            and not is_allowed_ascii_only(display_text)
        ):
            findings.append(Finding(title, "warn", "no_cjk_current_cn", file_name, text_id, jp, en, display_text))

    for key, row in installed.items():
        if key not in original:
            file_name, text_id = key
            if Path(file_name).name == "__staffroll__.egpack":
                continue
            findings.append(Finding(title, "warn", "extra_current_id", file_name, text_id, zh=row.get("jp", "") or ""))

    return findings


def audit_script_references(title: str, loc: Path, installed_rows: list[dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    ids_by_file: dict[str, set[str]] = {}
    for row in installed_rows:
        ids_by_file.setdefault(Path(row.get("file", "")).stem, set()).add(row.get("id", ""))
    ref_re = re.compile(r"\$((?:game|tda03)_[ts]\d+|(?:game|tda03)_t\d+_ruby)")
    for xml in loc.glob("*.xml"):
        refs = set(ref_re.findall(xml.read_text(encoding="utf-8", errors="replace")))
        missing = sorted(refs - ids_by_file.get(xml.stem, set()))
        for text_id in missing:
            findings.append(Finding(title, "error", "missing_referenced_id", xml.name, text_id))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "qa" / "tda_original_vs_current_audit.json")
    args = parser.parse_args()

    out_dir = args.out.parent
    all_findings: list[Finding] = []
    summaries: dict[str, dict[str, int]] = {}
    for title, cfg in TITLES.items():
        original_path = extract_slots(title, cfg["original"], "original", out_dir)
        current_path = extract_slots(title, cfg["installed"], "current", out_dir)
        original_rows = read_csv(original_path)
        current_rows = read_csv(current_path)
        findings = audit_pair(title, original_rows, current_rows)
        findings.extend(audit_script_references(title, cfg["installed"], current_rows))
        all_findings.extend(findings)
        summaries[title] = {
            "source_rows": len(original_rows),
            "current_rows": len(current_rows),
            "errors": sum(f.severity == "error" for f in findings),
            "warnings": sum(f.severity == "warn" for f in findings),
            "total": len(findings),
        }

    payload = {"summaries": summaries, "findings": [asdict(f) for f in all_findings]}
    write_json(args.out, payload)
    for title, s in summaries.items():
        print(
            f"{title}: source={s['source_rows']} current={s['current_rows']} "
            f"errors={s['errors']} warnings={s['warnings']} total={s['total']}"
        )
    print(args.out)
    for f in all_findings[:80]:
        print(f"[{f.severity}] {f.title} {f.kind} {f.file} {f.text_id} {sample(f.zh)}")
    return 1 if any(f.severity == "error" for f in all_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
