#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exline's Awnings（classId 28508）资料页 —— 按「综合」交付。

21 个方块：11 种木材的木板版 + 10 种木材的原木版（竹子无原木版）。
主名各不相同（Oak Awning / Birch Awning…），但正文几乎完全一样——
形状、放置方式、含水、拼接规则全部一致，只有材质不同。

按 §6.1.10 判定「条目 ≥10 且整页重复 → 综合」：
  抽象父资料：遮阳棚（1 条）
  子资料：21 个变体（html 留空，等站方综合后引用父资料）
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
EA = BASE / "ea/assets/exlineawnings"
ICONS128 = BASE / "ea-icons128"
ICONS32 = BASE / "ea-icons32"
OUT_PARENT = BASE / "ea-父资料-28508.json"
OUT_CHILD = BASE / "ea-子资料-28508.json"
OUT_APPLY = BASE / "ea-综合申请-28508.md"
NS = "exlineawnings"

_PAW = ["呜喵", "喵呜", "喵喵"]

WOOD_ZH = {
    "acacia": "金合欢", "bamboo": "竹", "birch": "白桦", "cherry": "樱花",
    "crimson": "绯红", "dark_oak": "深色橡木", "jungle": "丛林",
    "mangrove": "红树", "oak": "橡木", "spruce": "云杉", "warped": "诡异",
}


def b64(path: Path):
    if not path.exists():
        return ""
    buf = io.BytesIO()
    Image.open(path).convert("RGBA").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    zh = json.loads((EA / "lang/en_us.json").read_text(encoding="utf-8"))
    ids = [p.stem for p in sorted((EA / "blockstates").glob("*.json"))]

    planks_ids = [i for i in ids if not i.endswith("_log_awning")]
    log_ids = [i for i in ids if i.endswith("_log_awning")]

    parent_html = (
        "<p>遮阳棚是 Exline's Awnings 添加的装饰性方块，斜向的棚面由支架撑起，"
        "贴在建筑外墙做遮阳的造型。</p>"

        "<p><strong>两种材质</strong>：每种木材各有木板版与原木版。"
        "木板版的支架用细木条，原木版用整根原木，两者棚面相同，区别在支撑结构。"
        "共二十一种：十一种木材的木板版，十种木材的原木版——竹子没有原木，所以少一种。</p>"

        "<table><thead><tr><th>材质</th><th>数量</th><th>支架外观</th></tr></thead><tbody>"
        "<tr><td>木板版</td><td>11</td><td>细木条</td></tr>"
        "<tr><td>原木版</td><td>10</td><td>整根原木（绯红与诡异为菌柄）</td></tr>"
        "</tbody></table>"

        "<p><strong>放置</strong>：与楼梯一致——有朝向、上下两半，"
        "以及直形、内角、外角三种形状。连续摆放转角处会自动拼接成 L 形，"
        "与楼梯的拼接规则相同。</p>"

        "<p><strong>含水</strong>：可以含水，放在水边或水下不会阻断水流。</p>"

        "<p><strong>获取与堆叠</strong>：在工作台合成，可堆叠 64 个。"
        "具体配方随木材种类变化，在游戏内查看。</p>"
    )

    parent = [{
        "id": "awning",
        "name": "遮阳棚",
        "ename": "Awning",
        "regname": "",
        "category": "装饰方块",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Exline's Awnings 抽象父资料（综合用）：方块数量与木材清单取自 "
            "assets/exlineawnings/blockstates，放置属性取自 AwningBlock 的 FACING / HALF / SHAPE / "
            "WATERLOGGED 四个状态，材质区分取自 lang/en_us.json。"
            f"{tail()}"
        ),
        "html": parent_html,
        "icon32": b64(ICONS32 / f"{NS}__block_oak_awning.png"),
        "icon128": b64(ICONS128 / f"{NS}__block_oak_awning.png"),
    }]
    OUT_PARENT.write_text(json.dumps(parent, ensure_ascii=False, indent=2), encoding="utf-8")

    # 子资料
    children = []
    for bid in ids:
        en = zh.get(f"block.{NS}.{bid}", bid)
        # 该模组没有中文语言文件（lang 下只有 en_us.json），
        # 所以主名用英文原名、次要名留空，不自译。
        core = bid.replace("_awning", "")
        is_log = core.endswith("_log")
        wood = core[:-4] if is_log else core
        wood_zh = WOOD_ZH.get(wood, wood)
        stem_zh = ("菌柄" if wood in ("crimson", "warped") else "原木") if is_log else "木板"
        children.append({
            "id": bid,
            "name": en,
            "ename": "",
            "regname": f"{NS}:{bid}",
            "category": "装饰方块",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                f"Exline's Awnings 子资料（待综合）：方块 id 为 {NS}:{bid}，"
                f"英文名取自 lang/en_us.json，材质为{wood_zh}{'原木' if is_log else '木板'}。"
                "正文由父资料「遮阳棚」统一提供，本条不单独撰写。"
                f"{tail()}"
            ),
            "html": "",
            "icon32": b64(ICONS32 / f"{NS}__block_{bid}.png"),
            "icon128": b64(ICONS128 / f"{NS}__block_{bid}.png"),
        })
    OUT_CHILD.write_text(json.dumps(children, ensure_ascii=False, indent=2), encoding="utf-8")

    # 申请
    apply_md = f"""# Exline's Awnings（28508）综合申请

## 申请内容

功能：综合

抽象父资料：**遮阳棚**（本次提交，id `awning`）

子资料：共 {len(children)} 条，见 `ea-子资料-28508.json`。

## 申请理由

依据主站编辑规范第 33 条：多个同类资料的相互文本重复率较高时，应使用「综合」功能创建父资料。

1. **{len(children)} 个方块的介绍几乎完全一样**。它们共用同一套机制——斜棚面 + 支架，
   放置规则与楼梯相同（朝向、上下半、直/内角/外角），可含水，堆叠 64。
   逐条写等于把同一段话复制 {len(children)} 遍。
2. **差异只在材质**。木板版与原木版的区别是支架用细木条还是整根原木；
   同材质内不同木材的区别只是贴图颜色。
3. **数量在综合的适用范围内**（最少 2、最多不宜超过 450）。

## 子资料构成

| 材质 | 数量 | 木材 |
|---|---|---|
| 木板版 | {len(planks_ids)} | {'、'.join(WOOD_ZH.get(i.replace('_awning',''), i) for i in planks_ids)} |
| 原木版 | {len(log_ids)} | {'、'.join(WOOD_ZH.get(i.replace('_log_awning',''), i) for i in log_ids)} |

竹子只有木板版——原版竹子没有原木形态，所以总数是 11 + 10 = {len(children)}。

## 提交顺序

1. 本文件（父资料 `awning`）先提交；
2. 审核通过、拿到父资料 URL 后，由管理协助把 `ea-子资料-28508.json` 里的 {len(children)} 条
   合并到父资料下。

## 附注

子资料的图标已各自渲染（每个木材纹理不同），不需要额外处理。
"""
    OUT_APPLY.write_text(apply_md, encoding="utf-8")

    print(f"父资料 1 条 → {OUT_PARENT.name}  ({OUT_PARENT.stat().st_size/1024:.1f} KB)")
    print(f"子资料 {len(children)} 条 → {OUT_CHILD.name}  ({OUT_CHILD.stat().st_size/1024:.1f} KB)")
    print(f"综合申请 → {OUT_APPLY.name}  ({OUT_APPLY.stat().st_size/1024:.1f} KB)")
    print(f"\n木板版 {len(planks_ids)} / 原木版 {len(log_ids)}")
    print(f"父资料正文 {len(parent_html)} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
