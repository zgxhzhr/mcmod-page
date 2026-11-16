#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 RLBT 的结构 nbt，提取尺寸、方块构成、刷怪笼与箱子数量。

输出 rlbt-structures.json 供生成页面时引用。
"""
import json
from collections import Counter
from pathlib import Path

import nbtlib

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
MOD = BASE / "rlbt"
NBT = MOD / "data/kimohpangs_bs/structures"
POOL = MOD / "data/kimohpangs_bs/worldgen/template_pool"
SSET = MOD / "data/kimohpangs_bs/worldgen/structure_set"
OUT = BASE / "rlbt-structures.json"

# 关注这几类方块
WATCH = {
    "spawner": "刷怪笼",
    "chest": "箱子",
    "barrel": "木桶",
    "trapped_chest": "陷阱箱",
}


def template_of(sname: str):
    p = POOL / f"{sname}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    for e in d.get("elements", []):
        el = e.get("element", e)
        loc = el.get("location")
        if loc:
            return loc.split(":")[-1]
    return None


def spacing_of(sname: str):
    p = SSET / f"{sname}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("placement", {}).get("spacing")


def analyze(nbt_name: str) -> dict:
    p = NBT / f"{nbt_name}.nbt"
    if not p.exists():
        return {}
    root = nbtlib.load(p).root if hasattr(nbtlib.load(p), "root") else nbtlib.load(p)
    size = [int(x) for x in root["size"]]
    pal = root["palette"]
    blocks = root["blocks"]

    cnt = Counter()
    for b in blocks:
        idx = int(b["state"])
        cnt[str(pal[idx]["Name"]).split(":")[-1]] += 1

    solid = sum(v for k, v in cnt.items() if k != "air")
    watch = {zh: cnt.get(en, 0) for en, zh in WATCH.items() if cnt.get(en, 0)}

    # 主要建材（排除空气、刷怪笼、箱子等功能方块）
    skip = {"air", "spawner", "chest", "barrel", "trapped_chest", "wall_torch",
            "structure_block", "torch", "dirt"}
    materials = [(k, v) for k, v in cnt.most_common() if k not in skip][:5]

    return {
        "nbt": nbt_name,
        "size": size,
        "volume": size[0] * size[1] * size[2],
        "blocks_total": len(blocks),
        "blocks_solid": solid,
        "palette_size": len(pal),
        "watch": watch,
        "materials": materials,
        "entities": len(root.get("entities", [])),
    }


STRUCTS = sorted(p.stem for p in SSET.glob("*.json"))

data = {}
for s in STRUCTS:
    tpl = template_of(s)
    if not tpl:
        continue
    info = analyze(tpl)
    if not info:
        continue
    info["template"] = tpl
    info["spacing"] = spacing_of(s)
    data[s] = info

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"解析 {len(data)} 个结构 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)\n")

print(f"{'结构':<24}{'尺寸':<16}{'实心':>7}{'刷怪笼':>7}{'箱子':>6}{'实体':>5}")
for s, d in sorted(data.items(), key=lambda x: -x[1]["volume"]):
    sz = "×".join(str(x) for x in d["size"])
    sp = d["watch"].get("刷怪笼", 0)
    ch = d["watch"].get("箱子", 0)
    print(f"  {s:<22}{sz:<16}{d['blocks_solid']:>7}{sp:>7}{ch:>6}{d['entities']:>5}")
