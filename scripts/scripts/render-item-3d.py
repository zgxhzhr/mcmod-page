#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Minecraft 的 Blockbench/Java 物品模型渲染成 32×32 图标。

支持：elements[].from/to（像素坐标，0-16）、faces[].uv（纹理 UV，0-16）、
display.gui 的旋转。

做法是正交投影 + 画家算法（按面中心的相机深度排序），法线背面的面剔除。
输出 32×32，对应 GUI 里物品图标的样子。
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")


def rot_matrix(rx: float, ry: float, rz: float):
    """按 Minecraft 的显示顺序构造旋转矩阵（先 X，再 Y，最后 Z）。"""
    rx, ry, rz = map(math.radians, (rx, ry, rz))
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    # Rz * Ry * Rx
    Rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    Ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    Rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]

    def mul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

    return mul(Rz, mul(Ry, Rx))


def apply(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


FACE_DIRS = {
    "north": (0, 0, -1), "south": (0, 0, 1),
    "east": (1, 0, 0), "west": (-1, 0, 0),
    "up": (0, 1, 0), "down": (0, -1, 0),
}

# 每个 face 的四个角（在 from/to 构成的立方体里）
FACE_CORNERS = {
    "north": [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
    "south": [(1, 0, 1), (0, 0, 1), (0, 1, 1), (1, 1, 1)],
    "east": [(1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)],
    "west": [(0, 0, 1), (0, 0, 0), (0, 1, 0), (0, 1, 1)],
    "up": [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)],
    "down": [(0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0)],
}


def collect_faces(model: dict, texture: Image.Image):
    """把模型拆成「带世界坐标和 UV 的面」列表。"""
    elems = model.get("elements", [])
    # 模型坐标以 8 为中心（MC 的模型空间 0-16，中心 8）
    faces = []
    for el in elems:
        frm = el.get("from", [0, 0, 0])
        to = el.get("to", [16, 16, 16])
        for fname, fdef in (el.get("faces") or {}).items():
            if fname not in FACE_CORNERS:
                continue
            uv = fdef.get("uv")
            if not uv:
                continue
            corners = []
            for c in FACE_CORNERS[fname]:
                x = frm[0] + (to[0] - frm[0]) * c[0] - 8
                y = frm[1] + (to[1] - frm[1]) * c[1] - 8
                z = frm[2] + (to[2] - frm[2]) * c[2] - 8
                corners.append([x, y, z])
            faces.append({
                "dir": FACE_DIRS[fname],
                "corners": corners,
                # UV 是 [u1,v1,u2,v2]，单位 0-16
                "uv": uv,
                "texture": texture,
            })
    return faces


def render(model_path: Path, texture_path: Path, out_path: Path, size: int = 32):
    model = json.loads(model_path.read_text(encoding="utf-8"))
    # 解析纹理引用：模型里 face.texture 是 "#0"，映射到实际文件
    tex = Image.open(texture_path).convert("RGBA")
    tex_w, tex_h = tex.size

    rot = (model.get("display", {}).get("gui", {}).get("rotation") or [0, 0, 0])
    M = rot_matrix(*rot)

    faces = collect_faces(model, tex)

    # 旋转所有角
    for f in faces:
        f["rc"] = [apply(M, c) for c in f["corners"]]
        f["rdir"] = apply(M, f["dir"])

    # 背面剔除：视线方向 (0,0,-1)（相机在 +z 看 -z）
    visible = [f for f in faces if f["rdir"][2] > 1e-6]

    # 投影：正交，去掉 z
    xs = [p[0] for f in visible for p in f["rc"]]
    ys = [p[1] for f in visible for p in f["rc"]]
    if not xs:
        print(f"  ⚠ 没有可见面：{model_path.name}")
        return None
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span = max(max_x - min_x, max_y - min_y)
    if span <= 0:
        span = 1
    scale = size / span
    ox = (size - (max_x - min_x) * scale) / 2
    oy = (size - (max_y - min_y) * scale) / 2

    # 画家算法：按面中心 z 从小到大（远的先画）
    visible.sort(key=lambda f: sum(p[2] for p in f["rc"]) / 4)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = out.load()

    for f in visible:
        # 面四角映射到像素坐标（y 翻转：MC 的 y 向上）
        pts = []
        for p in f["rc"]:
            sx = ox + (p[0] - min_x) * scale
            sy = oy + (max_y - p[1]) * scale
            pts.append((sx, sy))

        u1, v1, u2, v2 = f["uv"]
        # 每个面按两个方向做双线性采样，铺满该面的像素
        for i in range(size):
            for j in range(size):
                if not point_in_quad((i + 0.5, j + 0.5), pts):
                    continue
                # 求该像素在四边形里的参数 (a,b)
                ab = quad_params((i + 0.5, j + 0.5), pts)
                if ab is None:
                    continue
                a, b = ab
                u = u1 + (u2 - u1) * a
                v = v1 + (v2 - v1) * b
                tx = int(u / 16 * tex_w) % tex_w
                ty = int(v / 16 * tex_h) % tex_h
                r, g, bl, al = f["texture"].getpixel((tx, ty))
                if al == 0:
                    continue
                px[i, j] = (r, g, bl, al)

    out.save(out_path)
    print(f"  {out_path.name}  ← {model_path.name} + {texture_path.name}  "
          f"({len(visible)}/{len(faces)} 面可见)")
    return out


def point_in_quad(p, quad, eps=1e-9):
    """凸四边形内点判定（同向叉积）。"""
    sign = None
    for i in range(4):
        a = quad[i]
        b = quad[(i + 1) % 4]
        cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        if abs(cross) < eps:
            continue
        s = cross > 0
        if sign is None:
            sign = s
        elif s != sign:
            return False
    return True


def quad_params(p, quad):
    """求点 p 在四边形里的参数 (a,b)，a 沿 0→1 边，b 沿 0→3 边。"""
    o = quad[0]
    ex = (quad[1][0] - o[0], quad[1][1] - o[1])
    ey = (quad[3][0] - o[0], quad[3][1] - o[1])
    dx = (p[0] - o[0], p[1] - o[1])
    det = ex[0] * ey[1] - ex[1] * ey[0]
    if abs(det) < 1e-9:
        return None
    a = (dx[0] * ey[1] - dx[1] * ey[0]) / det
    b = (ex[0] * dx[1] - ex[1] * dx[0]) / det
    return a, b


def main() -> int:
    jar = BASE / "hdp"
    assets = jar / "assets/headphones"
    outdir = BASE / "hdp-icons"
    outdir.mkdir(exist_ok=True)

    jobs = [
        ("headphones", assets / "models/custom/headphones.json",
         assets / "textures/blocks/hphone.png"),
        ("headphones_control", assets / "models/custom/headphone_control.json",
         assets / "textures/blocks/texture.png"),
    ]
    for name, mp, tp in jobs:
        if not mp.exists() or not tp.exists():
            print(f"  缺文件：{mp} / {tp}")
            continue
        render(mp, tp, outdir / f"{name}.png", 32)
        # 放大版便于查看
        im = Image.open(outdir / f"{name}.png")
        im.resize((128, 128), Image.NEAREST).save(outdir / f"{name}-128.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
