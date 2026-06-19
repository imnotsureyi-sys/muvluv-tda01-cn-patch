from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import http.client
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "https://api.deepseek.com/chat/completions"


SYSTEM_PROMPT = """你是视觉小说《Muv-Luv》系列的日译中本地化译者。
任务：把日文原文翻译成简体中文。英文只作为理解参考，不能照抄英文误译。
要求：
1. 输出自然中文，适合游戏字幕，不解释、不加注释。
2. 保留原句语气、脏话强度、军队口吻和角色关系。
3. 专有名词必须统一：
千堂=Sendo=千堂；千堂柚香=Sendo Yuzuka=千堂柚香；龍浪=Tatsunami=龙浪；
美桜乃雫 / 美桜乃静 / Miono Shizuku=美樱乃雫；
エレン・エイス / Ellen Aice=艾伦·艾斯；エレン=艾伦；
神宮司まりも / Jinguuji Marimo=神宫司麻理茉；
響=响；律子=律子；悠陽=悠阳；駒木=驹木；斑鳩=斑鸠；沙霧=沙雾；白銀武=白银武。
4. 军衔统一：
少尉=少尉，Lieutenant 在 Muv-Luv 英文里可能表示少尉/中尉，必须优先按日文判断；
中尉=中尉，少佐=少佐，大尉=大尉，大佐=大佐。
5. 世界观词：
BETA 保持 BETA；HIVE 保持 HIVE；戦術機=战术机；衛士=卫士；英文参考中的 surface pilot / TSF pilot / pilot 若指战术机驾驶人员，一律译为卫士，不译飞行员/驾驶员；光線級=光线级；重光線級=重光线级；
突撃級=突击级；要撃級=要击级；戦車級=战车级；兵士級=士兵级；闘士級=斗士级；母艦級=母舰级；
斯衛=斯卫；大海崩=大海崩；北米航空宇宙防衛司令部=NORAD/北美防空司令部，按语境选择。
6. 保留外层日式引号「」：如果原文有「」，译文也用「」。
7. 不要输出控制码，不要输出 \\w、\\p、\\n。
"""


USER_PROMPT = """请翻译下面 JSON 数组。每项含 id、jp、en。
返回严格 JSON 对象：{{"items":[{{"id":"原id","zh":"中文译文"}}]}}。
不要输出 Markdown。

{items}
"""


CONTROL_RE = re.compile(r"\\[A-Za-z]+")


POST_REPLACEMENTS = {
    "贝塔": "BETA",
    "蜂巢": "HIVE",
    "海夫": "HIVE",
    "战术表面战斗机": "战术机",
    "战术地面战斗机": "战术机",
    "美园": "美樱乃",
    "美樱乃静": "美樱乃雫",
    "仙道": "千堂",
    "立浪": "龙浪",
    "龙波": "龙浪",
    "麻理茂": "麻理茉",
    "马里莫": "麻理茉",
    "艾斯": "艾斯",
}


def strip_controls(text: str) -> str:
    text = text or ""
    text = text.replace("\\n", " ")
    text = CONTROL_RE.sub("", text)
    text = text.replace("　", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_zh(text: str, jp: str) -> str:
    text = (text or "").strip()
    text = text.strip(" \t\r\n\"“”")
    for src, dst in POST_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = re.sub(r"\s+([，。！？；：、」])", r"\1", text)
    text = re.sub(r"([「（])\s+", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    jp_clean = strip_controls(jp)
    if jp_clean.startswith("「") and jp_clean.endswith("」"):
        text = text.strip("「」")
        text = f"「{text}」"
    return text


def load_existing(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("id") and row.get("zh_deepseek"):
                key = f"{row.get('file','')}::{row['id']}"
                result[key] = row["zh_deepseek"]
    return result


def call_deepseek(api_key: str, model: str, items: list[dict[str, str]], timeout: int) -> list[dict[str, str]]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(items=json.dumps(items, ensure_ascii=False))},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
    body = json.loads(raw)
    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return parsed["items"]


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate TDA CSV rows with DeepSeek.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not set")

    rows = list(csv.DictReader(args.input.open(encoding="utf-8-sig", newline="")))
    if args.limit:
        rows = rows[: args.limit]

    existing = load_existing(args.output)
    fieldnames = list(rows[0].keys()) if rows else []
    if "zh_deepseek" not in fieldnames:
        fieldnames.append("zh_deepseek")
    for row in rows:
        row.setdefault("zh_deepseek", "")
        key = f"{row.get('file','')}::{row['id']}"
        if key in existing:
            row["zh_deepseek"] = existing[key]

    total = len(rows)
    done = sum(1 for r in rows if r.get("zh_deepseek"))
    print(f"start rows={total} already_done={done} model={args.model}", flush=True)

    cursor = 0
    while cursor < total:
        batch_rows: list[dict[str, str]] = []
        while cursor < total and len(batch_rows) < args.batch_size:
            row = rows[cursor]
            cursor += 1
            if row.get("zh_deepseek"):
                continue
            batch_rows.append(row)
        if not batch_rows:
            continue

        request_items = [
            {
                "id": row["id"],
                "jp": strip_controls(row.get("jp", "")),
                "en": strip_controls(row.get("en", "")),
            }
            for row in batch_rows
        ]

        for attempt in range(1, 5):
            try:
                translated = call_deepseek(api_key, args.model, request_items, args.timeout)
                by_id = {item["id"]: item.get("zh", "") for item in translated}
                for row in batch_rows:
                    row["zh_deepseek"] = normalize_zh(by_id.get(row["id"], ""), row.get("jp", ""))
                break
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
                KeyError,
                http.client.IncompleteRead,
                ConnectionError,
            ) as exc:
                print(f"batch failed attempt={attempt} cursor={cursor} err={exc!r}", flush=True)
                if attempt == 4:
                    raise
                time.sleep(2 * attempt)

        done = sum(1 for r in rows if r.get("zh_deepseek"))
        print(f"progress {done}/{total}", flush=True)
        write_rows(args.output, fieldnames, rows)
        if args.sleep:
            time.sleep(args.sleep)

    write_rows(args.output, fieldnames, rows)
    print(f"done output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
