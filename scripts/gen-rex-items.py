#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Realistic Explosives（classId 24724）物品/方块批量新增 JSON。

数量：103 条
  化学品 26 · 粉末 6 · 锭 6 · 炸药物品 16 · 防化服 4 · 机器 2
  矿石 6 · 液体 10 · 建材 6 · 反应容器 1 · 炸药方块 17 · 引信 2 · 地雷 1

名称全部取自 lang/en_US.lang 的英文值，模组只有 en_US，不做自译。
5 个标记 (DONT USE!) 的废弃内容不入库。

纹理映射：assets/realistic_explosives/textures/ 下
  items/components/<key>.png    化学品/粉末/锭/炸药物品
  items/hazma*.png              防化服
  blocks/ores/<key>.png         矿石
  blocks/building/<key>.png     建材
  blocks/explosives/<KEY>.png   炸药方块
  blocks/fluids/                液体
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
MOD = BASE / "rex"
ASSETS = MOD / "assets/realistic_explosives"
TEX = ASSETS / "textures"
OUT = BASE / "rex-物品导入-24724.json"
NS = "realistic_explosives"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


LANGS = {
    "acetone": "Acetone", "ammonia": "Ammonia", "glycerine": "Glycerine",
    "hydrochloricAcid": "Hydrochloric Acid", "hydrogenPeroxide": "Hydrogen Peroxide",
    "nitricAcid": "Nitric Acid", "sulfuricAcid": "Sulfuric Acid",
    "acetonePeroxide": "Acetone Peroxide", "nitroGlycerine": "Nitro Glycerine",
    "ammoniumNitrate": "Ammonium Nitrate", "potassiumNitrate": "Potassium Nitrate",
    "bariumNitrate": "Barium Nitrate", "sodiumNitrate": "Sodium Nitrate",
    "potassiumCarbonate": "Potassium Carbonate (Potash)",
    "distilledWater": "Distilled Water", "toxicWaste": "Toxic Waste",
    "sulfur": "Sulfur", "carbon": "Carbon", "hexamine": "Hexamine (Urotropine)",
    "aluminium": "Aluminium", "water": "Water", "formaldehyde": "Formaldehyde",
    "magnesium": "Magnesium", "titanium": "Titanium", "uranium": "Uranium",
    "bottle": "Bottle", "shell": "Shell",
    "aluminiumDust": "Aluminium dust", "titaniumDust": "Titanium dust",
    "magnesiumDust": "Magnesium dust", "sulfurDust": "Sulfur dust",
    "uraniumDust": "Uranium dust", "nitratineDust": "Nitratine dust",
    "sulfurIngot": "Sulfur Ingot", "nitratineIngot": "Nitratine Ingot",
    "uraniumIngot": "Uranium Ingot", "titaniumIngot": "Titanium Ingot",
    "aluminiumIngot": "Aluminium Ingot", "magnesiumIngot": "Magnesium Ingot",
    "hazmaHelmet": "Hazma Helmet", "hazmaChestplate": "Hazma Chestplate",
    "hazmaLeggins": "Hazma Leggins", "hazmaBoots": "Hazma Boots",
    "heater": "Heater", "electrolyzer": "Electrolyzer",
    "APEX": "APEX", "HMTD": "HMTD", "leadAzide": "Lead Azide", "APAN": "APAN",
    "ANFO": "ANFO", "ANNM": "ANNM", "AMMONAL": "AMMONAL", "dynamite": "Dynamite",
    "RDX": "RDX", "CL20": "CL20", "ONC": "ONC", "astroliteG": "Astrolite G",
    "PETN": "PETN", "ETN": "ETN", "FLASH": "Flash", "ATOMIC": "Atomic Bomb",
    "nitratine": "Nitratine (Ore)", "uraninite": "Uraninite (Ore)",
    "ilmenite": "Ilmenite (Ore)", "aluminosilicate": "Aluminosilicate (Ore)",
    "magnesite": "Magnesite (Ore)",
    "concrete": "Concrete", "hardenedConcrete": "Concrete (Hardened)",
    "reinforcedConcrete": "Concrete (Reinforced)",
    "hardenedGlass": "Glass (Hardened)", "reinforcedGlass": "Glass (Reinforced)",
    "lockedDoor": "Lockable Door",
    "reactionVessel": "Reaction Vessel",
    "detonatingCord": "Detonating Cord", "quickFuse": "Quick Fuse", "mine": "Mine",
}


def b64(path: Path) -> str:
    if not path.exists():
        return ""
    img = Image.open(path).convert("RGBA")
    if img.size != (32, 32):
        img = img.resize((32, 32), Image.LANCZOS if img.width > 32 else Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


BLOCK_ICONS = BASE / "rex-block-icons"


def icon_of(key: str, kind: str) -> str:
    """方块类用等轴测立体图标，物品类用平面纹理。"""
    iso_map = {
        "矿石": f"ore_{key}", "建筑方块": key, "核心设备": "reactionVessel",
        "炸药": key, "陷阱": "mine",
        "流体": f"{key}_f",
    }
    iso_key = iso_map.get(kind)
    if iso_key:
        p = BLOCK_ICONS / f"{iso_key}-128.png"
        if p.exists():
            return b64(p)
    """按类别找纹理。"""
    cands = [
        TEX / "items/components" / f"{key}.png",
        TEX / "items" / f"{key}.png",
        TEX / "items/weapons" / f"{key}.png",
        TEX / "blocks/explosives" / f"{key}.png",
        TEX / "blocks/explosives/models" / f"{key}.png",
        TEX / "blocks/ores" / f"{key}.png",
        TEX / "blocks/building" / f"{key}.png",
        TEX / "blocks/fluids" / f"{key}.png",
        TEX / "blocks" / f"{key}.png",
    ]
    for c in cands:
        if c.exists():
            return b64(c)
    # 多面方块：取主面纹理
    alias = {
        "lockedDoor": TEX / "blocks/building/lockedDoor_upper.png",
        "reactionVessel": TEX / "blocks/reactionVessel_side.png",
    }
    a = alias.get(key)
    if a and a.exists():
        return b64(a)
    return ""


# ── 分类数据 ──
# 与流体同名的 10 种（acetone / ammonia / … / toxicWaste）并入「流体」类，
# 因为它们同时有物品与方块两种形态，按 mcmod 惯例合成一页。
CHEMICALS = ["acetonePeroxide", "ammoniumNitrate", "potassiumNitrate", "bariumNitrate",
             "sodiumNitrate", "potassiumCarbonate", "sulfur", "carbon",
             "hexamine", "aluminium", "water", "formaldehyde", "magnesium", "titanium",
             "uranium", "bottle", "shell"]

DUSTS = ["aluminiumDust", "titaniumDust", "magnesiumDust", "sulfurDust",
         "uraniumDust", "nitratineDust"]

INGOTS = ["sulfurIngot", "nitratineIngot", "uraniumIngot", "titaniumIngot",
          "aluminiumIngot", "magnesiumIngot"]

EXPLOSIVES = ["APEX", "HMTD", "leadAzide", "APAN", "ANFO", "ANNM", "AMMONAL",
              "dynamite", "RDX", "CL20", "ONC", "astroliteG", "PETN", "ETN",
              "FLASH", "ATOMIC"]

EXPLOSIVE_TIER = {
    # 等级依据物品图标边框色：黄=起爆药 蓝=增强药 绿=主装药 白/其他=杂项
    "HMTD": "起爆药", "leadAzide": "起爆药",
    "APEX": "起爆药",       # 图标标注为 TATP，APEX 是它的商业名称
    "APAN": "增强药",
    "ANFO": "主装药", "ANNM": "主装药", "AMMONAL": "主装药", "dynamite": "主装药",
    "RDX": "主装药", "CL20": "主装药", "ONC": "主装药", "astroliteG": "主装药",
    "PETN": "主装药", "ETN": "主装药",
    "FLASH": "杂项", "ATOMIC": "杂项",
}

ARMOR = ["hazmaHelmet", "hazmaChestplate", "hazmaLeggins", "hazmaBoots"]

MACHINES = ["heater", "electrolyzer"]

ORES = ["sulfur", "nitratine", "uraninite", "ilmenite", "aluminosilicate", "magnesite"]

FLUIDS = ["acetone", "glycerine", "hydrochloricAcid", "hydrogenPeroxide",
          "nitricAcid", "nitroGlycerine", "sulfuricAcid", "distilledWater",
          "ammonia", "toxicWaste"]

BUILDING = ["concrete", "hardenedConcrete", "reinforcedConcrete",
            "hardenedGlass", "reinforcedGlass", "lockedDoor"]

EXPLOSIVE_BLOCKS = ["APEX", "HMTD", "leadAzide", "APAN", "ANFO", "ANNM", "AMMONAL",
                    "dynamite", "RDX", "CL20", "ONC", "astroliteG", "PETN", "ETN",
                    "FLASH", "ATOMIC"]

FUSES = ["detonatingCord", "quickFuse"]

MINES = ["mine"]


def chem_html(key: str) -> str:
    zh = {"acetone": "丙酮", "ammonia": "氨", "glycerine": "甘油",
          "hydrochloricAcid": "盐酸", "hydrogenPeroxide": "过氧化氢",
          "nitricAcid": "硝酸", "sulfuricAcid": "硫酸",
          "acetonePeroxide": "过氧化丙酮", "nitroGlycerine": "硝化甘油",
          "ammoniumNitrate": "硝酸铵", "potassiumNitrate": "硝酸钾",
          "bariumNitrate": "硝酸钡", "sodiumNitrate": "硝酸钠",
          "potassiumCarbonate": "碳酸钾", "distilledWater": "蒸馏水",
          "toxicWaste": "有毒废料", "sulfur": "硫", "carbon": "碳",
          "hexamine": "六亚甲基四胺", "aluminium": "铝", "water": "水",
          "formaldehyde": "甲醛", "magnesium": "镁", "titanium": "钛",
          "uranium": "铀", "bottle": "瓶子", "shell": "弹壳"}.get(key, "")
    name = LANGS[key]
    note = f"（{zh}）" if zh else ""
    parts = [f"<p>{name}{note}是 Realistic Explosives 添加的化学品。</p>"]
    if key in ("bottle", "shell"):
        parts.append("<p><strong>用途</strong>：盛装液体或作为弹药的容器类组件，属于生产链的辅助物品。</p>")
    else:
        parts.append("<p><strong>用途</strong>：化学链中的原料或中间体，用于合成更高级的试剂、起爆药与炸药。</p>"
                     "<p><strong>获取</strong>：由矿石经电解、加热或反应容器加工制得，部分需要 IC2 电力驱动。</p>")
    parts.append("<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")
    return "".join(parts)


def dust_html(key: str) -> str:
    zh = {"aluminiumDust": "铝粉", "titaniumDust": "钛粉", "magnesiumDust": "镁粉",
          "sulfurDust": "硫粉", "uraniumDust": "铀粉", "nitratineDust": "硝石粉"}.get(key, "")
    name = LANGS[key]
    return (f"<p>{name}（{zh}）是 Realistic Explosives 添加的金属或矿物粉末。</p>"
            "<p><strong>用途</strong>：既是冶炼成锭的原料，也是部分炸药配方的成分——"
            "金属粉末在含能材料中充当可燃剂。</p>"
            "<p><strong>获取</strong>：由对应矿石或锭经粉碎加工制得。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def ingot_html(key: str) -> str:
    zh = {"sulfurIngot": "硫锭", "nitratineIngot": "硝石锭", "uraniumIngot": "铀锭",
          "titaniumIngot": "钛锭", "aluminiumIngot": "铝锭", "magnesiumIngot": "镁锭"}.get(key, "")
    name = LANGS[key]
    return (f"<p>{name}（{zh}）是 Realistic Explosives 添加的金属锭。</p>"
            "<p><strong>用途</strong>：金属的压缩形态，便于存储与运输，可再粉碎为粉末用于炸药配方。</p>"
            "<p><strong>获取</strong>：由对应粉末冶炼而成。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def explosive_html(key: str) -> str:
    name = LANGS[key]
    tier = EXPLOSIVE_TIER.get(key, "主装药")
    tier_desc = {
        "起爆药": "作为起爆药使用，用来引爆威力更大的主装药。这类物质多数不稳定，容易因摩擦或高温点燃。",
        "主装药": "作为主装药使用，承担主要的爆炸输出。单独点火不会引爆，需要先由起爆药引发。",
        "增强药": "作为增强药使用，用于放大主装药的威力。威力强，但敏感度与起爆药相当。",
        "杂项": "属于杂项类炸药，不需要起爆药即可直接引爆。",
    }.get(tier, "")
    return (f"<p>{name} 是 Realistic Explosives 添加的炸药。</p>"
            f"<p><strong>等级</strong>：{tier}。</p>"
            f"<p><strong>特性</strong>：{tier_desc}</p>"
            "<p><strong>获取</strong>：在反应容器中按配方配比制得。具体配方可用 <strong>/syn {name}</strong> 在游戏内查询。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def armor_html(key: str) -> str:
    part = {"hazmaHelmet": "头盔", "hazmaChestplate": "胸甲",
            "hazmaLeggins": "护腿", "hazmaBoots": "靴子"}[key]
    name = LANGS[key]
    return (f"<p>{name}（防化服{part}）是 Realistic Explosives 添加的防护装备，为整套防化服的四件之一。</p>"
            "<p><strong>用途</strong>：生产线上大量涉及强酸、强碱与有毒物质，穿戴后可减免相应的环境伤害。</p>"
            "<p><strong>获取</strong>：由对应材料合成。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def machine_html(key: str) -> str:
    name = LANGS[key]
    desc = {
        "heater": "为化学反应提供温度条件。部分合成需要在加热状态下进行，由 IC2 电力驱动。",
        "electrolyzer": "通过电解制取试剂与金属。是化学链上游的关键设备，同样消耗 IC2 电力。",
    }[key]
    zh = {"heater": "加热器", "electrolyzer": "电解机"}[key]
    return (f"<p>{name}（{zh}）是 Realistic Explosives 添加的机器。</p>"
            f"<p><strong>作用</strong>：{desc}</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def ore_html(key: str) -> str:
    zh = {"sulfur": "硫矿", "nitratine": "硝石矿", "uraninite": "晶质铀矿",
          "ilmenite": "钛铁矿", "aluminosilicate": "铝硅酸盐矿",
          "magnesite": "菱镁矿"}[key]
    name = LANGS[key]
    return (f"<p>{name}（{zh}）是 Realistic Explosives 添加的矿石。</p>"
            "<p><strong>用途</strong>：开采后经粉碎、电解或加热加工，得到对应的粉末、锭与化学试剂。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


FLUID_NAMES = {"acetone", "ammonia", "glycerine", "hydrochloricAcid", "hydrogenPeroxide",
               "nitricAcid", "sulfuricAcid", "distilledWater", "nitroGlycerine", "toxicWaste"}


def fluid_html(key: str) -> str:
    zh = {"acetone": "丙酮", "glycerine": "甘油", "hydrochloricAcid": "盐酸",
          "hydrogenPeroxide": "过氧化氢", "nitricAcid": "硝酸",
          "nitroGlycerine": "硝化甘油", "sulfuricAcid": "硫酸",
          "distilledWater": "蒸馏水", "ammonia": "氨", "toxicWaste": "有毒废料"}.get(key, "")
    name = LANGS[key]
    return (f"<p>{name}（{zh}）是 Realistic Explosives 添加的流体方块。</p>"
            "<p><strong>形态</strong>：同时存在物品与方块两种形态——物品形态为瓶装，可搬运与配比；"
            "方块形态为可放置的流体，能在生产线上流动。</p>"
            "<p><strong>用途</strong>：与瓶子配合可得到对应的物品形态，用于反应容器的配比。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def building_html(key: str) -> str:
    zh = {"concrete": "混凝土", "hardenedConcrete": "硬化混凝土",
          "reinforcedConcrete": "强化混凝土", "hardenedGlass": "硬化玻璃",
          "reinforcedGlass": "强化玻璃", "lockedDoor": "可锁门"}[key]
    name = LANGS[key]
    return (f"<p>{name}（{zh}）是 Realistic Explosives 添加的建筑方块。</p>"
            "<p><strong>用途</strong>：抗爆性能高于原版方块，适合搭建试验场、储存区与防护墙。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def reaction_html() -> str:
    return ("<p>Reaction Vessel（反应容器）是 Realistic Explosives 的核心机器，用于按配方生成炸药与各类产物。</p>"
            "<p><strong>用法</strong>：把所需组件放入容器并按配方配比，即可产出目标物品。"
            "具体配方可用 <strong>/syn &lt;名称&gt;</strong> 在游戏内查询。</p>"
            "<p><strong>注意</strong>：容器的物品栏在取出后不保留内容，因此配方需一次性配比完成后取出。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def expl_block_html(key: str) -> str:
    name = LANGS[key]
    tier = EXPLOSIVE_TIER.get(key, "主装药")
    return (f"<p>{name} 的可放置方块形态，用于把该炸药布置在世界中。</p>"
            f"<p><strong>等级</strong>：{tier}。</p>"
            "<p><strong>用法</strong>：放置后用起爆索或导火索引爆。"
            "起爆药可直接点燃，主装药需先由起爆药引发。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def fuse_html(key: str) -> str:
    zh = {"detonatingCord": "起爆索", "quickFuse": "速燃导火索"}[key]
    name = LANGS[key]
    return (f"<p>{name}（{zh}）是 Realistic Explosives 添加的引爆组件。</p>"
            "<p><strong>用途</strong>：连接炸药方块，把起爆信号传导至装药。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def mine_html() -> str:
    return ("<p>Mine（地雷）是 Realistic Explosives 添加的陷阱类爆炸物。</p>"
            "<p><strong>用途</strong>：埋设在地面，由玩家或生物踩踏触发。</p>"
            "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>")


def main() -> int:
    rows = []

    _seen_cat = set()

    def add(key, category, html, maxstack=64):
        # 同类模板正文重复度高，只保留该类第一条的正文，其余留空
        if category in _seen_cat:
            html = ""
            note = (f"同类物品的正文已集中在「{category}」类的首条页面，本条留空，"
                    "需协助创建抽象类以统一展示。")
        else:
            _seen_cat.add(category)
            note = f"本条为「{category}」类的正文代表页，同类其余条目留空并引用同一套说明。"
        rows.append({
            "id": key,
            # 模组无中文 lang：主要名称用英文，次要名称留空
            "name": LANGS[key],
            "ename": "",
            "regname": f"{NS}:{key}",
            "category": category,
            "type": "物品/方块",
            "maxstack": maxstack,
            "remark": (
                "Realistic Explosives 新增资料页：名称取自 lang/en_US.lang 的英文值。"
                "分类与用途依据模组内的物品组划分与 CurseForge 项目说明。"
                + note + tail()
            ),
            "html": html,
            "icon32": icon_of(key, category),
        })

    for k in CHEMICALS:
        add(k, "化学品", chem_html(k))
    for k in DUSTS:
        add(k, "粉末", dust_html(k))
    for k in INGOTS:
        add(k, "金属锭", ingot_html(k))
    for k in EXPLOSIVES:
        add(k, "炸药", explosive_html(k))
    for k in ARMOR:
        add(k, "防化服", armor_html(k), maxstack=1)
    for k in MACHINES:
        add(k, "机器", machine_html(k))
    for k in ORES:
        add(k, "矿石", ore_html(k))
    for k in FLUIDS:
        add(k, "流体", fluid_html(k))
    for k in BUILDING:
        add(k, "建筑方块", building_html(k))
    add("reactionVessel", "核心设备", reaction_html())
    # 炸药方块的 16 个已并入上面的「炸药」类（同一物品的方块形态）
    for k in FUSES:
        add(k, "引爆组件", fuse_html(k))
    for k in MINES:
        add(k, "陷阱", mine_html())

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    noicon = [r["id"] for r in rows if not r["icon32"]]
    print(f"无图标 {len(noicon)} 个" + (f": {noicon}" if noicon else " ✓"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
