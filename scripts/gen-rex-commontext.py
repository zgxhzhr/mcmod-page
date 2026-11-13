#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Realistic Explosives（classId 24724）通用文本方案。

77 条 → 17 种正文结构，63 条（82%）挤在 8 种里。
建 11 条通用文本，其余条目留空并引用。

保留独立正文的条目：核心设备、引爆组件、陷阱等确实各不相同的几条。
"""
import json
import random
import re
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "rex-重建-24724.json"
OUT_ITEMS = BASE / "rex-重建-24724.json"
OUT_COMMON = BASE / "rex-通用文本-24724.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# ── 11 条通用文本 ──
COMMON = [
    ("common_chemical", "化学品", "Chemical", True,
     "<p>这些物品是模组中的化学品，构成整条合成链的基础原料。</p>"
     "<p><strong>用途</strong>：作为原料或中间体，用于合成更高级的试剂、起爆药与炸药。"
     "多数反应需要在反应容器中按配方配比完成。</p>"
     "<p><strong>获取</strong>：由矿石经电解、加热或反应容器加工制得，部分环节需要 IC2 电力驱动。</p>"
     "<p><strong>形态</strong>：部分化学品同时存在瓶装物品与可放置的流体方块两种形态。</p>"),

    ("common_fluid", "流体", "Fluid", True,
     "<p>这些物品是模组中的流体方块。</p>"
     "<p><strong>形态</strong>：同时存在物品与方块两种形态——物品形态为瓶装，可搬运与配比；"
     "方块形态为可放置的流体，能在生产线上流动。</p>"
     "<p><strong>用途</strong>：与瓶子配合可得到对应的物品形态，用于反应容器的配比。</p>"
     "<p><strong>搬运</strong>：瓶装形态便于在生产线上转移，也便于精确控制配比用量。</p>"),

    ("common_dust", "粉末", "Dust", True,
     "<p>这些物品是模组中的金属或矿物粉末。</p>"
     "<p><strong>用途</strong>：既是冶炼成锭的原料，也是部分炸药配方的成分——"
     "金属粉末在含能材料中充当可燃剂，颗粒越细则反应越剧烈。</p>"
     "<p><strong>获取</strong>：由对应矿石或锭经粉碎加工制得。</p>"
     "<p><strong>形态</strong>：粉末是矿石与锭之间的中间形态，可以双向转换。</p>"),

    ("common_ingot", "金属锭", "Ingot", True,
     "<p>这些物品是模组中的金属锭。</p>"
     "<p><strong>用途</strong>：金属的压缩形态，便于存储与运输，"
     "也可再粉碎为粉末用于炸药配方。</p>"
     "<p><strong>获取</strong>：由对应粉末冶炼而成。</p>"
     "<p><strong>形态</strong>：锭是这条材料链的终点形态，"
     "再往上只有用于合成的化学试剂。</p>"),

    ("common_ore", "矿石", "Ore", True,
     "<p>这些方块是模组添加的矿石。</p>"
     "<p><strong>用途</strong>：开采后经粉碎、电解或加热加工，"
     "得到对应的粉末、锭与化学试剂，是整条生产链的起点。</p>"
     "<p><strong>生成</strong>：生成在主世界地下，与元版矿石一同分布。</p>"
     "<p><strong>开采</strong>：需要对应等级的镐，部分矿石的硬度高于原版同类。</p>"),

    ("common_hazma", "防化服", "Hazmat Suit", True,
     "<p>这些物品是模组添加的防护装备，四件构成整套防化服。</p>"
     "<p><strong>用途</strong>：生产线上大量涉及强酸、强碱与有毒物质，"
     "穿戴整套后可减免相应的环境伤害。</p>"
     "<p><strong>组成</strong>：头盔、胸甲、护腿、靴子四件，需集齐才有完整防护效果。</p>"
     "<p><strong>获取</strong>：由对应材料合成。</p>"),

    ("common_building", "建筑方块", "Building Block", True,
     "<p>这些方块是模组添加的建筑材料。</p>"
     "<p><strong>用途</strong>：抗爆性能高于原版方块，适合搭建试验场、储存区与防护墙。</p>"
     "<p><strong>特性</strong>：加固类的强度更高，普通混凝土则用于常规搭建。"
     "玻璃类在保持抗爆的同时仍可透光。</p>"
     "<p><strong>获取</strong>：由混凝土或玻璃经加固处理制得。</p>"),

    ("common_explosive_primary", "起爆药", "Primary Explosive", True,
     "<p>这些物品是模组中的起爆药。</p>"
     "<p><strong>等级</strong>：三级爆炸物体系中的最低一级。</p>"
     "<p><strong>特性</strong>：用来引爆威力更大的主装药。这类物质多数不稳定，"
     "容易因摩擦、撞击或高温点燃，搬运与储存需要小心。</p>"
     "<p><strong>获取</strong>：在反应容器中按配方配比制得。"
     "具体配方可在游戏内用 <strong>/syn &lt;名称&gt;</strong> 查询。</p>"),

    ("common_explosive_booster", "增强药", "Booster", True,
     "<p>这些物品是模组中的增强药。</p>"
     "<p><strong>等级</strong>：三级爆炸物体系中的中间一级。</p>"
     "<p><strong>特性</strong>：作为中间传爆药，介于起爆药与主装药之间，"
     "用来放大起爆能量、确保主装药完全反应。威力低于主装药，但比起爆药稳定。</p>"
     "<p><strong>获取</strong>：在反应容器中按配方配比制得。"
     "具体配方可在游戏内用 <strong>/syn &lt;名称&gt;</strong> 查询。</p>"),

    ("common_explosive_secondary", "主装药", "Secondary Explosive", True,
     "<p>这些物品是模组中的主装药。</p>"
     "<p><strong>等级</strong>：三级爆炸物体系中的最高一级。</p>"
     "<p><strong>特性</strong>：是爆炸威力的主要来源。相对稳定，"
     "普通撞击与明火不会引爆，需要起爆药或增强药触发。</p>"
     "<p><strong>获取</strong>：在反应容器中按配方配比制得。"
     "具体配方可在游戏内用 <strong>/syn &lt;名称&gt;</strong> 查询。</p>"),

    ("common_explosive_nuclear", "核装置", "Nuclear Device", True,
     "<p>这些物品是模组中的核装置。</p>"
     "<p><strong>等级</strong>：超出常规炸药体系，威力远高于三级分类中的任何一项。</p>"
     "<p><strong>特性</strong>：引爆后破坏范围极大，使用时需远离爆心，"
     "并注意对存档与地形的影响。</p>"
     "<p><strong>获取</strong>：在反应容器中按配方配比制得，所需材料量远超常规炸药。</p>"),
]

# 每个条目归到哪条通用文本
GRADE_MAP = {
    "APEX": "common_explosive_primary",
    "HMTD": "common_explosive_primary",
    "Lead Azide": "common_explosive_primary",
    "APAN": "common_explosive_booster",
    "Flash": "common_explosive_booster",
    "ATOMIC": "common_explosive_nuclear",
}

CAT_MAP = {
    "化学品": "common_chemical",
    "流体": "common_fluid",
    "粉末": "common_dust",
    "金属锭": "common_ingot",
    "矿石": "common_ore",
    "防化服": "common_hazma",
    "建筑方块": "common_building",
}

COMMON_ZH = {c[0]: c[1] for c in COMMON}


def assign(r):
    """返回该条目应引用的通用文本 id；不引用的返回 None。"""
    name, cat = r["name"], r["category"]
    if cat == "炸药":
        return GRADE_MAP.get(name, "common_explosive_secondary")
    return CAT_MAP.get(cat)


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    # 1) 通用文本
    common_rows = []
    for cid, name, en, _ , html in COMMON:
        common_rows.append({
            "id": cid,
            "name": name,
            "ename": en,
            "regname": "",
            "category": "{文本}",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "Realistic Explosives 通用文本：本条不针对具体物品，"
                "用于承接同类条目的共通说明，供其余页面在附言中引用。"
                f"{tail()}"
            ),
            "html": html,
            "icon32": "",
            "icon128": "",
        })
    OUT_COMMON.write_text(json.dumps(common_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) 物品页：归入通用文本的清空正文，其余保留
    kept, cleared = [], []
    for r in rows:
        cid = assign(r)
        if cid:
            r["html"] = ""
            r["remark"] = (
                "Realistic Explosives 资料页：名称取自 lang/en_US.lang。"
                f"本条正文留空，通用说明需引用通用文本「{COMMON_ZH[cid]}」。"
                + tail()
            )
            cleared.append(r["name"])
        else:
            kept.append(r["name"])

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"通用文本 {len(common_rows)} 条 → {OUT_COMMON.name}  ({OUT_COMMON.stat().st_size/1024:.1f} KB)")
    print(f"物品页 {len(rows)} 条 → {OUT_ITEMS.name}  ({OUT_ITEMS.stat().st_size/1024:.1f} KB)")
    print(f"  引用通用文本: {len(cleared)} 条")
    print(f"  保留独立正文: {len(kept)} 条 —— {kept}")
    print(f"  缺图标: {sum(1 for r in rows if not r['icon32'] or not r['icon128'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
