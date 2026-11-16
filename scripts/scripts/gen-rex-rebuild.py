#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Realistic Explosives（classId 24724）物品页正文补齐 + remark 修正。

两件事：
  1. 旧文件有 65 条 html 为空（当初按「同类只写一条」处理，但这是新增 JSON，
     留空等于页面没内容）。这里按类别给每条补上正文。
  2. remark 里去掉「重建」字样，改成描述内容来源的说法。

图标逻辑不变（icon32 + icon128，从 64×64 原纹理各自缩出）。
"""
import base64
import io
import json
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
TEX = BASE / "rex2/assets/realistic_explosives/textures"
SRC = BASE / "rex-物品导入-24724.json"
OUT = BASE / "rex-重建-24724.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

TEX_OVERRIDE = {
    "lockedDoor": "blocks/building/lockedDoor_lower.png",
    "reactionVessel": "blocks/reactionVessel_side.png",
}

BLOCK_CATS = {"矿石", "建筑方块", "机器", "核心设备", "流体", "陷阱"}
PRIORITY = ["items", "blocks/explosives", "blocks", ""]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# ── 按类别生成正文 ──
def body_chemical(name, zh):
    return (
        f"<p>{name}（{zh}）是 Realistic Explosives 添加的化学品。</p>"
        "<p><strong>用途</strong>：化学链中的原料或中间体，用于合成更高级的试剂、起爆药与炸药。</p>"
        "<p><strong>获取</strong>：由矿石经电解、加热或反应容器加工制得，部分需要 IC2 电力驱动。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名，此处中文名为按化学式补注的常用译名。</p>"
    )


def body_dust(name, zh):
    return (
        f"<p>{name}（{zh}）是 Realistic Explosives 添加的金属或矿物粉末。</p>"
        "<p><strong>用途</strong>：既是冶炼成锭的原料，也是部分炸药配方的成分——"
        "金属粉末在含能材料中充当可燃剂。</p>"
        "<p><strong>获取</strong>：由对应矿石或锭经粉碎加工制得。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


def body_ingot(name, zh):
    return (
        f"<p>{name}（{zh}）是 Realistic Explosives 添加的金属锭。</p>"
        "<p><strong>用途</strong>：金属的压缩形态，便于存储与运输，可再粉碎为粉末用于炸药配方。</p>"
        "<p><strong>获取</strong>：由对应粉末冶炼而成。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


def body_ore(name, zh):
    return (
        f"<p>{name}（{zh}）是 Realistic Explosives 添加的矿石。</p>"
        "<p><strong>用途</strong>：开采后经粉碎、电解或加热加工，得到对应的粉末、锭与化学试剂。</p>"
        "<p><strong>生成</strong>：生成在主世界地下，与其他矿石一同分布。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


def body_fluid(name, zh):
    return (
        f"<p>{name}（{zh}）是 Realistic Explosives 添加的流体方块。</p>"
        "<p><strong>形态</strong>：同时存在物品与方块两种形态——物品形态为瓶装，可搬运与配比；"
        "方块形态为可放置的流体，能在生产线上流动。</p>"
        "<p><strong>用途</strong>：与瓶子配合可得到对应的物品形态，用于反应容器的配比。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


def body_building(name, zh):
    return (
        f"<p>{name}（{zh}）是 Realistic Explosives 添加的建筑方块。</p>"
        "<p><strong>用途</strong>：抗爆性能高于原版方块，适合搭建试验场、储存区与防护墙。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


def body_machine(name, zh):
    return (
        f"<p>{name}（{zh}）是 Realistic Explosives 添加的机器。</p>"
        "<p><strong>作用</strong>：为化学反应提供加工条件，由 IC2 电力驱动。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


def body_hazma(name, zh):
    return (
        f"<p>{name}（{zh}）是 Realistic Explosives 添加的防护装备，为整套防化服的四件之一。</p>"
        "<p><strong>用途</strong>：生产线上大量涉及强酸、强碱与有毒物质，穿戴后可减免相应的环境伤害。</p>"
        "<p><strong>获取</strong>：由对应材料合成。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


def body_explosive(name, grade):
    return (
        f"<p>{name} 是 Realistic Explosives 添加的炸药。</p>"
        f"<p><strong>等级</strong>：{grade}。</p>"
        f"<p><strong>特性</strong>：{EXPLOSIVE_TRAIT[grade]}</p>"
        "<p><strong>获取</strong>：在反应容器中按配方配比制得。"
        f"具体配方可用 <strong>/syn {name}</strong> 在游戏内查询。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


EXPLOSIVE_TRAIT = {
    "起爆药": "作为起爆药使用，用来引爆威力更大的主装药。这类物质多数不稳定，容易因摩擦或高温点燃。",
    "增强药": "作为中间传爆药，介于起爆药与主装药之间，用来放大起爆能量、确保主装药完全反应。",
    "主装药": "作为主装药，是爆炸威力的主要来源。相对稳定，需要起爆药或增强药触发。",
    "核装置": "模组里的顶级爆炸物，威力远超常规炸药，使用时需远离爆心。",
}

# 炸药等级：从图标边框颜色推断（黄=起爆药 / 蓝=增强药 / 绿=主装药 / 红=核）
GRADE_MAP = {
    "APEX": "起爆药", "HMTD": "起爆药", "Lead Azide": "起爆药",
    "APAN": "增强药", "Flash": "增强药",
    "ATOMIC": "核装置",
}
GRADE_DEFAULT = "主装药"


# 中文补注（模组无中文，按化学/材料常用译名）
ZH_HINT = {
    "Acetone": "丙酮", "Ammonia": "氨", "Glycerine": "甘油",
    "Hydrochloric Acid": "盐酸", "Hydrogen Peroxide": "过氧化氢",
    "Nitric Acid": "硝酸", "Sulfuric Acid": "硫酸",
    "Acetone Peroxide": "过氧化丙酮", "Nitro Glycerine": "硝化甘油",
    "Ammonium Nitrate": "硝酸铵", "Potassium Nitrate": "硝酸钾",
    "Barium Nitrate": "硝酸钡", "Sodium Nitrate": "硝酸钠",
    "Potassium Carbonate (Potash)": "碳酸钾", "Distilled Water": "蒸馏水",
    "Toxic Waste": "有毒废料", "Sulfur": "硫", "Carbon": "碳",
    "Hexamine (Urotropine)": "六亚甲基四胺", "Aluminium": "铝",
    "Water": "水", "Formaldehyde": "甲醛", "Magnesium": "镁",
    "Titanium": "钛", "Uranium": "铀", "Bottle": "瓶子", "Shell": "弹壳",
    "Aluminium dust": "铝粉", "Titanium dust": "钛粉",
    "Magnesium dust": "镁粉", "Sulfur dust": "硫粉",
    "Uranium dust": "铀粉", "Nitratine dust": "硝石粉",
    "Sulfur Ingot": "硫锭", "Nitratine Ingot": "硝石锭",
    "Uranium Ingot": "铀锭", "Titanium Ingot": "钛锭",
    "Aluminium Ingot": "铝锭", "Magnesium Ingot": "镁锭",
    "Hazma Helmet": "防化服头盔", "Hazma Chestplate": "防化服胸甲",
    "Hazma Leggins": "防化服护腿", "Hazma Boots": "防化服靴子",
    "Sulfur": "硫矿", "Nitratine (Ore)": "硝石矿", "Uraninite (Ore)": "沥青铀矿",
    "Ilmenite (Ore)": "钛铁矿", "Aluminosilicate": "铝硅酸盐矿",
    "Magnesite (Ore)": "菱镁矿",
    "Concrete": "混凝土", "Heater": "加热器", "Electrolyzer": "电解槽",
    "Reaction Vessel": "反应容器", "Detonating Cord": "起爆索",
    "Quick Fuse": "速燃导火索", "Mine": "地雷", "Lockable Door": "可锁门",
}


def find_tex(rid: str, prefer_item: bool = True):
    if rid in TEX_OVERRIDE:
        p = TEX / TEX_OVERRIDE[rid]
        return p if p.exists() else None
    hits = list(TEX.rglob(f"{rid}.png"))
    if not hits:
        low = rid.lower()
        hits = [p for p in TEX.rglob("*.png") if p.stem.lower() == low]
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    if prefer_item:
        def score(p):
            rel = str(p.relative_to(TEX)).replace("\\", "/")
            for i, pref in enumerate(PRIORITY):
                if pref and rel.startswith(pref):
                    return i
            return len(PRIORITY)
        hits.sort(key=score)
    return hits[0]


def shade(img, f):
    if f >= 0.999:
        return img
    import numpy as np
    a = np.asarray(img.convert("RGBA"), dtype=np.float32)
    a[..., :3] *= f
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def iso_icon(tex_path, size):
    if not tex_path or not tex_path.exists():
        return None
    tex = Image.open(tex_path).convert("RGBA")
    S = 512
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cx, cy = S / 2, S / 2
    w = S * 0.40
    h = w
    top_p = [(cx, cy - h), (cx + w, cy - h / 2), (cx, cy), (cx - w, cy - h / 2)]
    left_p = [(cx - w, cy - h / 2), (cx, cy), (cx, cy + h), (cx - w, cy + h / 2)]
    right_p = [(cx, cy), (cx + w, cy - h / 2), (cx + w, cy + h / 2), (cx, cy + h)]

    def draw(poly, factor):
        t = shade(tex, factor)
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, x1 = int(min(xs)), int(max(xs))
        y0, y1 = int(min(ys)), int(max(ys))
        if x1 <= x0 or y1 <= y0:
            return
        small = t.resize((x1 - x0, y1 - y0), Image.NEAREST)
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).polygon([(p[0], p[1]) for p in poly], fill=255)
        layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        layer.paste(small, (x0, y0))
        canvas.paste(layer, (0, 0), mask)

    draw(top_p, 1.0)
    draw(left_p, 0.8)
    draw(right_p, 0.6)
    return canvas.resize((size, size), Image.LANCZOS)


def flat_icon(tex_path, size):
    if not tex_path or not tex_path.exists():
        return None
    im = Image.open(tex_path).convert("RGBA")
    if im.size == (size, size):
        return im
    method = Image.NEAREST if im.width < size else Image.LANCZOS
    return im.resize((size, size), method)


def b64(img):
    if img is None:
        return ""
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_body(r):
    """按类别 + 名称生成正文；旧文件里有正文的优先保留。"""
    name = r["name"]
    cat = r["category"]
    zh = ZH_HINT.get(name, "")

    if cat == "化学品":
        return body_chemical(name, zh) if zh else body_chemical(name, name)
    if cat == "粉末":
        return body_dust(name, zh)
    if cat == "金属锭":
        return body_ingot(name, zh)
    if cat == "矿石":
        return body_ore(name, zh)
    if cat == "流体":
        return body_fluid(name, zh)
    if cat == "建筑方块":
        return body_building(name, zh)
    if cat == "机器":
        return body_machine(name, zh) if zh else body_machine(name, name)
    if cat == "防化服":
        return body_hazma(name, zh)
    if cat == "炸药":
        grade = GRADE_MAP.get(name, GRADE_DEFAULT)
        return body_explosive(name, grade)
    # 其余（核心设备、引爆组件、陷阱）用旧正文，没有就补一段
    if r.get("html"):
        return r["html"]
    return (
        f"<p>{name} 是 Realistic Explosives 添加的物品。</p>"
        "<p><strong>说明</strong>：模组的语言文件只提供英文名，无中文译名。</p>"
    )


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    out = []
    filled = 0

    for r in rows:
        rid = r["id"]
        cat = r["category"]
        is_block = cat in BLOCK_CATS
        tex = find_tex(rid, prefer_item=not is_block)

        if is_block:
            i32, i128 = iso_icon(tex, 32), iso_icon(tex, 128)
        else:
            i32, i128 = flat_icon(tex, 32), flat_icon(tex, 128)

        html = build_body(r)
        if not r["html"] and html:
            filled += 1

        out.append({
            "id": rid,
            "name": r["name"],
            "ename": r["ename"],
            "regname": r["regname"],
            "category": cat,
            "type": r["type"],
            "maxstack": r["maxstack"],
            "remark": (
                "Realistic Explosives 资料页：名称取自 lang/en_US.lang。"
                f"图标{'按方块纹理渲染成等轴测立体图' if is_block else '使用该物品的独立纹理'}，"
                "小图标 32×32、大图标 128×128，均从原纹理各自缩出（原纹理为 64×64）。"
                + tail()
            ),
            "html": html,
            "icon32": b64(i32),
            "icon128": b64(i128),
        })

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(out)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    print(f"  补正文 {filled} 条，剩余空正文 {sum(1 for r in out if not r['html'])} 条")
    print(f"  remark 含「重建」: {sum(1 for r in out if '重建' in r['remark'])} 条")
    print(f"  缺图标: {sum(1 for r in out if not r['icon32'] or not r['icon128'])} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
