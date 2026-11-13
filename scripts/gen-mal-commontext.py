#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Malstone Mod（classId 26143）通用文本方案。

19 条饰品正文里，以下三段 19/19 完全相同（占全文 30%）：
  佩戴：放在 Curios 的饰品栏里生效…（×19）
  获取：在工作台合成。（×19）
  归属：本模组是灵灾的扩展…（×19）

而「效果」部分每条都不同，不能走综合。所以按 §6.1.10 走「引用通用文本」：
  通用文本「饰品」承接共通说明
  19 条只留「效果」+ 一句定位
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "mal-物品导入-26143.json"
OUT_ITEMS = BASE / "mal-物品导入-26143.json"
OUT_COMMON = BASE / "mal-通用文本-26143.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

COMMON_HTML = (
    "<p>这些物品是 Malstone Mod 添加的饰品，为该模组对灵灾的扩展内容。</p>"
    "<p><strong>佩戴</strong>：放在 Curios 的饰品栏里生效，戴在身上即可，"
    "不需要拿在手上。模组新增的哭泣槽位也在饰品栏内。</p>"
    "<p><strong>获取</strong>：全部在工作台合成，没有掉落或交易来源。</p>"
    "<p><strong>品质</strong>：除沉沦战斧为史诗，其余都是罕见。"
    "全部不可堆叠，一个物品占一格。</p>"
    "<p><strong>归属</strong>：本模组不新增生物、方块或维度，"
    "物品效果中出现的精魂、灵魂护盾、哭泣之井、镰刀、奥术谐振等，"
    "都是灵灾本身已有的机制。</p>"
)


# 代码里有、但 lang 的 .text 条目没写的固定属性加成
# （游戏内由 Curios 自动列在物品提示里，百科读者看不到，所以补进正文）
ATTR_BONUS = {
    "breaking_the_life": [
        ("灵魂护盾容量", "-100%"),
        ("移动速度", "+20%"),
    ],
    "eternal_fallen_soul": [
        ("灵魂护盾容量", "+4"),
        ("灵魂异动", "+0.2"),
    ],
    "soul_steel_components": [
        ("灵魂护盾容量", "+6"),
        ("灵魂异动", "+0.3"),
    ],
    "white_arrow_blade": [
        ("镰刀熟练度", "+25%"),
        ("奥术谐振", "-25%"),
    ],
}


# lang 里的 %d%% / %d秒 是格式化占位符，游戏内替换成配置值。
# 能从 Config.java 的默认值确认的，直接填数字；确认不了的改成中性表述。
PLACEHOLDER_FIX = {
    "殉锋符文：轻击造成的伤害为上一次全力造成伤害的%d%%":
        "轻击造成的伤害按上一次全力一击的比例折算，具体比例可在配置里调整",
    "在生命恢复到%d%%时停止使用饥饿值恢复生命":
        "生命恢复到设定比例后，不再用饥饿值回血（默认 50%）",
    "生命值最多恢复到%d%%":
        "生命值最多恢复到 50%",
    "最多获得额外%d%%的属性":
        "最多获得额外 25% 的属性",
    "堕井还有%d秒的充能时间":
        "每次充能后有一段冷却时间，长度可在配置里调整",
    "物理伤害提高至%d%%":
        "物理伤害提高至 130%",
}


def fix_placeholders(text: str) -> str:
    """把 lang 里的格式化占位符换成可读表述。"""
    import re

    for src, dst in PLACEHOLDER_FIX.items():
        if src in text:
            text = text.replace(src, dst)
    # 兜底：还有残留的 %d%% / %d秒 就删掉占位符描述
    text = re.sub(r"%d%%", "一定比例", text)
    text = re.sub(r"%d秒", "若干秒", text)
    text = re.sub(r"%d", "若干", text)
    return text


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    # 通用文本
    common = [{
        "id": "common_accessory",
        "name": "饰品",
        "ename": "Accessory",
        "regname": "",
        "category": "{文本}",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Malstone Mod 通用文本：本条不针对具体物品，"
            "用于承接十九件饰品的共通说明，供各饰品页在附言中引用。"
            f"{tail()}"
        ),
        "html": COMMON_HTML,
        "icon32": "",
        "icon128": "",
    }]
    OUT_COMMON.write_text(json.dumps(common, ensure_ascii=False, indent=2), encoding="utf-8")

    # 19 条压缩：只留「定位 + 效果」
    changed = 0
    for r in rows:
        # 抽出第一段（定位句）与效果列表
        import re
        first = re.search(r"<p>(.*?)</p>", r["html"])
        lead = first.group(1) if first else ""
        eff = re.search(r"<p><strong>效果</strong>：</p>(<ul.*?</ul>)", r["html"], re.S)
        eff_html = eff.group(1) if eff else ""
        attr_html = ""
        if r["id"] in ATTR_BONUS:
            rows_attr = "".join(
                f"<li><p>{k} {v}</p></li>" for k, v in ATTR_BONUS[r["id"]]
            )
            attr_html = (
                "<p><strong>属性加成</strong>：</p>"
                f'<ul class="list-paddingleft-2">{rows_attr}</ul>'
            )
        if eff_html:
            r["html"] = f"<p>{lead}</p><p><strong>效果</strong>：</p>{eff_html}{attr_html}"
        else:
            r["html"] = f"<p>{lead}</p>{attr_html}"
        r["html"] = fix_placeholders(r["html"])
        r["remark"] = (
            f"Malstone Mod 资料页：名称取自 lang/zh_cn.json 的 item.malstone.{r['id']} 条目，"
            f"英文名取自 en_us.json，品质取自 ItemRegs 中 Item.Properties 的 Rarity 设定，"
            f"效果条目取自 lang 下的 .text 子项，"
            f"属性加成取自各物品类 getAttributeModifiers 里的 AttributeModifier。"
            f"佩戴方式、获取途径与所属扩展需引用通用文本「饰品」。"
            f"{tail()}"
        )
        changed += 1

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"通用文本 1 条 → {OUT_COMMON.name}  ({OUT_COMMON.stat().st_size/1024:.1f} KB)")
    print(f"物品页 {len(rows)} 条 → {OUT_ITEMS.name}  ({OUT_ITEMS.stat().st_size/1024:.1f} KB)")
    print(f"  改写 {changed} 条\n")
    print("  正文长度变化：")
    for r in rows[:5]:
        print(f"    {r['name']:<12} {len(r['html']):>3} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
