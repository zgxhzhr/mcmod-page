#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crafting Dead: Survival（classId 4397）通用文本方案改造。

做三件事：
  1. 生成 3 条「通用文本」资料（食物 / 饮品 / 容器）
     资料分类填 {文本}，正文写整族共通的说明
  2. 把 70 条食物/饮品/容器的正文压缩成「只写独有数据」
  3. 附言统一写上「通用说明需引用通用文本『XX』」

这么做的原因：70 条里只有 8 种正文结构，43 条完全同构。
"""
import json
import random
import re
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "cds-重建-食物-4397.json"
OUT_ITEMS = BASE / "cds-重建-食物-4397.json"
OUT_COMMON = BASE / "cds-通用文本-4397.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# ── 三条通用文本 ──
COMMON = [
    {
        "id": "common_unopened_can",
        "name": "未开封罐头",
        "ename": "Unopened Can",
        "regname": "",
        "category": "{文本}",
        "type": "物品/方块",
        "maxstack": 3,
        "html": (
            "<p>这些物品是未开封的罐头，不能直接食用。</p>"
            "<p><strong>获取</strong>：从各类战利品容器中搜到。</p>"
            "<p><strong>用法</strong>：在工作台与开罐器无序合成，变成对应的开封版本后才能吃。"
            "每个开罐器可用 8 次，用完即损坏。</p>"
            "<p><strong>堆叠</strong>：三个一组。</p>"
            "<p><strong>对应关系</strong>：每种未开封罐头都对应一种开封版本，"
            "例如豆子罐头对应开封的豆子罐头。</p>"
        ),
    },
    {
        "id": "common_food",
        "name": "食物",
        "ename": "Food",
        "regname": "",
        "category": "{文本}",
        "type": "物品/方块",
        "maxstack": 64,
        "html": (
            "<p>这些物品是模组中的食物，食用后恢复饥饿值与饱和度。</p>"
            "<p><strong>属性</strong>：每条食物页列出该物品的饥饿值与饱和度两项数值。"
            "饥饿值决定恢复多少饥饿条，饱和度决定恢复后饥饿条下降的速度——"
            "饱和度越高，饱腹感持续越久。</p>"
            "<p><strong>获取</strong>：从民用战利品、稀有民用战利品、医疗战利品、"
            "警用战利品与军用战利品等容器中搜到，也可以在创造模式的物品栏里直接取得。</p>"
            "<p><strong>堆叠</strong>：多数食物可堆叠，具体上限见各页的堆叠数量。</p>"
        ),
    },
    {
        "id": "common_drink",
        "name": "饮品",
        "ename": "Drink",
        "regname": "",
        "category": "{文本}",
        "type": "物品/方块",
        "maxstack": 64,
        "html": (
            "<p>这些物品是模组中的饮品，只能补充水分，不能充饥。</p>"
            "<p><strong>属性</strong>：每条饮品页列出该物品的补水量。"
            "本模组的饮品不提供饥饿值与饱和度。</p>"
            "<p><strong>容器</strong>：喝完会留下对应的空容器。空容器可以在水源处重新灌装，"
            "变回满版本。</p>"
            "<p><strong>获取</strong>：从民用战利品、稀有民用战利品、医疗战利品、"
            "警用战利品与军用战利品等容器中搜到，也可以在创造模式的物品栏里直接取得。</p>"
        ),
    },
    {
        "id": "common_container",
        "name": "空容器",
        "ename": "Empty Container",
        "regname": "",
        "category": "{文本}",
        "type": "物品/方块",
        "maxstack": 64,
        "html": (
            "<p>这些物品是饮品喝完后留下的空容器。</p>"
            "<p><strong>获取</strong>：喝完对应的饮品后自动留下，也可从战利品容器中搜到。</p>"
            "<p><strong>用途</strong>：在水源处右键可以重新灌装，变回对应的满版本。</p>"
            "<p><strong>对应关系</strong>：每种空容器都对应一种饮品，"
            "例如空水瓶对应水瓶、空可乐瓶对应可乐瓶。</p>"
        ),
    },
]


def strip_to_own_data(html: str, cat: str) -> str:
    """把正文压到只剩这条自己的数据。

    食物：只留属性行（有饥饿值/饱和度）
    饮品：只留补水量
    容器：什么都不留（全部是通用内容）
    """
    if cat == "容器":
        return ""
    # 未开封罐头没有饥饿值，正文全是通用说明（开罐器机制），归到「未开封罐头」通用文本
    if "未开封" in (html[:40]):
        return ""

    # 抽属性行
    m = re.search(r"<strong>属性</strong>：([^<]+)", html)
    if not m:
        return ""

    attr = m.group(1).strip()
    # 去掉尾部句号后重组
    attr = attr.rstrip("。")
    return f"<p><strong>属性</strong>：{attr}。</p>"


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    # 1) 通用文本
    common_rows = []
    for c in COMMON:
        common_rows.append({
            "id": c["id"],
            "name": c["name"],
            "ename": c["ename"],
            "regname": c["regname"],
            "category": c["category"],
            "type": c["type"],
            "maxstack": c["maxstack"],
            "remark": (
                "Crafting Dead: Survival 通用文本：本条不针对具体物品，"
                "用于承接同类条目的共通说明，供其余页面在附言中引用。"
                f"{tail()}"
            ),
            "html": c["html"],
            "icon32": "",
            "icon128": "",
        })
    OUT_COMMON.write_text(json.dumps(common_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) 压缩正文
    COPY = {"食物": "食物", "饮品": "饮品", "容器": "空容器"}

    def ref_of(r):
        """这条该引用哪条通用文本。"""
        if "未开封的罐头" in r["html"][:30]:
            return "未开封罐头"
        return COPY.get(r["category"])
    changed = 0
    for r in rows:
        cat = r["category"]
        if cat not in COPY:
            continue
        old = r["html"]
        new = strip_to_own_data(old, cat)
        if new == old:
            continue
        r["html"] = new
        ref = ref_of(r)
        if not ref:
            continue
        r["remark"] = (
            "Crafting Dead: Survival 资料页：中文名取自 lang/zh_cn.json，"
            f"本条正文仅列出该物品的独有数据，通用说明需引用通用文本「{ref}」。"
            + tail()
        )
        changed += 1

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"通用文本 {len(common_rows)} 条 → {OUT_COMMON.name}  ({OUT_COMMON.stat().st_size/1024:.1f} KB)")
    for c in common_rows:
        print(f"    {c['name']:<8} / {c['ename']:<16} 分类={c['category']}")
    print(f"\n物品页改造 {changed} 条 → {OUT_ITEMS.name}  ({OUT_ITEMS.stat().st_size/1024:.1f} KB)")

    from collections import Counter
    print(f"  分类: {dict(Counter(r['category'] for r in rows))}")
    print(f"  有正文: {sum(1 for r in rows if r['html'])}/{len(rows)}")
    print("\n  抽样：")
    for r in rows[:3] + [x for x in rows if x["category"] == "食物"][:2]:
        print(f"    [{r['name']}] {r['html'][:90] if r['html'] else '（空）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
