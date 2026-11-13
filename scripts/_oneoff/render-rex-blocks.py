#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Realistic Explosives（classId 24724）方块等轴测图标渲染。

方块的纹理在 textures/blocks/ 下，是 64×64 的平面图，直接当图标会被审核判
「单面纹理图」。这里按 skill 的图标规范渲染成等轴测立方体：
顶面 1.0 / 左面 0.8 / 右面 0.6 明暗。
"""
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
TEX = BASE / "rex/assets/realistic_explosives/textures"
OUT = BASE / "rex-block-icons"
OUT.mkdir(exist_ok=True)


def shade(img: Image.Image, f: float) -> Image.Image:
    a = img.copy()
    px = a.load()
    for y in range(a.height):
        for x in range(a.width):
            r, g, b, al = px[x, y]
            px[x, y] = (int(r * f), int(g * f), int(b * f), al)
    return a


def iso(texture: Path, size: int = 128) -> Image.Image:
    """把一张方块纹理渲染成等轴测立方体。"""
    tex = Image.open(texture).convert("RGBA")
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


# 方块 → 纹理文件
BLOCKS = {
    # 矿石
    "ore_sulfur": TEX / "blocks/ores/sulfur.png",
    "ore_nitratine": TEX / "blocks/ores/nitratine.png",
    "ore_uraninite": TEX / "blocks/ores/uraninite.png",
    "ore_ilmenite": TEX / "blocks/ores/ilmenite.png",
    "ore_aluminosilicate": TEX / "blocks/ores/aluminosilicate.png",
    "ore_magnesite": TEX / "blocks/ores/magnesite.png",
    # 建材
    "concrete": TEX / "blocks/building/concrete.png",
    "hardenedConcrete": TEX / "blocks/building/hardenedConcrete.png",
    "reinforcedConcrete": TEX / "blocks/building/reinforcedConcrete.png",
    "hardenedGlass": TEX / "blocks/building/hardenedGlass.png",
    "reinforcedGlass": TEX / "blocks/building/reinforcedGlass.png",
    "lockedDoor": TEX / "blocks/building/lockedDoor_upper.png",
    # 反应容器
    "reactionVessel": TEX / "blocks/reactionVessel_side.png",
    # 炸药方块
    "APEX": TEX / "blocks/explosives/APEX.png",
    "HMTD": TEX / "blocks/explosives/HMTD.png",
    "leadAzide": TEX / "blocks/explosives/leadAzide.png",
    "APAN": TEX / "blocks/explosives/APAN.png",
    "ANFO": TEX / "blocks/explosives/ANFO.png",
    "ANNM": TEX / "blocks/explosives/ANNM.png",
    "AMMONAL": TEX / "blocks/explosives/AMMONAL.png",
    "dynamite": TEX / "blocks/explosives/dynamite.png",
    "RDX": TEX / "blocks/explosives/RDX.png",
    "CL20": TEX / "blocks/explosives/CL20.png",
    "ONC": TEX / "blocks/explosives/ONC.png",
    "astroliteG": TEX / "blocks/explosives/astroliteG.png",
    "PETN": TEX / "blocks/explosives/PETN.png",
    "ETN": TEX / "blocks/explosives/ETN.png",
    "FLASH": TEX / "blocks/explosives/FLASH.png",
    "ATOMIC": TEX / "blocks/explosives/ATOMIC.png",
    # 流体（用静帧）
    "acetone_f": TEX / "blocks/fluids/acetone_s.png",
    "ammonia_f": TEX / "blocks/fluids/ammonia_s.png",
    "glycerine_f": TEX / "blocks/fluids/glycerine_s.png",
    "hydrochloricAcid_f": TEX / "blocks/fluids/hydrochloricAcid_s.png",
    "hydrogenPeroxide_f": TEX / "blocks/fluids/hydrogenPeroxide_s.png",
    "nitricAcid_f": TEX / "blocks/fluids/nitricAcid_s.png",
    "nitroGlycerine_f": TEX / "blocks/fluids/nitroGlycerine_s.png",
    "sulfuricAcid_f": TEX / "blocks/fluids/sulfuricAcid_s.png",
    "distilledWater_f": TEX / "blocks/fluids/distilledWater_s.png",
    "toxicWaste_f": TEX / "blocks/fluids/toxicWaste_s.png",
    # 地雷
    "mine": TEX / "blocks/explosives/mine.png",
}


def main() -> int:
    ok, miss = 0, []
    for name, path in BLOCKS.items():
        if not path.exists():
            miss.append(f"{name} → {path.relative_to(TEX)}")
            continue
        iso(path).save(OUT / f"{name}-128.png")
        ok += 1
    print(f"渲染 {ok} 个方块图标 → {OUT}")
    if miss:
        print(f"缺失 {len(miss)} 个:")
        for m in miss:
            print(f"  {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
