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
        "csv": ROOT / "outputs" / "tda_text" / "tda01_deepseek_full.csv",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda01\data"),
    },
    "tda02": {
        "csv": ROOT / "outputs" / "tda_text" / "tda02_deepseek_full.csv",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda02\data"),
    },
    "tda03": {
        "csv": ROOT / "outputs" / "tda_text" / "tda03_deepseek_full.csv",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda03\data"),
    },
}

ALLOWED_ASCII_WORDS = {
    "A-6",
    "AMWS",
    "BETA",
    "CP",
    "ECM",
    "HQ",
    "HIVE",
    "IJMDF",
    "JFK",
    "NATO",
    "NORAD",
    "OSP",
    "PX",
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

VISIBLE_CONTROL_RE = re.compile(r"\\[A-Za-z]")
QUESTION_RUN_RE = re.compile(r"\?{3,}")
ASCII_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'.-]*")
LONG_ASCII_PHRASE_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9'.-]*(?:\s+[A-Za-z][A-Za-z0-9'.-]*){2,}"
)
TEXT_ID_RE = re.compile(r"\*\*\*\s*Text ID Not Found\s*\*\*\*", re.I)


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


def sample(text: str, limit: int = 240) -> str:
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
    # Common UTF-8-as-CP932/GBK mojibake often mixes many of these.
    weird = sum(text.count(ch) for ch in "縺譁荳譛蝣繧蜷閾")
    return weird >= 3


def ascii_tokens(text: str) -> set[str]:
    return {w.strip(".-,!?;:'\"()[]{}").upper() for w in ASCII_WORD_RE.findall(text or "")}


def is_allowed_ascii_only(text: str) -> bool:
    tokens = ascii_tokens(text)
    return bool(tokens) and tokens <= ALLOWED_ASCII_WORDS


def source_has_real_text(row: dict[str, str]) -> bool:
    jp = (row.get("jp") or "").strip()
    en = (row.get("en") or "").strip()
    if not jp and not en:
        return False
    if row.get("id", "").endswith("_ruby"):
        return False
    return True


def audit_rows(title: str, rows: list[dict[str, str]], zh_key: str) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        file_name = Path(row.get("file", "")).name
        text_id = row.get("id", "")
        jp = row.get("jp", "") or ""
        en = row.get("en", "") or ""
        zh = row.get(zh_key, "") or ""
        key = (file_name, text_id)
        if key in seen:
            findings.append(Finding(title, "error", "duplicate_id", file_name, text_id, jp, en, zh))
        seen.add(key)

        if source_has_real_text(row) and not zh.strip():
            findings.append(Finding(title, "error", "empty_translation", file_name, text_id, jp, en, zh))
        if TEXT_ID_RE.search(zh):
            findings.append(Finding(title, "error", "text_id_not_found", file_name, text_id, jp, en, zh))
        if QUESTION_RUN_RE.search(zh):
            findings.append(Finding(title, "error", "question_run", file_name, text_id, jp, en, zh))
        if VISIBLE_CONTROL_RE.search(zh):
            findings.append(Finding(title, "error", "visible_control", file_name, text_id, jp, en, zh))
        if has_mojibake(zh):
            findings.append(Finding(title, "error", "mojibake", file_name, text_id, jp, en, zh))
        if hira_count(zh) >= 1:
            findings.append(Finding(title, "error", "hiragana_left", file_name, text_id, jp, en, zh))
        elif kana_count(zh) >= 3:
            findings.append(Finding(title, "warn", "katakana_left", file_name, text_id, jp, en, zh))

        m = LONG_ASCII_PHRASE_RE.search(zh)
        if m and not is_allowed_ascii_only(m.group(0)):
            findings.append(
                Finding(title, "warn", "long_english_left", file_name, text_id, jp, en, zh)
            )

        if zh.strip() == jp.strip() and kana_count(jp) >= 1:
            findings.append(Finding(title, "error", "same_as_japanese", file_name, text_id, jp, en, zh))
        if zh.strip() == en.strip() and len(en.strip()) > 8 and not is_allowed_ascii_only(en):
            findings.append(Finding(title, "warn", "same_as_english", file_name, text_id, jp, en, zh))
        if cjk_count(zh) == 0 and source_has_real_text(row) and len(zh.strip()) > 0 and not is_allowed_ascii_only(zh):
            findings.append(Finding(title, "warn", "no_cjk_translation", file_name, text_id, jp, en, zh))

    return findings


def extract_installed(title: str, data_dir: Path, out_dir: Path) -> Path | None:
    loc = data_dir / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized"
    if not loc.exists():
        return None
    out = out_dir / f"{title}_installed_slots.csv"
    subprocess.run(
        [sys.executable, str(EXTRACTOR), str(loc), "--output", str(out)],
        cwd=str(ROOT),
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return out


def compare_csv_to_installed(
    title: str, source_rows: list[dict[str, str]], installed_rows: list[dict[str, str]]
) -> list[Finding]:
    findings: list[Finding] = []
    source = {(Path(r.get("file", "")).name, r.get("id", "")): r for r in source_rows}
    installed = {(Path(r.get("file", "")).name, r.get("id", "")): r for r in installed_rows}
    for key, row in source.items():
        if key not in installed:
            findings.append(
                Finding(title, "error", "missing_in_installed", key[0], key[1], row.get("jp", ""), row.get("en", ""), row.get("zh_deepseek", ""))
            )
            continue
        src_zh = (row.get("zh_deepseek", "") or "").strip()
        inst_jp = (installed[key].get("jp", "") or "").strip()
        if src_zh != inst_jp:
            findings.append(
                Finding(title, "error", "installed_differs_from_csv", key[0], key[1], row.get("jp", ""), row.get("en", ""), inst_jp, note=f"csv={sample(src_zh)}")
            )
    for key, row in installed.items():
        if key not in source:
            findings.append(
                Finding(title, "warn", "extra_in_installed", key[0], key[1], row.get("jp", ""), row.get("en", ""), row.get("jp", ""))
            )
    return findings


def audit_script_references(title: str, data_dir: Path, installed_rows: list[dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    loc = data_dir / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized"
    if not loc.exists():
        return findings
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
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "qa" / "tda_text_audit.json")
    args = parser.parse_args()

    out_dir = args.out.parent
    all_findings: list[Finding] = []
    summaries: dict[str, dict[str, int]] = {}
    for title, cfg in TITLES.items():
        csv_rows = read_csv(cfg["csv"])
        findings = audit_rows(title, csv_rows, "zh_deepseek")
        extracted = extract_installed(title, cfg["installed"], out_dir)
        if extracted:
            installed_rows = read_csv(extracted)
            findings.extend(audit_rows(title, installed_rows, "jp"))
            findings.extend(compare_csv_to_installed(title, csv_rows, installed_rows))
            findings.extend(audit_script_references(title, cfg["installed"], installed_rows))
        else:
            findings.append(Finding(title, "error", "missing_installed_dir", str(cfg["installed"]), ""))
        all_findings.extend(findings)
        summaries[title] = {
            "errors": sum(f.severity == "error" for f in findings),
            "warnings": sum(f.severity == "warn" for f in findings),
            "total": len(findings),
        }

    payload = {"summaries": summaries, "findings": [asdict(f) for f in all_findings]}
    write_json(args.out, payload)
    for title, s in summaries.items():
        print(f"{title}: errors={s['errors']} warnings={s['warnings']} total={s['total']}")
    print(args.out)
    for f in all_findings[:80]:
        print(f"[{f.severity}] {f.title} {f.kind} {f.file} {f.text_id} {sample(f.zh)}")
    return 1 if any(f.severity == "error" for f in all_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
