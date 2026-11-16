#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tax' Village Architect（classId 15261）自然生成页 —— 7 页。

  1. 平原村庄      2. 沙漠村庄      3. 热带草原村庄
  4. 雪地村庄      5. 针叶林村庄    6. 樱花村庄（新增）
  7. 掠夺者前哨站

数据来自 tva-structures.json（296 个 nbt 的解析结果）。
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
DATA = json.loads((BASE / "tva-structures.json").read_text(encoding="utf-8"))
OUT = BASE / "tva-自然生成-15261.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def fmt(n: int) -> str:
    return f"{n:,}"


KIND_ZH = {
    "houses": "房屋", "streets": "街道", "decor": "装饰",
    "town_centers": "中心广场", "terminators": "尽头",
    "villagers": "村民", "animals": "动物", "cats": "猫",
    "iron_golem": "铁傀儡", "camel": "骆驼",
}

VILLAGES = [
    ("plains", "平原村庄", "minecraft/plains",
     "平原村庄是最常见的一种，也是六种里方块总量最大的（一万八千余个）。"
     "房屋 21 种、街道 9 种，还包含一个平原专属的渔夫小屋（plains_fisher）。"),
    ("desert", "沙漠村庄", "minecraft/desert",
     "沙漠村庄的房屋种类最多，达 25 种，但整体方块量只有八千余个，是六种里最少的一组。"
     "房屋多而体量小，村庄铺得更开。这一组还有专用的骆驼部件。"),
    ("savanna", "热带草原村庄", "minecraft/savanna",
     "热带草原村庄的结构数量最少（35 个），但中心广场有 4 种，是六种里中心变体最多的一组。"),
    ("snowy", "雪地村庄", "minecraft/snowy",
     "雪地村庄的街道种类最多，达 15 种，房屋 23 种。"
     "平均高度只有 8.1 格，是六种村庄里建筑最矮的一组。"),
    ("taiga", "针叶林村庄", "minecraft/taiga",
     "针叶林村庄房屋 22 种、街道 9 种，平均高度 11.3 格，建筑偏高。"
     "装饰件有 5 种，是原版五种村庄里装饰最丰富的一组。"),
    ("cherry", "樱花村庄", "brutos/cherry",
     "樱花村庄是本模组新增的品种，原版没有。结构数 44 个，平均高度 12.8 格，"
     "是六种村庄里最高的。房屋 19 种、装饰 11 种，装饰件数量为六种之最。"
     "它使用独立的 brutos 命名空间，不与原版村庄共用部件。"),
]

MISC = [
    ("pillager_outpost", "掠夺者前哨站", "minecraft/pillager_outpost",
     "重做后的前哨站共 25 个部件：七种帐篷（tent_1 到 tent_7）、一座瞭望塔、"
     "一辆货车，以及多种铁笼——关押村民的、关押悦灵的、破损状态的各有版本。"
     "另有靶标、木板与木桩等散件。"),
    ("common", "村庄通用部件", "minecraft/common",
     "各村庄共用的生物部件，包括 10 种猫、9 种动物与 1 个铁傀儡。"
     "这些部件不构成建筑，只决定村庄生成时附带哪些生物。"),
]


def page_of(key: str, title: str, data_key: str, desc: str) -> dict:
    d = DATA.get(data_key, {})
    kinds = d.get("kinds", {})
    rows = "".join(
        f"<tr><td>{KIND_ZH.get(k, k)}</td><td>{v}</td></tr>"
        for k, v in sorted(kinds.items(), key=lambda x: -x[1])
        if k in KIND_ZH
    )

    html = [f"<p>{desc}</p>"]
    html.append(
        "<table><thead><tr><th>项目</th><th>数值</th></tr></thead><tbody>"
        f"<tr><td>结构部件总数</td><td>{d.get('count', 0)}</td></tr>"
        f"<tr><td>实心方块合计</td><td>{fmt(d.get('total_solid', 0))}</td></tr>"
        f"<tr><td>平均结构高度</td><td>{d.get('avg_height', 0)} 格</td></tr>"
        "</tbody></table>"
    )
    if rows:
        html.append(f"<p><strong>部件构成</strong>：</p><table><thead><tr><th>部件类型</th>"
                    f"<th>数量</th></tr></thead><tbody>{rows}</tbody></table>")
    html.append("<p><strong>生成</strong>：使用 jigsaw 拼图结构，以随机组合的方式拼成村庄，"
                "每次生成的布局都不相同。村庄的生成生物群系由原版对应的 has_structure 标签决定。</p>")

    return {
        "id": f"village_{key}" if key not in ("common", "pillager_outpost") else key,
        "name": title,
        "ename": "",
        "regname": "",
        "category": "结构",
        "type": "自然生成",
        "maxstack": 64,
        "remark": (
            "Tax' Village Architect 新增自然生成页：部件数量、实心方块数与平均高度"
            "由 data 下对应目录的 nbt 文件解析得出。"
            f"{tail()}"
        ),
        "html": "".join(html),
        "icon32": "",
    }


def main() -> int:
    rows = [page_of(k, t, dk, desc) for k, t, dk, desc in VILLAGES]
    rows += [page_of(k, t, dk, desc) for k, t, dk, desc in MISC]

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    for r in rows:
        print(f"  {r['name']:<16} 正文 {len(r['html']):>5} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
