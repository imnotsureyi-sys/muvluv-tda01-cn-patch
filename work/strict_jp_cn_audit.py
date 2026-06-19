from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "tools" / "extract_egpack_text.py"

TITLES = {
    "tda01": {
        "source": ROOT / "outputs" / "tda_fpd_extract" / "tda01" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "csv": ROOT / "outputs" / "tda_text" / "tda01_deepseek_full.csv",
        "current": ROOT / "outputs" / "repack_tda01_xmlsafe_20260615",
    },
    "tda02": {
        "source": ROOT / "outputs" / "tda_fpd_extract" / "tda02" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "csv": ROOT / "outputs" / "tda_text" / "tda02_deepseek_full.csv",
        "current": ROOT / "outputs" / "repack_tda02_xmlsafe_20260615",
    },
    "tda03": {
        "source": ROOT / "outputs" / "tda_fpd_extract" / "tda03" / "root" / "assets" / "data_spec" / "adv" / "game" / "scr" / "localized",
        "csv": ROOT / "outputs" / "tda_text" / "tda03_deepseek_full.csv",
        "current": ROOT / "outputs" / "repack_tda03_xmlsafe_20260615",
    },
}

CONTROL_RE = re.compile(r"\\[A-Za-z]+")
ASCII_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'.-]*")
LONG_ASCII_RE = re.compile(r"[A-Za-z][A-Za-z0-9'.-]*(?:\s+[A-Za-z][A-Za-z0-9'.-]*){2,}")
TEXT_ID_RE = re.compile(r"Text ID Not Found", re.I)
ID_RE = re.compile(r"(?:game_[ts]|tda03_[ts]|tda02_staff)\d+(?:_ruby)?")

ALLOWED_ASCII = {
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

JP_TERMS = {
    "ウォードッグ": "战犬",
    "Wardog": "战犬",
    "Wardogs": "战犬",
    "衛士": "卫士",
    "衛士徽章": "卫士徽章",
    "パイロット": "卫士",
    "大尉": "上尉",
    "中尉": "中尉",
    "少佐": "少佐",
    "神宮司まりも": "神宫司麻理茉",
    "神宮司": "神宫司",
    "龍浪": "龙浪",
    "竜浪": "龙浪",
    "斑鳩": "斑鸠",
    "駒木": "驹木",
    "米軍": "美军",
    "米国": "美",
    "帝国軍": "我军",
    "バビロン作戦": "巴比伦作战",
    "バビロン": "巴比伦",
}

BAD_CN_SNIPPETS = {
    "龍浪": "繁体/旧字残留，应为龙浪",
    "大隊長": "日文汉字残留",
    "正規": "日文汉字残留",
    "情報": "日文汉字残留",
    "神宮司": "日文汉字残留，应为神宫司",
    "軍人優遇反対": "日文残留",
    "可憐": "繁体/日文汉字残留",
    "関係": "日文汉字残留",
    "駒木": "日文汉字残留，应为驹木",
    "斑鳩": "日文汉字残留，应为斑鸠",
    "這種": "繁体残留，应为这种",
    "沃德狗": "术语错误，应为战犬",
    "战狗": "术语错误，应为战犬",
    "沃德": "术语错误，应为战犬或沃肯，需看日文",
    "沃克": "人名错误候选，应为沃肯",
    "沃尔肯": "人名错误候选，应为沃肯",
    "神宫司麻理茂": "人名错误，应为神宫司麻理茉",
    "飞行员徽章": "术语错误，应为卫士徽章",
    "地表飞行员": "术语错误，应为卫士",
    "表面飞行员": "术语错误，应为卫士",
    "驾驶员徽章": "术语错误，应为卫士徽章",
    "大尉": "军衔错误，应为上尉",
    "希望亡命": "译法错误，应为寻求庇护",
    "巴比伦行动": "术语错误，应为巴比伦作战",
}

MOJIBAKE_CHARS = set("缂佹椽缂氶悺澶愭嚒鐎圭姷鎽ｉ柧锔肩悼閹參鎽庨悜鑺ョ叄")


@dataclass
class Finding:
    title: str
    severity: str
    kind: str
    file: str
    text_id: str
    jp: str
    cn: str
    note: str = ""


def norm(text: str) -> str:
    return (text or "").replace("\r", "").replace("\n", "\\n").strip()


def strip_controls(text: str) -> str:
    return CONTROL_RE.sub("", norm(text)).replace("Pg9", "").strip()


def punctuation_only(text: str) -> bool:
    text = strip_controls(text)
    if not text:
        return False
    text = re.sub(r"[\s\"'“”‘’「」『』（）()\[\]{}<>《》、。，，,.!?！？…‥ー—－・:：;；~～]+", "", text)
    return not text


def vocal_like(text: str) -> bool:
    text = strip_controls(text)
    if not text:
        return False
    compact = re.sub(r"[\s\"'“”‘’「」『』（）()\[\]{}<>《》、。，，,.!?！？…‥ー—－・:：;；~～]+", "", text)
    if not compact:
        return True
    jp_vocal = set("あいうえおぁぃぅぇぉっんァアィイゥウェエォオッンわワはハひヒふフへヘほホやヤゆユよヨぎギゃャ")
    cn_vocal = set("啊呀哇唔呜嗯哼呃诶欸哦哈呵嘿咦嗬")
    if all(ch in jp_vocal or ch in cn_vocal for ch in compact):
        return True
    return len(compact) <= 3 and not re.search(r"[一-龥A-Za-z0-9]", compact)


def kana_count(text: str) -> int:
    return sum(0x3040 <= ord(c) <= 0x30FF for c in text or "")


def cjk_count(text: str) -> int:
    return sum(0x4E00 <= ord(c) <= 0x9FFF for c in text or "")


def ascii_tokens(text: str) -> set[str]:
    return {w.strip(".-,!?;:'\"()[]{}").upper() for w in ASCII_WORD_RE.findall(text or "")}


def allowed_ascii_only(text: str) -> bool:
    tokens = ascii_tokens(text)
    return bool(tokens) and tokens <= ALLOWED_ASCII


def has_mojibake(text: str) -> bool:
    if not text:
        return False
    if "\ufffd" in text or "锟" in text:
        return True
    return sum(text.count(ch) for ch in MOJIBAKE_CHARS) >= 3


def compact_compare(text: str) -> str:
    text = strip_controls(text)
    return re.sub(r"[\s\"'“”‘’「」『』（）()\[\]{}<>《》、。，，,.!?！？…‥ー—－・:：;；~～]+", "", text)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def extract_baseline(title: str, source: Path, out_dir: Path) -> Path:
    out = out_dir / f"{title}_strict_jp_baseline.csv"
    subprocess.run(
        [sys.executable, str(EXTRACTOR), str(source), "--output", str(out)],
        cwd=str(ROOT),
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return out


def key(row: dict[str, str]) -> tuple[str, str]:
    return (Path(row.get("file", "")).name, row.get("id", ""))


def visible_before_id(path: Path) -> list[dict[str, str]]:
    data = path.read_bytes()
    if not data.startswith(b"EPK\0"):
        return []
    text = data.decode("utf-8", "surrogateescape")
    matches = list(ID_RE.finditer(text))
    rows: list[dict[str, str]] = []
    previous_id_end = 0
    for match in matches:
        tid = match.group()
        if tid.endswith("_ruby"):
            previous_id_end = match.end()
            continue
        segment = text[previous_id_end : match.start()]
        previous_id_end = match.end()
        before_p = segment.rsplit("\\p", 1)[0] if "\\p" in segment else segment
        runs = []
        start: int | None = None
        for index, ch in enumerate(before_p):
            boundary = ch == "\x00" or 0xDC80 <= ord(ch) <= 0xDCFF or (ord(ch) < 32 and ch not in "\t\r\n")
            if boundary:
                if start is not None:
                    runs.append(before_p[start:index])
                    start = None
            elif start is None:
                start = index
        if start is not None:
            runs.append(before_p[start:])
        runs = [norm(r) for r in runs if norm(r) and norm(r) != "Pg9"]
        display = runs[-1] if runs else ""
        rows.append({"file": path.name, "id": tid, "display": display})
    return rows


def extract_current_display(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for egpack in sorted(path.glob("*.egpack")):
        rows.extend(visible_before_id(egpack))
    return rows


def audit_title(title: str, baseline_rows: list[dict[str, str]], cn_rows: list[dict[str, str]], current_rows: list[dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    baseline = {key(r): r for r in baseline_rows}
    cn_by_key = {key(r): r for r in cn_rows}
    current_by_key = {(r["file"], r["id"]): r for r in current_rows}

    for k, src in baseline.items():
        file_name, text_id = k
        jp = norm(src.get("jp", ""))
        row = cn_by_key.get(k)
        if row is None:
            findings.append(Finding(title, "error", "missing_csv_row", file_name, text_id, jp, ""))
            continue
        csv_jp = norm(row.get("jp", ""))
        cn = norm(row.get("zh_deepseek", ""))
        if csv_jp != jp:
            findings.append(Finding(title, "error", "csv_jp_differs_from_reextracted_jp", file_name, text_id, jp, cn, f"csv_jp={csv_jp}"))
        if norm(row.get("en", "")):
            findings.append(Finding(title, "error", "en_field_not_empty", file_name, text_id, jp, cn, row.get("en", "")))
        if not strip_controls(jp):
            if strip_controls(cn):
                findings.append(Finding(title, "error", "jp_empty_but_cn_not_empty", file_name, text_id, jp, cn))
            continue
        if not strip_controls(cn):
            findings.append(Finding(title, "error", "jp_not_empty_but_cn_empty", file_name, text_id, jp, cn))
            continue
        if punctuation_only(jp) and not punctuation_only(cn):
            findings.append(Finding(title, "warn", "jp_symbol_but_cn_not_symbol", file_name, text_id, jp, cn))
        if vocal_like(jp) and not vocal_like(cn):
            findings.append(Finding(title, "warn", "jp_vocal_but_cn_not_vocal", file_name, text_id, jp, cn))
        if not vocal_like(jp) and vocal_like(cn) and cjk_count(strip_controls(jp)) >= 2:
            findings.append(Finding(title, "warn", "jp_normal_but_cn_vocal_only", file_name, text_id, jp, cn))
        if TEXT_ID_RE.search(cn):
            findings.append(Finding(title, "error", "text_id_not_found_text", file_name, text_id, jp, cn))
        if has_mojibake(cn):
            findings.append(Finding(title, "error", "mojibake", file_name, text_id, jp, cn))
        if kana_count(cn):
            findings.append(Finding(title, "error", "japanese_kana_left_in_cn", file_name, text_id, jp, cn))
        if compact_compare(cn) == compact_compare(jp) and kana_count(jp):
            findings.append(Finding(title, "error", "cn_same_as_jp", file_name, text_id, jp, cn))
        m = LONG_ASCII_RE.search(cn)
        if m and not allowed_ascii_only(m.group(0)):
            findings.append(Finding(title, "warn", "long_english_left", file_name, text_id, jp, cn, m.group(0)))
        if cjk_count(cn) == 0 and not punctuation_only(cn) and not vocal_like(cn) and not allowed_ascii_only(cn):
            findings.append(Finding(title, "warn", "cn_has_no_chinese", file_name, text_id, jp, cn))
        for bad, note in BAD_CN_SNIPPETS.items():
            if bad in cn:
                findings.append(Finding(title, "error", "bad_cn_snippet", file_name, text_id, jp, cn, f"{bad}: {note}"))
        for jp_term, cn_term in JP_TERMS.items():
            if jp_term in jp and cn_term not in cn:
                findings.append(Finding(title, "warn", "term_expected_translation_missing", file_name, text_id, jp, cn, f"{jp_term} -> {cn_term}"))

        cur = current_by_key.get(k)
        if cur is not None:
            display = norm(cur.get("display", ""))
            if not strip_controls(display):
                findings.append(Finding(title, "error", "current_display_blank_for_nonempty_jp", file_name, text_id, jp, cn))
            if TEXT_ID_RE.search(display):
                findings.append(Finding(title, "error", "current_display_text_id_not_found", file_name, text_id, jp, display))
            if kana_count(display):
                findings.append(Finding(title, "error", "current_display_japanese_left", file_name, text_id, jp, display))

    for k, row in cn_by_key.items():
        if k not in baseline:
            findings.append(Finding(title, "warn", "csv_extra_row_not_in_reextracted_jp", k[0], k[1], "", norm(row.get("zh_deepseek", ""))))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict JP-only audit for TDA01-03 CSV and rebuilt egpacks.")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "qa" / "strict_jp_cn_audit")
    args = parser.parse_args()

    all_findings: list[Finding] = []
    summary: dict[str, object] = {}
    for title, cfg in TITLES.items():
        baseline_path = extract_baseline(title, cfg["source"], args.out_dir)
        baseline_rows = read_csv(baseline_path)
        cn_rows = read_csv(cfg["csv"])
        current_rows = extract_current_display(cfg["current"])
        write_csv(args.out_dir / f"{title}_current_display.csv", current_rows, ["file", "id", "display"])
        findings = audit_title(title, baseline_rows, cn_rows, current_rows)
        all_findings.extend(findings)
        counter = Counter(f.kind for f in findings)
        summary[title] = {
            "baseline_rows": len(baseline_rows),
            "csv_rows": len(cn_rows),
            "current_display_rows": len(current_rows),
            "findings": len(findings),
            "by_kind": dict(sorted(counter.items())),
        }
        write_csv(
            args.out_dir / f"{title}_findings.csv",
            [asdict(f) for f in findings],
            ["title", "severity", "kind", "file", "text_id", "jp", "cn", "note"],
        )

    counter = Counter(f.kind for f in all_findings)
    summary["all"] = {"findings": len(all_findings), "by_kind": dict(sorted(counter.items()))}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(
        args.out_dir / "all_findings.csv",
        [asdict(f) for f in all_findings],
        ["title", "severity", "kind", "file", "text_id", "jp", "cn", "note"],
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
