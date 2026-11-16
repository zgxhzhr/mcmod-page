#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dungeons 2（classId 2475）6 个方块的等轴测图标 + 批量新增 JSON。

方块模型分三种父类型，各自取不同面的纹理：
  cube_all           → 六面同图
  cube_bottom_top    → top / bottom / side
  orientable         → top / front / side
  block/block        → 自定义元素（mining_chest）

等轴测：上 1.0、左 0.8、右 0.6 明暗，512 超采样后缩到 128/32。
"""
import base64
import io
import json
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
BLK = BASE / "vanilla-block-tex"
MOD = BASE / "dg2/assets/dungeons2/textures/block"
OUTICON = BASE / "dg2-block-icons"
OUT = BASE / "dg2-方块导入-2475.json"
NS = "dungeons2"

OUTICON.mkdir(exist_ok=True)

# 方块 → 六个面的纹理名（None 表示用 side）
BLOCKS = [
    {
        "id": "mob_set_spawner", "name": "Mob Set Spawner",
        "tex": {"top": "spawner", "left": "spawner", "right": "spawner"},
        "html": "<p>Mob Set Spawner 是 Dungeons 2 用来按生物套装刷怪的方块。</p>"
                "<p><strong>作用</strong>：每次触发时从所属的生物套装里按权重随机挑一种生成，"
                "不会一直刷同一种怪。套装本身在 mob_sets 下的 JSON 里定义。</p>"
                "<p><strong>获取</strong>：创造模式物品栏。地牢生成时由结构里的 Spawner Marker 替换而来，"
                "玩家正常探索时看不到它。</p>",
    },
    {
        "id": "spawner_marker", "name": "Spawner Marker",
        "tex": {"top": "spawner", "left": "spawner", "right": "spawner"},
        "html": "<p>Spawner Marker 是 Dungeons 2 的结构标记方块，用来在预制件里标出刷怪点。</p>"
                "<p><strong>作用</strong>：标记这个位置要生成刷怪笼。地牢生成完后它会被替换成 "
                "Mob Set Spawner，具体刷什么由结构挂的生物套装决定。</p>"
                "<p><strong>获取</strong>：创造模式物品栏。给做地牢结构的人用，正常玩见不到。</p>",
    },
    {
        "id": "chest_marker", "name": "Chest Marker",
        "tex": {"top": "oak_planks", "left": "oak_planks", "right": "barrel_top"},
        "html": "<p>Chest Marker 是 Dungeons 2 的结构标记方块，用来在预制件里标出箱子位置。</p>"
                "<p><strong>作用</strong>：标记这个位置要放箱子。生成时会按结构的战利品配置换成实际箱子，"
                "装备 Treasure2 时还支持指定换成 Treasure2 的箱子。</p>"
                "<p><strong>获取</strong>：创造模式物品栏。给做地牢结构的人用。</p>",
    },
    {
        "id": "pot_marker", "name": "Pot Marker",
        "tex": {"top": "orange_glazed_terracotta", "left": "terracotta", "right": "terracotta"},
        "html": "<p>Pot Marker 是 Dungeons 2 的结构标记方块，用来在预制件里标出罐子位置。</p>"
                "<p><strong>作用</strong>：标记这个位置要放罐子。生成时替换成陶罐，"
                "罐子的战利品表在 loot_tables/pots 下。</p>"
                "<p><strong>获取</strong>：创造模式物品栏。给做地牢结构的人用。</p>",
    },
    {
        "id": "sarcophagus_marker", "name": "Sarcophagus Marker",
        "tex": {"top": "chiseled_stone_bricks", "left": "stone_bricks", "right": "bone_block_top"},
        "html": "<p>Sarcophagus Marker 是 Dungeons 2 的结构标记方块，用来在预制件里标出石棺位置。</p>"
                "<p><strong>作用</strong>：标记这个位置要放石棺。石棺是地牢里的一种特殊容器，"
                "通常出现在墓室类结构里，产出与普通箱子不同。</p>"
                "<p><strong>获取</strong>：创造模式物品栏。给做地牢结构的人用。</p>",
    },
    {
        "id": "mining_chest", "name": "Mining Chest",
        # 模型是 16 个元素的箱子，直接贴 UV 也会碎；particle 指定的是 iron_block，用铁块近似
        "tex": {"top": "iron_block", "left": "iron_block", "right": "iron_block"},
        "html": "<p>Mining Chest 是 Dungeons 2 的采矿箱，用来补偿地牢挖掉的矿石。</p>"
                "<p><strong>作用</strong>：地牢从岩层里开挖，原本存在的矿石随之消失。"
                "每座地牢生成一个采矿箱，按开挖体积与深度返还一部分资源。</p>"
                "<p><strong>产出</strong>：小型约 67 件、中型约 216 件、大型约 261 件，"
                "以煤、铜、铁为主。钻石上限 3 个，仅大型地牢挖至世界底部时可能达成。</p>"
                "<p><strong>限制</strong>：采矿箱的产出与 BOSS 箱刻意错开，"
                "不会开出附魔书、钻石装备或金苹果。</p>"
                "<p><strong>获取</strong>：地牢内固定生成一个，另有创造模式物品栏版本。"
                "不是可合成的方块。</p>",
    },
]

SIZE = 512
ISO = 32


def face_texture(name: str, self_tex: bool) -> Image.Image:
    p = (MOD if self_tex else BLK) / f"{name}.png"
    if not p.exists():
        # 找不到就用品红占位
        img = Image.new("RGBA", (16, 16), (248, 0, 248, 255))
        return img
    return Image.open(p).convert("RGBA")


def shade(img: Image.Image, factor: float) -> Image.Image:
    a = img.copy()
    px = a.load()
    for y in range(a.height):
        for x in range(a.width):
            r, g, b, al = px[x, y]
            px[x, y] = (int(r * factor), int(g * factor), int(b * factor), al)
    return a


def draw_face(canvas: Image.Image, tex: Image.Image, quad, factor: float, size: int):
    """把纹理按透视贴到四边形上（简化：按包围盒逐像素映射）。"""
    tex = shade(tex, factor)
    tw, th = tex.size
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    if x1 <= x0 or y1 <= y0:
        return
    small = tex.resize((max(1, int(x1 - x0)), max(1, int(y1 - y0))), Image.NEAREST)
    # 用四边形的掩码裁剪
    mask = Image.new("L", (size, size), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(mask)
    d.polygon([(p[0], p[1]) for p in quad], fill=255)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    layer.paste(small, (int(x0), int(y0)))
    canvas.paste(layer, (0, 0), mask)


def render_iso(top: Image.Image, left: Image.Image, right: Image.Image, out_size: int = 32) -> str:
    """标准等轴测立方体：上菱形 + 左面 + 右面。"""
    S = SIZE
    # 立方体在画布上的顶点
    cx, cy = S / 2, S / 2
    w = S * 0.40          # 半宽
    h = w                 # 竖直方向偏移（保持 2w 总高）
    top_p = [(cx, cy - h), (cx + w, cy - h / 2), (cx, cy), (cx - w, cy - h / 2)]
    left_p = [(cx - w, cy - h / 2), (cx, cy), (cx, cy + h), (cx - w, cy + h / 2)]
    right_p = [(cx, cy), (cx + w, cy - h / 2), (cx + w, cy + h / 2), (cx, cy + h)]

    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw_face(canvas, top, top_p, 1.0, S)
    draw_face(canvas, left, left_p, 0.8, S)
    draw_face(canvas, right, right_p, 0.6, S)

    img = canvas.resize((out_size, out_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    rows = []
    for b in BLOCKS:
        t = b["tex"]
        self_tex = b.get("self_tex", False)
        top = face_texture(t["top"], self_tex)
        left = face_texture(t["left"], self_tex)
        right = face_texture(t["right"], self_tex)

        icon32 = render_iso(top, left, right, 32)
        icon128 = render_iso(top, left, right, 128)

        # 存一份预览
        (OUTICON / f"{b['id']}-128.png").write_bytes(base64.b64decode(icon128))

        rows.append({
            "id": b["id"],
            "name": b["name"],
            "ename": "",
            "regname": f"{NS}:{b['id']}",
            "category": "方块" if b["id"] in ("mob_set_spawner", "mining_chest") else "结构标记",
            "type": "物品/方块",
            "maxstack": 1,
            "remark": ("Dungeons 2 新增方块资料页：名称取自 lang/en_us.json。"
                       "作用与生成时机依据本模组的方块注册与 structures 下的结构配置。辛苦喵呜机了"),
            "html": b["html"],
            "icon32": icon32,
            "icon128": icon128,
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    print(f"预览图: {OUTICON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
