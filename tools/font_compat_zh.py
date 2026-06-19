from __future__ import annotations

import argparse
import csv
from pathlib import Path


PHRASES = {
    "这里": "此処",
    "这边": "此方",
    "这个": "此個",
    "这种": "此種",
    "这样": "此様",
    "这么": "如此",
    "这些": "此等",
    "这次": "此次",
    "这是": "此是",
    "这下": "此下",
    "什么": "何",
    "怎么": "如何",
    "为什么": "為何",
    "怎么样": "如何",
    "没办法": "没法子",
    "总统": "大統領",
    "总统夫人": "大統領夫人",
    "发现": "発見",
    "确定": "確定",
    "确认": "確認",
    "尸体": "遺体",
    "遗体": "遺体",
    "战术机": "戦術機",
    "战斗": "戦闘",
    "战争": "戦争",
    "光线级": "光線級",
    "重光线级": "重光線級",
    "突击级": "突撃級",
    "要击级": "要撃級",
    "战车级": "戦車級",
    "士兵级": "兵士級",
    "斗士级": "闘士級",
    "母舰级": "母艦級",
    "战线": "戦線",
    "军队": "軍隊",
    "美樱乃": "美桜乃",
    "美樱乃雫": "美桜乃雫",
    "神宫司": "神宮司",
    "神宫司麻理茉": "神宮司麻理茉",
    "龙浪": "龍浪",
    "响": "響",
    "艾伦": "艾倫",
    "西雅图": "西雅図",
    "北美": "北米",
    "大海崩": "大海崩",
    "美国": "米国",
    "法国": "仏国",
    "加拿大": "加国",
    "日本帝国": "日本帝国",
    "帝国": "帝国",
}


CHARS = {
    "这": "此",
    "说": "説",
    "们": "等",
    "为": "為",
    "战": "戦",
    "还": "還",
    "队": "隊",
    "过": "過",
    "现": "現",
    "发": "発",
    "后": "後",
    "无": "無",
    "让": "譲",
    "觉": "覚",
    "经": "経",
    "击": "撃",
    "听": "聴",
    "线": "線",
    "确": "確",
    "给": "給",
    "进": "進",
    "厂": "廠",
    "题": "題",
    "总": "総",
    "绝": "絶",
    "备": "備",
    "术": "術",
    "产": "産",
    "樱": "桜",
    "级": "級",
    "伦": "倫",
    "见": "見",
    "连": "連",
    "务": "務",
    "设": "設",
    "记": "記",
    "错": "錯",
    "类": "類",
    "并": "並",
    "报": "報",
    "东": "東",
    "强": "強",
    "传": "伝",
    "响": "響",
    "许": "許",
    "龙": "龍",
    "变": "変",
    "样": "様",
    "对": "対",
    "实": "実",
    "该": "該",
    "请": "請",
    "认": "認",
    "应": "応",
    "从": "従",
    "卫": "衛",
    "谢": "謝",
    "长": "長",
    "况": "況",
    "于": "於",
    "虽": "雖",
    "须": "須",
    "边": "辺",
    "敌": "敵",
    "联": "聯",
    "办": "辦",
    "宫": "宮",
    "国": "国",
    "军": "軍",
    "机": "機",
    "开": "開",
    "关": "関",
    "吗": "か",
    "么": "麼",
    "诶": "欸",
    "呜": "嗚",
    "吗": "か",
    "吗": "か",
}


def convert(text: str) -> str:
    if not text:
        return text
    for src, dst in sorted(PHRASES.items(), key=lambda kv: len(kv[0]), reverse=True):
        text = text.replace(src, dst)
    return "".join(CHARS.get(ch, ch) for ch in text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Simplified Chinese subtitles to Japanese-font-compatible glyphs.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--column", default="zh_deepseek")
    args = parser.parse_args()

    rows = list(csv.DictReader(args.input.open(encoding="utf-8-sig", newline="")))
    fieldnames = list(rows[0].keys()) if rows else []
    for row in rows:
        row[args.column] = convert(row.get(args.column, ""))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"done rows={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
