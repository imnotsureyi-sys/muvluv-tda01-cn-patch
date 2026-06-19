from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO / "tools" / "extract_egpack_text.py"


TITLES = {
    "tda01": {
        "csv": REPO / "outputs" / "tda_text" / "tda01_deepseek_full.csv",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda01\data"),
    },
    "tda02": {
        "csv": REPO / "outputs" / "tda_text" / "tda02_deepseek_full.csv",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda02\data"),
    },
    "tda03": {
        "csv": REPO / "outputs" / "tda_text" / "tda03_deepseek_full.csv",
        "installed": Path(r"C:\Users\Administrator\AppData\Local\ancr\tda03\data"),
    },
}


ALLOWED_ASCII_WORDS = {
    "BETA",
    "HIVE",
    "JFK",
    "NORAD",
    "TSF",
    "F",
    "PX",
    "OSP",
    "GL",
    "CP",
    "HQ",
    "XM",
    "AMWS",
    "WS",
    "S",
    "A",
    "B",
    "C",
    "D",
    "E",
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
}


MOJIBAKE_MARKERS = (
    "\ufffd",
    "Ã",
    "Â",
    "ã€",
    "ã",
    "ã‚",
    "ãƒ",
    "銆",
    "鈥",
    "绋",
    "鍗",
    "浣",
    "璇",
)

TERM_BLACKLIST = {
    "仙道": "千堂",
    "美园": "美樱乃雫",
    "美園": "美樱乃雫",
    "美樱乃静": "美樱乃雫",
    "美樱乃零": "美樱乃雫",
    "麻理茂": "麻理茉",
    "立浪": "龙浪",
    "龍波": "龙浪",
    "龙波": "龙浪",
    "塔科马港和城市": "塔科马港以及城市",
    "驾驶员章": "卫士徽章",
    "飞行员章": "卫士徽章",
    "地面飞行员": "卫士",
    "表面飞行员": "卫士",
    "美国飞行员": "美国卫士",
    "日本飞行员": "日本卫士",
    "贝塔": "BETA",
    "蜂巢": "HIVE",
    "・": "·",
}


CONTROL_RE = re.compile(r"\\[A-Za-z]")
LONG_ASCII_RE = re.compile(r"[A-Za-z][A-Za-z'’.-]{2,}(?:\s+[A-Za-z][A-Za-z'’.-]{2,}){2,}")
BACKSLASH_CJK_RE = re.compile(r"\\[\u4e00-\u9fff]")
W_ELLIPSIS_RE = re.compile(r"\bw[\.。…]+|w…")
QUESTION_RUN_RE = re.compile(r"\?{4,}")


@dataclass
class Finding:
    scope: str
    severity: str
    kind: str
    title: str
    file: str = ""
    text_id: str = ""
    sample: str = ""


def is_hiragana(ch: str) -> bool:
    return 0x3040 <= ord(ch) <= 0x309F


def is_katakana(ch: str) -> bool:
    return 0x30A0 <= ord(ch) <= 0x30FF


def kana_count(text: str) -> int:
    return sum(is_hiragana(ch) or is_katakana(ch) for ch in text or "")


def hira_count(text: str) -> int:
    return sum(is_hiragana(ch) for ch in text or "")


def cjk_count(text: str) -> int:
    return sum(0x4E00 <= ord(ch) <= 0x9FFF for ch in text or "")


def meaningful_source(row: dict[str, str]) -> bool:
    jp = (row.get("jp") or "").strip()
    en = (row.get("en") or "").strip()
    if not jp or en == "Pg9":
        return False
    stripped = re.sub(r"[「」『』（）()【】\[\]\s\\w\\p\\n…\.。,，!！?？ー―—ッっ]", "", jp)
    return bool(stripped)


def add_sample(text: str, limit: int = 160) -> str:
    text = (text or "").replace("\r", "").replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def audit_csv(title: str, csv_path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not csv_path.exists():
        return [Finding(title, "error", "missing_csv", "翻译 CSV 不存在", file=str(csv_path))]

    rows = load_csv(csv_path)
    seen: set[tuple[str, str]] = set()
    for row in rows:
        text_id = row.get("id", "")
        file_name = Path(row.get("file", "")).name
        key = (file_name, text_id)
        if key in seen:
            findings.append(Finding(title, "error", "duplicate_id", "同文件内 ID 重复", file=file_name, text_id=text_id))
        seen.add(key)

        zh = row.get("zh_deepseek", "") or ""
        jp = row.get("jp", "") or ""
        if meaningful_source(row) and not zh.strip():
            findings.append(Finding(title, "error", "empty_translation", "有源文本但中文为空", file=file_name, text_id=text_id, sample=add_sample(jp)))
        if hira_count(zh) >= 2:
            findings.append(Finding(title, "error", "hiragana_in_zh", "中文译文残留日文平假名", file=file_name, text_id=text_id, sample=add_sample(zh)))
        if kana_count(zh) >= 4:
            findings.append(Finding(title, "warn", "kana_in_zh", "中文译文残留较多假名", file=file_name, text_id=text_id, sample=add_sample(zh)))
        if CONTROL_RE.search(zh):
            findings.append(Finding(title, "error", "control_in_csv_zh", "中文译文残留控制符", file=file_name, text_id=text_id, sample=add_sample(zh)))
        if any(marker in zh for marker in MOJIBAKE_MARKERS):
            findings.append(Finding(title, "error", "mojibake_in_csv_zh", "中文译文疑似乱码", file=file_name, text_id=text_id, sample=add_sample(zh)))
        if QUESTION_RUN_RE.search(zh):
            findings.append(Finding(title, "error", "question_mark_corruption_in_csv", "中文译文出现连续问号，疑似写入时编码损坏", file=file_name, text_id=text_id, sample=add_sample(zh)))
        for bad, good in TERM_BLACKLIST.items():
            if bad in zh:
                findings.append(Finding(title, "error", "blacklisted_term_in_csv", f"疑似术语错误，应考虑：{good}", file=file_name, text_id=text_id, sample=add_sample(zh)))
        if W_ELLIPSIS_RE.search(zh) or BACKSLASH_CJK_RE.search(zh):
            findings.append(Finding(title, "error", "control_prefix_in_csv_zh", "中文译文疑似控制符残片", file=file_name, text_id=text_id, sample=add_sample(zh)))

        ascii_match = LONG_ASCII_RE.search(zh)
        if ascii_match:
            words = {w.strip(".,!?;:'\"()[]").upper() for w in re.findall(r"[A-Za-z][A-Za-z'’.-]*", ascii_match.group(0))}
            if not words <= ALLOWED_ASCII_WORDS:
                findings.append(Finding(title, "warn", "long_english_in_zh", "中文译文里有较长英文片段", file=file_name, text_id=text_id, sample=add_sample(zh)))

    return findings


def localized_dir(data_dir: Path) -> Path:
    return data_dir / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized"


def extract_installed(title: str, data_dir: Path, out_dir: Path) -> Path | None:
    source = localized_dir(data_dir)
    if not source.exists():
        return None
    out_csv = out_dir / f"qa_{title}_installed_slots.csv"
    cmd = [sys.executable, str(EXTRACTOR), str(source), "--output", str(out_csv)]
    subprocess.run(cmd, cwd=str(REPO), check=True, stdout=subprocess.DEVNULL)
    return out_csv


def audit_installed(title: str, data_dir: Path, extracted_csv: Path | None) -> list[Finding]:
    findings: list[Finding] = []
    locale = data_dir / ".locale"
    if not locale.exists():
        findings.append(Finding(title, "error", "missing_locale", ".locale 不存在", file=str(locale)))
    else:
        value = locale.read_text(encoding="ascii", errors="ignore").strip()
        if value != "jp":
            findings.append(Finding(title, "error", "wrong_locale", ".locale 不是 jp", file=str(locale), sample=value))

    source = localized_dir(data_dir)
    if not source.exists():
        findings.append(Finding(title, "error", "missing_installed_dir", "安装后的 localized 目录不存在", file=str(source)))
        return findings

    files = sorted(source.rglob("*.egpack"))
    if not files:
        findings.append(Finding(title, "error", "no_egpack", "安装目录没有 egpack 文件", file=str(source)))
    for p in files:
        data = p.read_bytes()
        if not data.startswith(b"EPK\0"):
            findings.append(Finding(title, "error", "bad_egpack_magic", "egpack 文件头异常", file=str(p)))
        if b"\\x00" in data[:0]:
            pass

    if extracted_csv is None or not extracted_csv.exists():
        return findings

    rows = load_csv(extracted_csv)
    for row in rows:
        jp_slot = row.get("jp", "") or ""
        text_id = row.get("id", "")
        file_name = Path(row.get("file", "")).name
        if hira_count(jp_slot) >= 2:
            findings.append(Finding(title, "error", "hiragana_in_installed_jp_slot", "安装后的日语槽仍残留平假名", file=file_name, text_id=text_id, sample=add_sample(jp_slot)))
        if CONTROL_RE.search(jp_slot):
            findings.append(Finding(title, "error", "visible_control_in_installed", "安装后的日语槽有可见控制符", file=file_name, text_id=text_id, sample=add_sample(jp_slot)))
        if W_ELLIPSIS_RE.search(jp_slot) or BACKSLASH_CJK_RE.search(jp_slot):
            findings.append(Finding(title, "error", "control_prefix_in_installed", "安装后的日语槽有控制符残片", file=file_name, text_id=text_id, sample=add_sample(jp_slot)))
        if any(marker in jp_slot for marker in MOJIBAKE_MARKERS):
            findings.append(Finding(title, "error", "mojibake_in_installed", "安装后的日语槽疑似乱码", file=file_name, text_id=text_id, sample=add_sample(jp_slot)))
        if QUESTION_RUN_RE.search(jp_slot):
            findings.append(Finding(title, "error", "question_mark_corruption_in_installed", "安装后的日语槽出现连续问号，疑似写入时编码损坏", file=file_name, text_id=text_id, sample=add_sample(jp_slot)))
        for bad, good in TERM_BLACKLIST.items():
            if bad in jp_slot:
                findings.append(Finding(title, "error", "blacklisted_term_in_installed", f"疑似术语错误，应考虑：{good}", file=file_name, text_id=text_id, sample=add_sample(jp_slot)))
        if len(jp_slot) > 90 and cjk_count(jp_slot) > 80:
            findings.append(Finding(title, "warn", "long_display_line", "安装后的单条文本较长，可能需要人工看换行", file=file_name, text_id=text_id, sample=add_sample(jp_slot)))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=REPO / "outputs" / "qa")
    parser.add_argument("--json", type=Path, default=REPO / "outputs" / "qa" / "tda_localization_qa.json")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    all_findings: list[Finding] = []
    summaries: dict[str, dict[str, int]] = {}

    for title, cfg in TITLES.items():
        findings = []
        findings.extend(audit_csv(title, cfg["csv"]))
        extracted = extract_installed(title, cfg["installed"], args.out_dir)
        findings.extend(audit_installed(title, cfg["installed"], extracted))
        all_findings.extend(findings)
        summaries[title] = {
            "error": sum(f.severity == "error" for f in findings),
            "warn": sum(f.severity == "warn" for f in findings),
            "total": len(findings),
        }

    payload = {
        "summaries": summaries,
        "findings": [asdict(f) for f in all_findings],
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for title, summary in summaries.items():
        print(f"{title}: errors={summary['error']} warnings={summary['warn']} total={summary['total']}")
    print(f"report={args.json}")
    if all_findings:
        print("first_findings:")
        for finding in all_findings[:80]:
            print(f"[{finding.severity}] {finding.scope} {finding.kind} {finding.file} {finding.text_id} {finding.sample}")
    return 1 if any(f.severity == "error" for f in all_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
