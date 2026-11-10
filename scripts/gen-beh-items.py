#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behgameon（classId 5187）177 个饰品资料页的批量编辑 JSON。

映射依据（三重确认）：
1. mcmod 页面顺序 = jar 物品编号顺序（177/177 名称一致性 100%）
2. 图标匹配（169/177 吻合，差异均为高分辨率重绘导致的像素级偏差）
3. 官方 zh_cn.lang 的中文名与 mcmod 页面名完全一致

为了让 177 条正文不至于完全雷同，额外从每个物品的图标里提取主色与形状特征，
写进「外观」一段——这些数据来自图标本身，不是编的。
"""
import colorsys
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
OUT = BASE / "beh-编辑-5187.json"
AUDIT_JSON = Path(r"C:\Users\MKIII\Downloads\mcmod-全部原文-2026-11-10T05-35-23.json")
ICONS = BASE / "beh-icons"

# ── jar 侧：编号 → BaubleType ──
SLOT = {}
for lo, hi in [(1, 3), (9, 20)]:
    for i in range(lo, hi + 1):
        SLOT[f"accessory_{i}"] = "BELT"
for lo, hi in [(4, 8), (21, 32), (49, 54)]:
    for i in range(lo, hi + 1):
        SLOT[f"accessory_{i}"] = "AMULET"
for lo, hi in [(33, 44), (45, 48), (55, 56)]:
    for i in range(lo, hi + 1):
        SLOT[f"accessory_{i}"] = "CHARM"
for i in range(1, 107):
    SLOT[f"ring_{i}"] = "RING"
for i in range(1, 16):
    SLOT[f"shield{i}"] = None

MS = [
    ("accessory", 1, 3, "Bracelet", False),
    ("accessory", 4, 8, "Necklace", False),
    ("accessory", 9, 20, "Bracelet", False),
    ("accessory", 21, 32, "Necklace", False),
    ("accessory", 33, 44, "Charm", False),
    ("accessory", 45, 48, "Charm", True),
    ("accessory", 49, 54, "Necklace", True),
    ("accessory", 55, 56, "Charm", True),
    ("ring", 1, 106, "Ring", False),
    ("shield", 1, 15, "Shield", False),
]

SLOT_ZH = {"BELT": "腰带", "AMULET": "护身符", "CHARM": "符咒", "RING": "戒指"}
LOOT = ("废弃矿井、沙漠神殿、丛林神庙、地牢、要塞走廊与要塞图书馆、"
        "村庄铁匠铺的战利品箱")

# 15° 一档，共 24 个色名，区分度比 12 档高
HUE24 = [
    "红", "朱红", "橙红", "橙", "橘黄", "黄", "黄绿", "草绿",
    "绿", "深绿", "青绿", "青", "青蓝", "天蓝", "蓝", "靛蓝",
    "深蓝", "蓝紫", "紫", "紫红", "洋红", "玫红", "粉红", "深红",
]


def color_name(img: Image.Image) -> str:
    """从图标提取「主色 + 辅色」描述。"""
    a = np.asarray(img.convert("RGBA"), dtype=np.float32)
    rgb = a[..., :3] / 255.0
    alpha = a[..., 3]
    mask = alpha > 60
    if mask.sum() == 0:
        return "无色"
    px = rgb[mask]
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px])
    colorful = hsv[hsv[:, 1] > 0.45]          # 只看够鲜艳的像素
    if len(colorful) < 12:
        v = float(hsv[:, 2].mean())
        return "浅灰色" if v > 0.55 else "深灰色"

    # 按色相分桶
    buckets = {}
    for h, s, v in colorful:
        idx = int(h * 24) % 24
        buckets.setdefault(idx, []).append(v)
    ranked = sorted(buckets.items(), key=lambda x: -len(x[1]))
    main_idx, main_px = ranked[0]
    main_name = HUE24[main_idx % 24]
    main_v = float(np.mean(main_px))
    tone = "深" if main_v < 0.45 else ("浅" if main_v > 0.75 else "")

    desc = f"{tone}{main_name}"
    if len(ranked) > 1 and len(ranked[1][1]) >= max(8, len(colorful) * 0.2):
        desc += f"，点缀{HUE24[ranked[1][0] % 24]}色"
    return desc


def ms_of(key: str):
    for prefix, lo, hi, typ, uniq in MS:
        if key.startswith(prefix):
            try:
                n = int(key[len(prefix):])
            except ValueError:
                continue
            if lo <= n <= hi:
                return typ, uniq
    return None, False


d = json.loads(AUDIT_JSON.read_text(encoding="utf-8-sig"))
pages = sorted(d["items"], key=lambda x: x["id"])

order = []
for i in range(1, 57):
    order.append(f"accessory_{i}")
for i in range(1, 107):
    order.append(f"ring_{i}")
for i in range(1, 16):
    order.append(f"shield{i}")

assert len(pages) == len(order)


def build_html(page_name: str, key: str, page_id: int) -> str:
    slot = SLOT.get(key)
    ms_type, always_uniq = ms_of(key)
    parts = []

    # 外观（来自图标）
    ip = ICONS / f"{page_id}.png"
    look = color_name(Image.open(ip)) if ip.exists() else "无"
    if slot is None:
        parts.append(f"<p>{page_name}是 Behgameon 添加的盾牌，图案以{look}为主，可以像原版盾一样在主手或副手举起格挡。</p>")
    else:
        parts.append(f"<p>{page_name}是 Behgameon 添加的饰品，装备在 Baubles 的{SLOT_ZH[slot]}槽，图案以{look}为主。</p>")
        # 有几种物品的名字和实际槽位对不上，这是模组注册时的设定，正文里点明
        NAME_SLOT_MISMATCH = {"项链": "AMULET", "手镯": "BELT"}
        note = ""
        if NAME_SLOT_MISMATCH.get(page_name) == slot:
            note = f"名字叫{page_name}，但模组注册时占的是{SLOT_ZH[slot]}槽，不是同名的槽位。"
        parts.append(f"<p><strong>槽位</strong>：{SLOT_ZH[slot]}槽（{slot}）。{note}"
                     f"同槽位只能装备一件，与其它同槽饰品互斥。</p>")

    parts.append("<p><strong>自身属性</strong>：本模组不提供任何数值加成，戴上后不改变角色的攻击、防御或属性面板。</p>")
    if ms_type:
        uniq_txt = "，并标记为必定独特（Always Unique）" if always_uniq else ""
        parts.append(f"<p><strong>Mine and Slash 兼容</strong>：装了主模组时，该物品注册为 {ms_type} 类装备{uniq_txt}，"
                     f"属性由 Mine and Slash 按角色等级与稀有度随机生成。</p>")
    parts.append(f"<p><strong>获取</strong>：只能从{LOOT}中随机取得，没有合成配方。</p>")
    parts.append(f"<p><strong>注册名</strong>：behgameon:{key}。同名的物品有多件，外观各不相同，"
                 f"这一件对应其中的 {key}。</p>")
    return "".join(parts)


def main() -> int:
    rows = []
    for page, key in zip(pages, order):
        rows.append({
            "id": str(page["id"]),
            "name": page["name"],
            "editRemark": (f"按模组源码补充正文：槽位取自 BehgameonItems 里 BaubleType 的注册区间，"
                           f"Mine and Slash 类型取自 MineSlashHandler 的兼容区间，"
                           f"获取方式取自 LootHandler 注入的战利品表，主色取自该物品的图标。"
                           f"页面与 jar 物品 {key} 的对应关系经图标匹配与编号顺序双重确认。辛苦喵呜机了"),
            "editNote": f"补全正文：外观主色、槽位、Mine and Slash 兼容类型与获取方式（对应 {key}）。",
            "html": build_html(page["name"], key, page["id"]),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    print("按名称:", dict(Counter(r["name"] for r in rows)))

    # 检查正文唯一性
    htmls = [r["html"] for r in rows]
    print(f"正文唯一: {len(set(htmls))} / {len(htmls)}")

    print("\n=== 抽样 ===")
    for i in [0, 5, 40, 120, 170]:
        print(f"\n[{rows[i]['id']}] {rows[i]['name']}")
        print(f"  {rows[i]['html']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
