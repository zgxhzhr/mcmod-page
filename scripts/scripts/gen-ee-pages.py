#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Environmental Energy（classId 4236）26 个页面的批量编辑 JSON。

页面构成：
  太阳能电池 ×8     472119-472126
  太阳能发电机控制器 ×8  472127-472134
  避雷针 / 绝缘避雷针  472135 / 472136
  避雷针控制器 ×8   472137-472144

数据来源：官方 Wiki（wiki.teamkrypticlink.com/books/environmental-energy-3-wiki）
——电池效率与板最高效率两张表都来自 Solar Cells / Solar Panels 页面。
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
OUT = BASE / "ee-编辑-4236.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# 等级：中文, 英文, 电池效率, 板最高效率
TIERS = [
    ("莱泽尔", "Litherite", 0.30, 0.56),
    ("艾洛蒂", "Erodium",   0.46, 0.64),
    ("凯罗尼", "Kyronite",  0.60, 0.72),
    ("普雷蒂", "Pladium",   0.72, 0.80),
    ("艾恩尼", "Ionite",    0.82, 0.88),
    ("以太",   "Aethium",   0.90, 0.96),
    ("纳诺莱", "Nanorite",  0.96, 1.00),
    ("泽洛斯", "Xerothium", 1.00, 1.00),
]

TIER_IDS = {
    "cell": ["472119", "472120", "472121", "472122", "472123", "472124", "472125", "472126"],
    "panel": ["472127", "472128", "472129", "472130", "472131", "472132", "472133", "472134"],
    "rod": ["472137", "472138", "472139", "472140", "472141", "472142", "472143", "472144"],
}


def cell_html(zh: str, en: str, eff: float) -> str:
    pct = f"{eff * 100:.0f}%"
    return (
        f"<p>{zh}太阳能电池（{en} Solar Cell）是 Environmental Energy 中添加的太阳能板组件，"
        f"八个等级中的第 {[t[0] for t in TIERS].index(zh) + 1} 档。</p>"
        f"<p><strong>效率倍率</strong>：{eff:.2f}（{pct}）。同系列电池从 0.30 递增到 1.00，本档位于其中。</p>"
        "<p><strong>用法</strong>：装入太阳能板多方块结构中提供效率加成。任意等级的电池都可以装到任意等级的板上，"
        "不受等级限制。</p>"
        "<p><strong>实际效率</strong>：取电池效率与太阳能板最高效率中较低的一方。"
        "把低档电池装到高档板上，输出仍以电池为限；反过来高档电池装到低档板上，则受板的上限约束。</p>"
        "<p><strong>获取</strong>：由对应等级的材料合成，材料链来自环境科技系列。</p>"
    )


def panel_html(zh: str, en: str, max_eff: float) -> str:
    pct = f"{max_eff * 100:.0f}%"
    return (
        f"<p>{zh}太阳能发电机控制器（{en} Solar Panel Controller）是 Environmental Energy 中"
        f"太阳能板多方块结构的核心方块，八级中的第 {[t[0] for t in TIERS].index(zh) + 1} 档。</p>"
        f"<p><strong>最高效率</strong>：{max_eff:.2f}（{pct}）。这是该等级太阳能板能发挥的效率上限，"
        "实际产出还要看装入的太阳能电池等级。</p>"
        "<p><strong>多方块结构</strong>：控制器周围需要搭建框架与太阳能电池，具体形状见模组内说明。"
        "结构建成后由控制器统筹发电与输出。</p>"
        "<p><strong>采光要求</strong>：不需要每块电池都暴露在天空下。被不透光方块覆盖的电池不发电，"
        "其余仍正常工作；上方加盖玻璃不影响发电。</p>"
        "<p><strong>修正器</strong>：默认装的是空修正器。替换为 Piezo 修正器后，"
        "面板在雨天与雷雨天也能发电。</p>"
        "<p><strong>输出</strong>：IO 槽位中只有 FE 输出块有实际作用。输出块本身可升级，"
        "等级不足时产能无法完全导出。</p>"
    )


def rod_ctrl_html(zh: str, en: str) -> str:
    return (
        f"<p>{zh}避雷针控制器（{en} Lightning Rod Controller）是 Environmental Energy 中"
        f"避雷针多方块结构的核心方块，八级中的第 {[t[0] for t in TIERS].index(zh) + 1} 档。</p>"
        "<p><strong>核心机制</strong>：雷击时瞬间产出大量能量。任何天气下都可能被雷击，"
        "但雨天与雷雨天的概率显著更高，因此建在多雨生物群系效率更好。</p>"
        "<p><strong>采光要求</strong>：多方块结构需要露天才能运作。</p>"
        "<p><strong>修正器</strong>：可装 Radiant（晴天被动发电少量能量）或 Electrostatic"
        "（雨天与雷雨天被动发电），把结构从依赖雷击转为稳定电力来源。</p>"
        "<p><strong>输出</strong>：雷击能量极大，缓冲会被瞬间灌满。FE 输出块等级不足时能量导不出去，"
        "会卡在缓冲区浪费，因此对输出等级的要求高于太阳能板。</p>"
    )


ROD_HTML = {
    "472135": (
        "<p>避雷针是 Environmental Energy 中添加的吸引雷电的方块，用于搭建避雷针多方块结构。</p>"
        "<p><strong>作用</strong>：吸引雷击并将能量导入结构中的控制器。雷击不仅带来电力，"
        "也可能对附近的实体造成伤害。</p>"
        "<p><strong>天气条件</strong>：任何天气都可能被雷击，雨天与雷雨天概率更高。</p>"
        "<p><strong>与绝缘避雷针的区别</strong>：普通避雷针会传导雷击伤害；"
        "绝缘避雷针在保留引雷功能的同时做了防护处理，适合建在基地内部或人员经常经过的位置。</p>"
        "<p><strong>搭建</strong>：与对应等级的避雷针控制器组合成多方块结构，需露天放置。</p>"
    ),
    "472136": (
        "<p>绝缘避雷针是 Environmental Energy 中添加的避雷针变体，在引雷的同时做了绝缘处理。</p>"
        "<p><strong>作用</strong>：同样用于避雷针多方块结构，吸引雷击并将能量导入控制器。</p>"
        "<p><strong>绝缘的意义</strong>：普通避雷针在雷击时可能对附近实体造成伤害；"
        "绝缘版保住了引雷与发电的功能，同时避免这类附带伤害，适合建在基地内部或人员活动的区域。</p>"
        "<p><strong>天气条件</strong>：任何天气都可能被雷击，雨天与雷雨天概率更高。</p>"
        "<p><strong>搭建</strong>：与对应等级的避雷针控制器组合成多方块结构，需露天放置。</p>"
    ),
}


def main() -> int:
    rows = []

    # 太阳能电池 8
    for i, (zh, en, eff, _) in enumerate(TIERS):
        rows.append({
            "id": TIER_IDS["cell"][i],
            "name": f"{zh}太阳能电池",
            "editRemark": (
                f"补全正文：效率倍率 {eff} 取自官方 Wiki 的 Solar Cells 页面，"
                "电池与太阳能板的搭配规则与效率取低值的机制同样依据该页。"
                f"{tail()}"
            ),
            "editNote": f"补全正文：效率倍率 {eff}、可跨等级搭配、实际效率取两者较低值。",
            "html": cell_html(zh, en, eff),
        })

    # 太阳能控制器 8
    for i, (zh, en, _, maxeff) in enumerate(TIERS):
        rows.append({
            "id": TIER_IDS["panel"][i],
            "name": f"{zh}太阳能发电机控制器",
            "editRemark": (
                f"补全正文：最高效率 {maxeff} 取自官方 Wiki 的 Solar Panels 页面，"
                "采光规则、Piezo 修正器与 FE 输出块机制同样依据该页。"
                f"{tail()}"
            ),
            "editNote": f"补全正文：最高效率 {maxeff}、采光要求、修正器与输出机制。",
            "html": panel_html(zh, en, maxeff),
        })

    # 避雷针 2
    for rid, name in (("472135", "避雷针"), ("472136", "绝缘避雷针")):
        rows.append({
            "id": rid,
            "name": name,
            "editRemark": (
                "补全正文：作用与天气机制取自官方 Wiki 的 Lightning Rods 页面，"
                "与绝缘版的区别依据两个方块的设定差异。"
                f"{tail()}"
            ),
            "editNote": "补全正文：引雷与发电作用、天气条件、与另一变体的区别。",
            "html": ROD_HTML[rid],
        })

    # 避雷针控制器 8
    for i, (zh, en, _, _) in enumerate(TIERS):
        rows.append({
            "id": TIER_IDS["rod"][i],
            "name": f"{zh}避雷针控制器",
            "editRemark": (
                "补全正文：雷击发电机制、两种修正器与输出等级要求取自官方 Wiki 的 Lightning Rods 页面。"
                f"{tail()}"
            ),
            "editNote": "补全正文：雷击发电、Radiant 与 Electrostatic 修正器、输出等级要求。",
            "html": rod_ctrl_html(zh, en),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("页面:", dict(Counter("太阳能电池" if "电池" in r["name"] else
                               "太阳能控制器" if "太阳能发电机" in r["name"] else
                               "避雷针" if r["name"] in ("避雷针", "绝缘避雷针") else
                               "避雷针控制器" for r in rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
