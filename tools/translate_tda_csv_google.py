from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


CONTROL_RE = re.compile(r"\\[A-Za-z]+")


JP_TO_ZH_TERMS = {
    "千堂柚香": "千堂柚香",
    "千堂": "千堂",
    "柚香": "柚香",
    "龍浪": "龙浪",
    "美桜乃雫": "美樱乃雫",
    "美桜乃": "美樱乃",
    "雫": "雫",
    "神宮司まりも": "神宫司麻理茉",
    "神宮司": "神宫司",
    "まりも": "麻理茉",
    "エレン・エイス": "艾伦·艾斯",
    "エレン": "艾伦",
    "エイス": "艾斯",
    "響": "响",
    "律子": "律子",
    "悠陽": "悠阳",
    "斑鳩": "斑鸠",
    "駒木": "驹木",
    "沙霧": "沙雾",
    "白銀武": "白银武",
    "斯衛": "斯卫",
    "戦術機": "战术机",
    "衛士": "卫士",
    "光線級": "光线级",
    "重光線級": "重光线级",
    "突撃級": "突击级",
    "要撃級": "要击级",
    "戦車級": "战车级",
    "兵士級": "士兵级",
    "闘士級": "斗士级",
    "母艦級": "母舰级",
    "大海崩": "大海崩",
    "北米航空宇宙防衛司令部": "北美防空司令部",
    "靖国": "靖国",
}


POST_REPLACEMENTS = {
    "贝塔": "BETA",
    "贝塔版": "BETA",
    "蜂巢": "HIVE",
    "海夫": "HIVE",
    "战术表面战斗机": "战术机",
    "战术地面战斗机": "战术机",
    "中尉": "中尉",
    "少尉": "少尉",
    "少佐": "少佐",
    "大尉": "大尉",
    "大佐": "大佐",
    "例子": "目标",
    "那东西": "那个东西",
}


def normalize_source(text: str) -> tuple[str, bool]:
    text = text.strip()
    quoted = text.startswith("「") and text.endswith("」")
    if quoted:
        text = text[1:-1]
    text = text.replace("\\n", " ")
    text = CONTROL_RE.sub("", text)
    text = text.replace("　", " ")
    for jp, zh in sorted(JP_TO_ZH_TERMS.items(), key=lambda kv: len(kv[0]), reverse=True):
        text = text.replace(jp, zh)
    text = re.sub(r"\s+", " ", text).strip()
    return text, quoted


def postprocess(text: str, quoted: bool) -> str:
    text = text.strip()
    text = text.replace("\\", "")
    text = text.strip(" “”“\"")
    for src, dst in POST_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = re.sub(r"\s+([，。！？；：、」])", r"\1", text)
    text = re.sub(r"([「（])\s+", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    if quoted and not (text.startswith("「") and text.endswith("」")):
        text = f"「{text}」"
    return text


def google_translate(text: str, timeout: int = 20) -> str:
    if not text:
        return ""
    url = (
        "https://translate.googleapis.com/translate_a/single"
        "?client=gtx&sl=ja&tl=zh-CN&dt=t&q="
        + urllib.parse.quote(text, safe="")
    )
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(request, timeout=timeout).read().decode("utf-8", "replace")
    payload = json.loads(data)
    return "".join(part[0] for part in payload[0] if part and part[0])


def load_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate extracted TDA CSV rows to Simplified Chinese.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("outputs/tda_text/google_translate_cache.json"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.05)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.input.open(encoding="utf-8-sig")))
    if args.limit:
        rows = rows[: args.limit]

    cache = load_cache(args.cache)
    translated = 0
    failed = 0
    started = time.time()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) + ["zh_machine"] if rows else ["zh_machine"]

    for i, row in enumerate(rows, 1):
        source, quoted = normalize_source(row.get("jp", ""))
        if not source:
            source, quoted = normalize_source(row.get("en", ""))

        if source in cache:
            zh = cache[source]
        else:
            try:
                zh = google_translate(source)
                cache[source] = zh
                translated += 1
                if args.sleep:
                    time.sleep(args.sleep)
            except Exception as exc:
                failed += 1
                zh = row.get("en", "")
                print(f"failed row={i} id={row.get('id')} err={exc!r}", flush=True)

        row["zh_machine"] = postprocess(zh, quoted)
        if i % 100 == 0:
            elapsed = time.time() - started
            print(f"progress {i}/{len(rows)} new={translated} failed={failed} elapsed={elapsed:.1f}s", flush=True)
            save_cache(args.cache, cache)

    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    save_cache(args.cache, cache)
    print(f"done rows={len(rows)} new={translated} failed={failed} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
