#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 Minecraft 的刷怪蛋渲染逻辑生成图标。

原版模型 template_spawn_egg.json：
  parent = item/generated
  layer0 = item/spawn_egg          （蛋身，tint index 0 = primary color）
  layer1 = item/spawn_egg_overlay  （斑点，tint index 1 = secondary color）

渲染规则：Minecraft 的 item tint 是乘法——纹理灰度值 × 染色值 / 255。
所以生成 = 两张纹理各乘自己的颜色后叠加，再 NEAREST 放大到 32。
"""
import base64
import io
import json
import sys
import urllib.request
import ssl
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
CDN = "https://gcore.jsdelivr.net/gh/misode/mcmeta@1.18.2-assets/assets/minecraft/textures/item/"


def fetch(name: str) -> Image.Image:
    p = BASE / f"vanilla-{name}"
    if not p.exists():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(CDN + name, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            p.write_bytes(r.read())
        print(f"  下载 {name}  {p.stat().st_size} 字节")
    return Image.open(p).convert("RGBA")


def tint(layer: Image.Image, color: int) -> Image.Image:
    """按 Minecraft 规则做乘法染色：rgb_out = rgb_tex * rgb_color / 255"""
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    for y in range(layer.height):
        for x in range(layer.width):
            lr, lg, lb, la = layer.getpixel((x, y))
            if la == 0:
                continue
            out.putpixel((x, y), (lr * r // 255, lg * g // 255, lb * b // 255, la))
    return out


def compose(primary: int, secondary: int, size: int = 32) -> str:
    base = tint(fetch("spawn_egg.png"), primary)
    over = tint(fetch("spawn_egg_overlay.png"), secondary)
    out = Image.alpha_composite(base, over)
    out = out.resize((size, size), Image.NEAREST)
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    # 模组里所有刷怪蛋用同一组颜色：primary=0（黑）、secondary=0xFFFFFF（白）
    b64 = compose(0, 0xFFFFFF, 32)

    # 预览
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    img.resize((128, 128), Image.NEAREST).save(BASE / "spawn-egg-render-128.png")
    print(f"生成 {img.size} 图标，预览：{BASE / 'spawn-egg-render-128.png'}")
    print(f"base64 长度 {len(b64)}")

    # 写回刷怪蛋 JSON
    p = BASE / "cds-新增刷怪蛋-4397.json"
    rows = json.loads(p.read_text(encoding="utf-8"))
    for r in rows:
        r["icon32"] = b64
        r["remark"] = ("Crafting Dead: Survival 补齐刷怪蛋资料页：中文名取自 lang/zh_cn.json。"
                       "图标按 Minecraft 原版刷怪蛋的渲染规则生成（spawn_egg 与 spawn_egg_overlay "
                       "两层纹理分别乘以模组注册的 primary/secondary 颜色），"
                       "颜色取自 SurvivalItems 里的 ForgeSpawnEggItem 构造参数。辛苦喵呜机了")
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写回 {len(rows)} 条刷怪蛋")

    # 存一份参考图
    (BASE / "spawn-egg-icon32.png").write_bytes(base64.b64decode(b64))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
