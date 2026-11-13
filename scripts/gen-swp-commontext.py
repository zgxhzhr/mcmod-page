#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple Wooden Pipes（classId 15375）通用文本方案。

8 条管道正文每条 320 字符，其中约 240 字符（75%）八条完全相同：
连接规则、活塞提取方向、传输速率。真正有差异的只有木材名与耐高温两处。

所以建一条通用文本「管道」承接共通说明，8 条只写自己独有的数据。
泵只有 1 条，不引用通用文本。
"""
import json
import random
import re
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "swp-物品导入-15375.json"
OUT_ITEMS = BASE / "swp-物品导入-15375.json"
OUT_COMMON = BASE / "swp-通用文本-15375.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

COMMON_HTML = (
    "<p>这些方块是 Simple Wooden Pipes 添加的木制流体管道。</p>"
    "<p><strong>连接</strong>：自动与相邻的管道、泵或容器对接，"
    "六个方向各自独立判断，不需要调整朝向。</p>"
    "<p><strong>提取方向</strong>：手持活塞对某一面右键，可把该面设为流体的提取端；"
    "Shift + 右键取消设定，活塞退还。因此同一根管道可以只有一端抽取、其余端输送，"
    "不需要额外区分输入管与输出管。</p>"
    "<p><strong>传输速率</strong>：默认 50，写在配置文件的 transferRate 项里。"
    "管道内部容量默认 1000，同样可配置。</p>"
    "<p><strong>木材</strong>：八种木材各有对应管道，材质取自原版木板，"
    "外观能与原版建筑直接贴合。</p>"
    "<p><strong>温度限制</strong>：绯红木与诡异木耐高温，可输送岩浆、熔融金属等流体；"
    "其余六种为普通木材，通入高温流体会被破坏。</p>"
)


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    # 1) 通用文本
    common = [{
        "id": "common_pipe",
        "name": "管道",
        "ename": "Pipe",
        "regname": "",
        "category": "{文本}",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Simple Wooden Pipes 通用文本：本条不针对具体木材，"
            "用于承接八种管道的共通说明，供各管道页在附言中引用。"
            f"{tail()}"
        ),
        "html": COMMON_HTML,
        "icon32": "",
        "icon128": "",
    }]
    OUT_COMMON.write_text(json.dumps(common, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) 管道页正文压到只写独有数据
    changed = 0
    for r in rows:
        if r["category"] != "管道":
            continue
        # 从原正文里抽「材质」与「耐高温」两项
        m_zh = re.search(r"材质为([^。]+)。", r["html"])
        zh = m_zh.group(1) if m_zh else ""
        hot = "可以输送岩浆、熔融金属等高温流体。" in r["html"]
        temp = ("<p><strong>耐高温</strong>：是。绯红木属下界木材，可输送岩浆、熔融金属等高温流体。</p>"
                if hot else
                "<p><strong>耐高温</strong>：否。属普通木材，通入岩浆这类流体会被破坏。</p>")
        r["html"] = (
            f"<p><strong>材质</strong>：{zh}。</p>"
            + temp
        )
        r["remark"] = (
            "Simple Wooden Pipes 资料页：名称取自 lang/en_us.json。"
            "通用说明需引用通用文本「管道」。"
            f"{tail()}"
        )
        changed += 1

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"通用文本 {len(common)} 条 → {OUT_COMMON.name}  ({OUT_COMMON.stat().st_size/1024:.1f} KB)")
    print(f"物品页 {len(rows)} 条 → {OUT_ITEMS.name}  ({OUT_ITEMS.stat().st_size/1024:.1f} KB)")
    print(f"  管道页改写 {changed} 条")
    print("\n  管道页新正文（抽样）:")
    for r in rows[:2]:
        print(f"    [{r['name']}]")
        print(f"      {r['html']}")
    print("\n  泵（不引用）:")
    pump = [r for r in rows if r["category"] == "泵"][0]
    print(f"    [{pump['name']}] {len(pump['html'])} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
