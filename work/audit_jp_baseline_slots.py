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
        "original": ROOT
        / "outputs"
        / "tda_fpd_extract"
        / "tda01"
        / "root"
        / "assets"
        / "data_spec"
        / "adv"
        / "game"
        / "scr"
        / "localized",
        "installed": Path(
            r"C:\Users\Administrator\AppData\Local\ancr\tda01\data\root\assets\data_spec\adv\game\scr\localized"
        ),
    },
    "tda02": {
        "original": ROOT
        / "outputs"
        / "tda_fpd_extract"
        / "tda02"
        / "root"
        / "assets"
        / "data_spec"
        / "adv"
        / "game"
        / "scr"
        / "localized",
        "installed": Path(
            r"C:\Users\Administrator\AppData\Local\ancr\tda02\data\root\assets\data_spec\adv\game\scr\localized"
        ),
    },
    "tda03": {
        "original": ROOT
        / "outputs"
        / "tda_fpd_extract"
        / "tda03"
        / "root"
        / "assets"
        / "data_spec"
        / "adv"
        / "game"
        / "scr"
        / "localized",
        "installed": Path(
            r"C:\Users\Administrator\AppData\Local\ancr\tda03\data\root\assets\data_spec\adv\game\scr\localized"
        ),
    },
}

ALLOWED_ASCII_WORDS = {
    "A-01",
    "A-6",
    "ACLU",
    "AMWS",
    "BETA",
    "CP",
    "DNA",
    "ECM",
    "F-15",
    "F-15E",
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

BAD_TERMS = {
    "pilot_as_flyer": ["地表飞行员", "美国地表飞行员", "美国飞行员", "飞行员", "驾驶员", "驾驶者", "飞行兵"],
    "miono_as_shizuka": ["结识静", "认识静", "见到静", "感谢静", "和静", "跟静", "对静", "小静", "静少尉"],
    "bad_name_sendo": ["仙道"],
    "bad_name_miono": ["美园", "美樱乃静"],
    "bad_yasukuni": ["靖国神社"],
}

CONTROL_RE = re.compile(r"\\[A-Za-z]")
ASCII_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'.-]*")
LONG_ASCII_PHRASE_RE = re.compile(r"[A-Za-z][A-Za-z0-9'.-]*(?:\s+[A-Za-z][A-Za-z0-9'.-]*){2,}")
TEXT_ID_RE = re.compile(r"\*\*\*\s*Text ID Not Found\s*\*\*\*", re.I)


@dataclass
class Finding:
    title: str
    severity: str
    kind: str
    file: str
    text_id: str
    original_jp: str = ""
    original_en: str = ""
    current_jp: str = ""
    current_en: str = ""
    note: str = ""


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def extract(title: str, src: Path, label: str, out_dir: Path) -> Path:
    out = out_dir / f"{title}_{label}_jp_baseline_slots.csv"
    subprocess.run(
        [sys.executable, str(EXTRACTOR), str(src), "--output", str(out)],
        cwd=str(ROOT),
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return out


def key(row: dict[str, str]) -> tuple[str, str]:
    return (Path(row.get("file", "")).name, row.get("id", ""))


def normalize(text: str) -> str:
    return (text or "").replace("\r", "").replace("\n", "\\n").strip()


def strip_controls(text: str) -> str:
    return CONTROL_RE.sub("", normalize(text)).replace("Pg9", "").strip()


def kana_count(text: str) -> int:
    return sum(0x3040 <= ord(c) <= 0x30FF for c in text or "")


def hira_count(text: str) -> int:
    return sum(0x3040 <= ord(c) <= 0x309F for c in text or "")


def cjk_count(text: str) -> int:
    return sum(0x4E00 <= ord(c) <= 0x9FFF for c in text or "")


def ascii_tokens(text: str) -> set[str]:
    return {w.strip(".-,!?;:'\"()[]{}").upper() for w in ASCII_WORD_RE.findall(text or "")}


def allowed_ascii_only(text: str) -> bool:
    tokens = ascii_tokens(text)
    return bool(tokens) and tokens <= ALLOWED_ASCII_WORDS


def has_mojibake(text: str) -> bool:
    if not text:
        return False
    if "\ufffd" in text or "锟" in text or "鈻" in text:
        return True
    # Typical UTF-8/GBK corruption fragments seen in earlier broken outputs.
    weird = sum(text.count(ch) for ch in "缁洪缚鐡夐懡瀹犵摣閾︼絿鎭摎鐑芥煣")
    return weird >= 3


def punctuation_only(text: str) -> bool:
    text = strip_controls(text)
    text = re.sub(r"[\s\"'「」『』（）()\[\]{}<>《》]+", "", text)
    if not text:
        return False
    return not re.search(r"[A-Za-z0-9\u3040-\u30ff\u3400-\u9fff]", text)


def meaningful_jp_source(row: dict[str, str]) -> bool:
    jp = strip_controls(row.get("jp", ""))
    if not jp:
        return False
    if jp == "Pg9":
        return False
    # Pure punctuation source slots are still real slots, but handled separately
    # because translating them needs nearby voice/context.
    return True


def compact_for_compare(text: str) -> str:
    text = strip_controls(text)
    text = re.sub(r"[\s「」『』（）()\[\]{}<>《》、。，．.,!?！？…‥ー―—・:：;；\"'“”‘’]+", "", text)
    return text


def audit_title(title: str, original_rows: list[dict[str, str]], current_rows: list[dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    original = {key(r): r for r in original_rows}
    current = {key(r): r for r in current_rows}

    for k, src in original.items():
        file_name, text_id = k
        cur = current.get(k)
        if cur is None:
            findings.append(Finding(title, "error", "missing_id", file_name, text_id, src.get("jp", ""), src.get("en", "")))
            continue

        if not meaningful_jp_source(src):
            continue

        jp = normalize(src.get("jp", ""))
        en = normalize(src.get("en", ""))
        zh = normalize(cur.get("jp", ""))
        cur_en = normalize(cur.get("en", ""))
        zh_clean = strip_controls(zh)

        if not zh_clean:
            findings.append(Finding(title, "error", "blank_jp_slot", file_name, text_id, jp, en, zh, cur_en))
            continue

        if TEXT_ID_RE.search(zh):
            findings.append(Finding(title, "error", "text_id_not_found", file_name, text_id, jp, en, zh, cur_en))
        if has_mojibake(zh):
            findings.append(Finding(title, "error", "mojibake", file_name, text_id, jp, en, zh, cur_en))
        if CONTROL_RE.search(zh):
            findings.append(Finding(title, "error", "visible_control", file_name, text_id, jp, en, zh, cur_en))
        if hira_count(zh) > 0:
            findings.append(Finding(title, "error", "hiragana_left", file_name, text_id, jp, en, zh, cur_en))
        elif kana_count(zh) >= 3:
            findings.append(Finding(title, "warn", "katakana_left", file_name, text_id, jp, en, zh, cur_en))

        if punctuation_only(zh):
            severity = "error" if not punctuation_only(jp) else "warn"
            findings.append(Finding(title, severity, "symbol_only_current", file_name, text_id, jp, en, zh, cur_en))

        if compact_for_compare(zh) == compact_for_compare(jp) and kana_count(jp) > 0:
            findings.append(Finding(title, "error", "same_as_original_japanese", file_name, text_id, jp, en, zh, cur_en))

        long_ascii = LONG_ASCII_PHRASE_RE.search(zh)
        if long_ascii and not allowed_ascii_only(long_ascii.group(0)):
            findings.append(Finding(title, "warn", "long_english_left", file_name, text_id, jp, en, zh, cur_en))
        if cjk_count(zh) == 0 and not punctuation_only(zh) and not allowed_ascii_only(zh):
            findings.append(Finding(title, "warn", "no_cjk_current", file_name, text_id, jp, en, zh, cur_en))

        for kind, terms in BAD_TERMS.items():
            for term in terms:
                if term in zh:
                    findings.append(Finding(title, "error", kind, file_name, text_id, jp, en, zh, cur_en, term))

    for k in sorted(set(current) - set(original)):
        file_name, text_id = k
        if file_name == "__staffroll__.egpack":
            continue
        findings.append(Finding(title, "warn", "extra_id", file_name, text_id, current_jp=current[k].get("jp", "")))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "qa" / "jp_baseline_slot_audit.json")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    all_findings: list[Finding] = []
    summaries: dict[str, dict[str, int]] = {}

    for title, cfg in TITLES.items():
        original_csv = extract(title, cfg["original"], "original", args.out.parent)
        current_csv = extract(title, cfg["installed"], "current", args.out.parent)
        original_rows = read_rows(original_csv)
        current_rows = read_rows(current_csv)
        findings = audit_title(title, original_rows, current_rows)
        all_findings.extend(findings)
        summaries[title] = {
            "original_rows": len(original_rows),
            "current_rows": len(current_rows),
            "jp_source_slots": sum(1 for r in original_rows if meaningful_jp_source(r)),
            "errors": sum(1 for f in findings if f.severity == "error"),
            "warnings": sum(1 for f in findings if f.severity == "warn"),
            "total": len(findings),
        }

    payload = {"summaries": summaries, "findings": [asdict(f) for f in all_findings]}
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for title, summary in summaries.items():
        print(
            f"{title}: jp_source_slots={summary['jp_source_slots']} "
            f"errors={summary['errors']} warnings={summary['warnings']} total={summary['total']}"
        )
    print(args.out)
    for f in all_findings[:120]:
        print(f"[{f.severity}] {f.title} {f.kind} {f.file} {f.text_id} :: {f.current_jp[:160]}")
    return 1 if any(f.severity == "error" for f in all_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
