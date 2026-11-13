#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Malstone Mod（classId 26143）物品页 —— 19 件饰品。

数据来源：assets/malstone/lang/{zh_cn,en_us}.json、ItemRegs.java 的注册清单。
模组是 Malum（灵灾）的饰品扩展，饰品栏走 Curios。
图标从 16×16 纹理 NEAREST 放大到 128 与 32。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
LANG = BASE / "mal/assets/malstone/lang"
ICONS128 = BASE / "mal-icons128"
ICONS32 = BASE / "mal-icons32"
OUT = BASE / "mal-物品导入-26143.json"
NS = "malstone"

_PAW = ["呜喵", "喵呜", "喵喵"]

# (id, 类别, 稀有度, 一句话定位)
ITEMS = [
    ("blade_dath", "符文", "罕见", "镰刀专用的强化符文"),
    ("martyrdom", "符文", "罕见", "把全力一击的伤害分摊到后续轻击"),
    ("hungrier", "符文", "罕见", "拾取精魂时补充饥饿值"),
    ("eternal_fallen_soul", "符文", "罕见", "恢复灵魂护盾时叠加属性"),
    ("condenser", "扭曲", "罕见", "让精魂瞬间飞向佩戴者"),
    ("corpse_cauldron", "扭曲", "罕见", "让吃下的食物二次消化"),
    ("die_abyss", "扭曲", "罕见", "降低扭曲物品的能量消耗"),
    ("evil_engine", "扭曲", "罕见", "把精魂销毁换成生命与经验"),
    ("extremely_dead", "扭曲", "罕见", "让精魂在飞行中攻击沿途生物"),
    ("falling_well", "扭曲", "罕见", "强化腐朽心盾"),
    ("weeping_immortal", "扭曲", "罕见", "哭泣之井充能后的强化饰品"),
    ("breaking_the_life", "白镴", "罕见", "以生命值换取属性加成"),
    ("breaking_the_weapon", "白镴", "罕见", "偏移也能打中的攻击补正"),
    ("huge_soul", "白镴", "罕见", "提升治疗效果与魔法抗性"),
    ("ring_of_authority", "白镴", "罕见", "强化镰刀与权杖的攻击"),
    ("white_arrow_blade", "白镴", "罕见", "让镰刀始终能横扫"),
    ("soul_device", "灵魂", "罕见", "拾取精魂有概率翻倍"),
    ("soul_steel_components", "灵魂", "罕见", "魂钢的构件"),
    ("wallow_axe", "武器", "史诗", "三倍暴击的战斧"),
]


def b64(path: Path):
    if not path.exists():
        return ""
    buf = io.BytesIO()
    Image.open(path).convert("RGBA").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def title_case(s: str) -> str:
    """模组 lang 里有些英文名是全小写或半小写，统一转成标题格式。

    只处理普通单词，保留已有的全大写缩写与连字符。
    """
    small = {"of", "the", "and", "a", "an", "to", "in", "on", "for", "with"}
    words = s.split()
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in small:
            out.append(lw)
        elif w.isupper() and len(w) > 1:
            out.append(w)          # 保留缩写
        elif "-" in w:
            out.append("-".join(x[:1].upper() + x[1:] for x in w.split("-")))
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    zh = json.loads((LANG / "zh_cn.json").read_text(encoding="utf-8"))
    en = json.loads((LANG / "en_us.json").read_text(encoding="utf-8"))

    rows = []
    for bid, cat, rarity, blurb in ITEMS:
        name = zh.get(f"item.{NS}.{bid}", bid)
        ename = title_case(en.get(f"item.{NS}.{bid}", bid))
        # 说明条目
        subs = sorted(
            (k for k in zh if k.startswith(f"item.{NS}.{bid}.text")),
            key=lambda k: k,
        )
        effects = "".join(f"<li><p>{zh[k]}</p></li>" for k in subs)

        html = f"<p>{name}是 Malstone Mod 添加的{cat}类饰品，{blurb}。</p>"
        if effects:
            html += (
                "<p><strong>效果</strong>：</p>"
                f'<ul class="list-paddingleft-2">{effects}</ul>'
            )
        html += (
            f"<p><strong>品质</strong>：{rarity}。不可堆叠，一个物品占一格。</p>"
            "<p><strong>佩戴</strong>：放在 Curios 的饰品栏里生效，戴在身上即可，"
            "不需要拿在手上。模组新增的哭泣槽位也在饰品栏内。</p>"
            "<p><strong>获取</strong>：在工作台合成。</p>"
            "<p><strong>归属</strong>：本模组是灵灾的扩展，物品效果中的精魂、灵魂护盾、"
            "哭泣之井、镰刀等机制均来自灵灾本身。</p>"
        )

        rows.append({
            "id": bid,
            "name": name,
            "ename": ename,
            "regname": f"{NS}:{bid}",
            "category": cat,
            "type": "物品/方块",
            "maxstack": 1,
            "remark": (
                f"Malstone Mod 资料页：名称取自 lang/zh_cn.json 的 item.{NS}.{bid} 条目，"
                f"英文名取自 en_us.json，品质取自 ItemRegs 中 Item.Properties 的 Rarity 设定。"
                f"效果条目取自 lang 下的 .text 子项。"
                f"{tail()}"
            ),
            "html": html,
            "icon32": b64(ICONS32 / f"{NS}__{bid}.png"),
            "icon128": b64(ICONS128 / f"{NS}__{bid}.png"),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)\n")
    for r in rows:
        print(f"  {r['name']:<12} {r['ename']:<26} {r['category']:<5} {len(r['html']):>4} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
