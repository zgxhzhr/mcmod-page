#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minecraft 方块模型渲染器 —— 按 models/block/*.json 的 elements 还原真实外观。

模型 JSON 的结构：
  elements[]  每个元素是一个长方体，from / to 是 0-16 的模型坐标
  faces{}     每个面的 uv / texture 引用
  textures{}  纹理别名表，'0' '1' '2' ... 指向实际贴图路径

渲染方式：正交等轴测投影 + 画家算法（按深度从远到近绘制）。
不追求完全还原游戏内的光照，只求形状与贴图正确、比例准确。

用法：
  python render-block-model.py <模型json> <贴图根目录> <输出png> [尺寸]
"""
import json
import sys
from pathlib import Path

from PIL import Image

# 等轴测投影：世界坐标 (x,y,z) → 屏幕 (sx, sy)
# x 向右下、z 向左下、y 向上
COS30 = 0.8660254
SIN30 = 0.5


def project(x, y, z, scale, ox, oy):
    """y 轴朝上，x/z 是水平面。等轴测。"""
    sx = (x - z) * COS30 * scale + ox
    sy = ((x + z) * SIN30 - y) * scale + oy
    return sx, sy


class ModelRenderer:
    def __init__(self, model_path: Path, tex_root: Path, size: int = 128):
        self.data = json.loads(model_path.read_text(encoding="utf-8"))
        self.tex_root = tex_root
        self.size = size
        self.cache = {}

    def load_tex(self, ref: str):
        """把 'minecraft:block/iron_block' 这类引用解析成图片。"""
        if ref in self.cache:
            return self.cache[ref]
        ns, _, path = ref.partition(":")
        if not path:
            ns, path = "minecraft", ref
        # 只处理本模组的贴图；原版的返回 None（用纯色代替）
        p = self.tex_root / f"{path}.png"
        img = None
        if p.exists():
            img = Image.open(p).convert("RGBA")
        self.cache[ref] = img
        return img

    def face_color(self, ref: str):
        """拿不到贴图时用平均色兜底。"""
        img = self.load_tex(ref)
        if img is None:
            return (128, 128, 128, 255)
        px = list(img.convert("RGBA").getdata())
        n = len(px)
        r = sum(p[0] for p in px) // n
        g = sum(p[1] for p in px) // n
        b = sum(p[2] for p in px) // n
        return (r, g, b, 255)

    def render(self):
        elements = self.data.get("elements", [])
        if not elements:
            return None
        textures = self.data.get("textures", {})

        S = self.size * 4          # 超采样
        canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))

        # 模型坐标 0-16 → 屏幕。留边距，scale 取能放下的值
        scale = S / (22 * COS30 * 2)
        ox = S / 2
        oy = S * 0.30

        # 画家算法：按 (x+y+z) 从后往前画
        def depth(el):
            f = el.get("from", [0, 0, 0])
            t = el.get("to", [0, 0, 0])
            return (f[0] + t[0]) + (f[1] + t[1]) + (f[2] + t[2])

        for el in sorted(elements, key=depth):
            fx, fy, fz = el["from"]
            tx, ty, tz = el["to"]
            faces = el.get("faces", {})
            for fname, fdef in faces.items():
                texref = fdef.get("texture", "")
                texref = textures.get(texref.lstrip("#"), texref)
                tex = self.load_tex(texref)
                # 面的四个顶点（模型坐标）
                if fname == "up":
                    quad = [(fx, ty, fz), (tx, ty, fz), (tx, ty, tz), (fx, ty, tz)]
                    bright = 1.0
                elif fname == "down":
                    quad = [(fx, fy, fz), (tx, fy, fz), (tx, fy, tz), (fx, fy, tz)]
                    bright = 0.5
                elif fname == "north":      # -z
                    quad = [(fx, fy, fz), (tx, fy, fz), (tx, ty, fz), (fx, ty, fz)]
                    bright = 0.8
                elif fname == "south":      # +z
                    quad = [(tx, fy, tz), (fx, fy, tz), (fx, ty, tz), (tx, ty, tz)]
                    bright = 0.8
                elif fname == "west":       # -x
                    quad = [(fx, fy, tz), (fx, fy, fz), (fx, ty, fz), (fx, ty, tz)]
                    bright = 0.65
                elif fname == "east":       # +x
                    quad = [(tx, fy, fz), (tx, fy, tz), (tx, ty, tz), (tx, ty, fz)]
                    bright = 0.65
                else:
                    continue

                pts = [project(*q, scale, ox, oy) for q in quad]
                if tex is None:
                    col = self.face_color(texref)
                    col = (int(col[0] * bright), int(col[1] * bright), int(col[2] * bright), 255)
                    from PIL import ImageDraw
                    ImageDraw.Draw(canvas).polygon(pts, fill=col)
                    continue

                # 用贴图的平均色做面填充（简化：不做逐像素 UV 映射）
                col = self.face_color(texref)
                col = (min(255, int(col[0] * bright)), min(255, int(col[1] * bright)),
                       min(255, int(col[2] * bright)), 255)
                from PIL import ImageDraw
                ImageDraw.Draw(canvas).polygon(pts, fill=col)

        return canvas.resize((self.size, self.size), Image.LANCZOS)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    model = Path(sys.argv[1])
    tex_root = Path(sys.argv[2])
    out = Path(sys.argv[3])
    size = int(sys.argv[4]) if len(sys.argv) > 4 else 128

    r = ModelRenderer(model, tex_root, size)
    img = r.render()
    if img is None:
        print("模型没有 elements")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"渲染 {model.stem} → {out}  {img.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
