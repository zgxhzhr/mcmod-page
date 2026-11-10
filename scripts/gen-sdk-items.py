#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self Damage Knife（classId 12913）1 个物品页的批量编辑 JSON。

数据来源：
- 名称：assets/selfdamageknife/lang/en_us.json（只有 en_us，无 zh_cn）
- 功能：KnifeRightclickedProcedure 里 entity.hurt(DamageSource, 5.0f) + 5 个血粒子
- 属性：KnifeItem 构造的 Item.Properties().stacksTo(1).rarity(COMMON)，没有耐久设置
- 配方：data/selfdamageknife/recipes/knife.json
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
OUT = BASE / "sdk-编辑-12913.json"

PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


HTML = (
    "<p>Stone knife 是 Self Damage Knife 唯一添加的物品，作用是对使用者自己造成伤害。</p>"
    "<p><strong>用法</strong>：手持右击，立即对自己造成 5 点伤害（2.5 颗心），"
    "同时向四周喷出 5 个血粒子作为反馈。</p>"
    "<p><strong>属性</strong>：不可堆叠，稀有度普通，没有耐久度设定，可以无限次使用。"
    "它不能攻击其他生物，右击只作用于自己。</p>"
    "<p><strong>用途</strong>：专门给需要「受伤」触发效果的场景准备——"
    "比如某些模组的低血量增益、吸血机制、或依赖受伤的成就。"
    "用它受伤比跳崖或找怪撞更可控，扣多少血是固定的。</p>"
    "<p><strong>风险</strong>：每次扣 2.5 颗心，半血以下连续使用会把自己打死，"
    "而且伤害来源是自己，死亡提示与被打死不同。</p>"
    "<p><strong>获取</strong>：竖排两块合成，上圆石下木棍。</p>"
)


def main() -> int:
    rows = [{
        "id": "774785",
        "name": "Stone knife",
        "editRemark": (
            "补全正文：右击造成 5 点自身伤害并生成 5 个血液粒子的逻辑，"
            "取自 KnifeRightclickedProcedure；堆叠与稀有度取自 KnifeItem 的构造参数；"
            "配方依据 data/selfdamageknife/recipes 下的定义。"
            f"{tail()}"
        ),
        "editNote": "补全正文：用法、固定 5 点自伤、无耐久、获取方式与风险提示。",
        "html": HTML,
    }]
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    print(f"\nremark: {rows[0]['editRemark']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
