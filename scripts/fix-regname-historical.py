#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补历史交付里空着的 regname / ename（按新规则「必填」）。

覆盖：
  tdv-自然生成-15221.json   3 条
  prom-自然生成-5300.json   7 条

rlbt-自然生成-28249.json 是「一页对应多个结构」的分组页，另行处理。
"""
import json
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")

# tdv：结构 id 直接来自 data/seavil/worldgen/structure/
TDV = {
    "undersea_village": ("seavil:undersea_village", "Undersea Village"),
    "undersea_village_skylands": ("seavil:undersea_village_skylands", "Undersea Village (Skylands)"),
    # 「村庄部件」对应的是 undersea_village 的模板池集合，注册名挂到结构上
    "village_parts": ("seavil:undersea_village", "Undersea Village (Parts)"),
}

# prom：生物群系 5 个 + 结构 1 个 + 地物 1 个
PROM = {
    "biome_blush_sakura_grove": ("promenade:blush_sakura_grove", "Blush Sakura Grove"),
    "biome_cotton_sakura_grove": ("promenade:cotton_sakura_grove", "Cotton Sakura Grove"),
    "biome_carnelian_treeway": ("promenade:carnelian_treeway", "Carnelian Treeway"),
    "biome_glacarian_taiga": ("promenade:glacarian_taiga", "Glacarian Taiga"),
    "biome_dark_amaranth_forest": ("promenade:dark_amaranth_forest", "Dark Amaranth Forest"),
    "structure_dark_forest_witch_hut": (
        "promenade:dark_forest_witch_hut", "Dark Forest Witch Hut"),
    # 「地物与植被」是一整组 placed_feature，挂到该群系的植被地物上
    "features": ("promenade:dark_amaranth_forest_vegetation", "Dark Amaranth Forest Vegetation"),
}


def patch(fname: str, table: dict) -> None:
    p = BASE / fname
    rows = json.loads(p.read_text(encoding="utf-8"))
    miss = []
    for r in rows:
        meta = table.get(r["id"])
        if not meta:
            miss.append(r["id"])
            continue
        r["regname"], r["ename"] = meta
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{fname}: 补 {len(rows) - len(miss)}/{len(rows)} 条" + (f"  未匹配 {miss}" if miss else ""))


if __name__ == "__main__":
    patch("tdv-自然生成-15221.json", TDV)
    patch("prom-自然生成-5300.json", PROM)
