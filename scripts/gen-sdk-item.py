#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self Damage Knife —— 物品页。

审核意见：对单个物品的详细描述需要写到物品/方块里（版本信息、适用场景、简介可保留）。
所以模组页只留简介 / 适用场景 / 版本信息，物品的详细描述全部搬到这里。

模组只有一个物品：selfdamageknife:knife（Stone knife）。
本机没有该模组的 jar，图标无法渲染，两个字段留空并在 remark 里说明。
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
OUT = BASE / "sdk-物品导入.json"
NS = "selfdamageknife"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


HTML = (
    "<p>Stone knife 是 Self Damage Knife 添加的小刀，右击对自己造成固定数值的伤害，"
    "供需要主动受伤的场合使用。</p>"

    "<p><strong>效果</strong>：</p>"
    '<ul class="list-paddingleft-2">'
    "<li><p>手持右击，立即对自身造成 5 点伤害（2.5 颗心）</p></li>"
    "<li><p>同时在脚下生成 5 个血液粒子，向四周扩散</p></li>"
    "</ul>"

    "<p><strong>特性</strong>：不可堆叠、没有耐久度，可以无限次使用。"
    "无法攻击其他生物，右击仅作用于使用者自身。</p>"

    "<p><strong>伤害来源</strong>：标记为自己，所以死亡提示与被打死不同。"
    "连续使用会使生命值持续下降，半血以下两次即可致死。</p>"

    "<p><strong>与其它自伤手段的区别</strong>：跳崖高度会改变伤害量，生物攻击的数值有浮动，"
    "接触仙人掌等方块还会附带额外效果。这把刀每次均为恒定的 2.5 颗心。</p>"

    "<p><strong>合成</strong>：竖排两块，上圆石下木棍。</p>"

    "<p><strong>成本</strong>：极低，游戏开局挖两块石头、砍一棵树即可制作，遗失也无实际损失。</p>"
)

rows = [{
    "id": "knife",
    "name": "Stone knife",
    "ename": "",
    "regname": f"{NS}:knife",
    "category": "工具",
    "type": "物品/方块",
    "maxstack": 1,
    "remark": (
        "Self Damage Knife 资料页：物品 id 自模组页原表格（selfdamageknife:knife），"
        "伤害数值 5 点、粒子数量 5 个、合成配方与使用特性取自模组页原有的详细描述，"
        "按审核意见从模组页移入本条。模组只有 en_us，无中文语言文件，主名用英文原名。"
        "图标未能提供：本机没有该模组 jar，无法渲染。"
        f"{tail()}"
    ),
    "html": HTML,
    "icon32": "",
    "icon128": "",
}]

OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
print(f"  正文 {len(HTML)} 字符")
print(f"  regname={rows[0]['regname']}  maxstack={rows[0]['maxstack']}")
