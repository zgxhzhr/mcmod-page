#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mine & Slash Expansion（5180）—— 按审核意见建通用文本。

审核附言：需要建立通用文本。

重复情况：
  54 条工具  795 字符里约 700 与同系列其它档位完全相同（含整张 6 行属性表）
  18 条材料  221 字符里 180 相同，只差一个数字
  8 条法术   结构完全相同，只有效果句子不同

结构特点：九种工具在六个档位上的属性完全一致（镐子与鱼竿同档位数值相同），
所以一条通用文本能覆盖全部 54 条工具。

产出：
  mse-通用文本-5180.json   3 条：工具 / 工具材料 / 自身增益法术
  mse-物品导入-5180.json   80 条压缩正文
"""
import json
import random
import re
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "mse-物品导入-5180.json"
OUT_ITEMS = BASE / "mse-物品导入-5180.json"
OUT_COMMON = BASE / "mse-通用文本-5180.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

# 八个法术的效果（取自模组页 mse-介绍-5180.html 的「自身法术」表）
# 写成常量而不是从已改写的 html 里正则提取 —— 后者第二次运行就取不到了
SPELL_EFFECT = {
    "饱腹": "恢复饥饿值",
    "急促": "提升挖掘速度",
    "跳跃提升": "提升跳跃高度",
    "迅疾": "提升移动速度",
    "羽落": "减免摔落伤害",
    "全体夜视": "获得夜视",
    "全体水肺": "水下呼吸",
    "全体火焰保护": "抗火",
}

TIERS = ["普通", "罕见", "稀有", "史诗", "传说", "神话"]

# 六档属性（所有工具共用，从现有正文核对得出）
TIER_ATTR = {
    "普通": (0, 128, 4.0, 1.0),
    "罕见": (1, 256, 8.0, 2.0),
    "稀有": (2, 512, 12.0, 4.0),
    "史诗": (3, 1024, 16.0, 8.0),
    "传说": (4, 2048, 20.0, 16.0),
    "神话": (5, 4096, 24.0, 32.0),
}

TOOL_PURPOSE = {
    "镐子": "常规采矿工具，可以挖掘石头与矿石",
    "斧子": "伐木工具，也能当武器用",
    "铲子": "挖掘泥土、沙与沙砾",
    "锄头": "耕地工具",
    "鱼竿": "钓鱼工具",
    "锤子": "一次破坏正对方位的 3×3 方块，适合开采矿脉",
    "挖掘器": "一次破坏正对方位的 3×3 方块，适合清理土方",
    "Excalator": "阶梯式挖掘，一次破出斜向通道",
    "Hamavator": "锤与锹的合体，用于范围挖掘的通用款",
}

MAT_PURPOSE = {
    "锭": "基础材料，所有档位工具的主要原料",
    "混合锭": "由多种材料熔合而成，用于中高档工具",
    "压缩锭": "密度更高的一档材料，用于高阶工具",
}


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    # ── 通用文本 1：工具 ──
    tool_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in TOOL_PURPOSE.items()
    )
    tier_rows = "".join(
        f"<tr><td>{t}</td><td>{TIER_ATTR[t][0]}</td><td>{TIER_ATTR[t][1]:,}</td>"
        f"<td>{TIER_ATTR[t][2]:g}</td><td>{TIER_ATTR[t][3]:g}</td><td>30</td></tr>"
        for t in TIERS
    )

    html_tool = (
        "<p>Mine &amp; Slash Expansion 的工具共九种，每种按稀有度分六档，"
        "从普通一路做到神话。</p>"

        "<p><strong>九种工具的分工</strong>：</p>"
        "<table><thead><tr><th>工具</th><th>用途</th></tr></thead><tbody>"
        + tool_rows +
        "</tbody></table>"

        "<p><strong>六档属性</strong>：同一件工具的六个档位，属性项目完全相同，"
        "数值逐级提升——耐久与攻击伤害每级翻倍，挖掘速度每级 +4，采集等级每级 +1，"
        "附魔能力固定 30。</p>"
        "<table><thead><tr><th>档位</th><th>采集等级</th><th>耐久</th>"
        "<th>挖掘速度</th><th>攻击伤害</th><th>附魔能力</th></tr></thead><tbody>"
        + tier_rows +
        "</tbody></table>"

        "<p><strong>九种工具在属性上没有任何区别</strong>：镐子与鱼竿在同档位下的耐久、"
        "挖掘速度与攻击伤害完全一致。它们的差别只在于适合挖掘的方块类型，"
        "这点由工具种类本身决定，与档位无关。</p>"

        "<p><strong>合成</strong>：每种工具由对应档位的金属锭制作，一档材料对应一档工具。</p>"
    )

    # ── 通用文本 2：工具材料 ──
    mat_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in MAT_PURPOSE.items()
    )
    html_mat = (
        "<p>Mine &amp; Slash Expansion 的材料分三种，每种各六档稀有度，"
        "与六档工具一一对应。同一档位下，三种材料都用于制作该档的工具。</p>"
        "<table><thead><tr><th>材料</th><th>定位</th></tr></thead><tbody>"
        + mat_rows +
        "</tbody></table>"
        "<p>三种材料的区别在于加工层级：锭是基础，混合锭由它熔合而来，"
        "压缩锭的密度最高。层级越高，对应的工具档位也越高。</p>"
        "<p>三种材料都由工作台合成，或从战利品中取得。</p>"
    )

    # ── 通用文本 3：自身增益法术 ──
    spell_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in SPELL_EFFECT.items()
    )

    html_spell = (
        "<p>这八个法术都是只作用于使用者本人的增益，一次性消耗，"
        "用法与挖矿与砍杀本体的法术一致。</p>"
        "<p><strong>效果一览</strong>：</p>"
        "<table><thead><tr><th>法术</th><th>效果</th></tr></thead><tbody>"
        + spell_rows +
        "</tbody></table>"
        "<p><strong>属性联动</strong>：效果会挂在本体的属性条目上，"
        "因此能吃属性加成与词条体系。</p>"
    )

    common = [
        {
            "id": "common_tools", "name": "工具", "ename": "Tools", "regname": "",
            "category": "{文本}", "type": "物品/方块", "maxstack": 64,
            "remark": (
                "Mine & Slash Expansion 通用文本：本条不针对具体工具，"
                "用于承接九种工具的分工与六档属性阶梯，供 54 条工具页在附言中引用。"
                f"{tail()}"
            ),
            "html": html_tool, "icon32": "", "icon128": "",
        },
        {
            "id": "common_materials", "name": "工具材料", "ename": "Tool Materials", "regname": "",
            "category": "{文本}", "type": "物品/方块", "maxstack": 64,
            "remark": (
                "Mine & Slash Expansion 通用文本：本条不针对具体材料，"
                "用于承接三种锭的定位与六档对应关系，供 18 条材料页在附言中引用。"
                f"{tail()}"
            ),
            "html": html_mat, "icon32": "", "icon128": "",
        },
        {
            "id": "common_spells", "name": "自身增益法术", "ename": "Self Buff Spells", "regname": "",
            "category": "{文本}", "type": "物品/方块", "maxstack": 64,
            "remark": (
                "Mine & Slash Expansion 通用文本：本条不针对具体法术，"
                "用于承接八个自身增益法术的用法与效果一览，供各法术页在附言中引用。"
                f"{tail()}"
            ),
            "html": html_spell, "icon32": "", "icon128": "",
        },
    ]
    OUT_COMMON.write_text(json.dumps(common, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 80 条压缩正文 ──
    for r in rows:
        cat = r["category"]
        if cat == "工具":
            parts = r["name"].split(" ", 1)
            tier, kind = parts[0], parts[1] if len(parts) > 1 else ""
            c, d, s, a = TIER_ATTR.get(tier, (0, 0, 0, 0))
            r["html"] = f"<p>{tier}档的{kind}。</p>"
            r["remark"] = (
                f"Mine & Slash Expansion 资料页：物品 id 为 {r['regname']}，"
                f"属性取自模组注册参数。九种工具的分工与六档阶梯需引用通用文本「工具」。"
                f"{tail()}"
            )
        elif cat == "材料":
            parts = r["name"].split(" ", 1)
            tier, kind = parts[0], parts[1] if len(parts) > 1 else ""
            r["html"] = f"<p>{tier}档的{kind}。</p>"
            r["remark"] = (
                f"Mine &amp; Slash Expansion 资料页：物品 id 为 {r['regname']}，"
                f"三种锭的定位与六档对应关系需引用通用文本「工具材料」。"
                f"{tail()}"
            )
        else:  # 法术
            eff = SPELL_EFFECT.get(r["name"], "")
            r["html"] = f"<p>自身增益法术，使用后{eff}。</p>"
            r["remark"] = (
                f"Mine &amp; Slash Expansion 资料页：物品 id 为 {r['regname']}，"
                f"用法与属性联动需引用通用文本「自身增益法术」。"
                f"{tail()}"
            )

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"通用文本 3 条 → {OUT_COMMON.name}  ({OUT_COMMON.stat().st_size/1024:.1f} KB)")
    for c in common:
        print(f"  {c['name']:<14}{len(c['html']):>5} 字符")
    print(f"\n物品页 {len(rows)} 条 → {OUT_ITEMS.name}  ({OUT_ITEMS.stat().st_size/1024:.1f} KB)")
    lens = {}
    for r in rows:
        lens.setdefault(r["category"], []).append(len(r["html"]))
    for k, v in lens.items():
        print(f"  {k}: {min(v)}~{max(v)} 字符（{len(v)} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
