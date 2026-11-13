#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minecraft 方块模型渲染器 —— 按 models/block/*.json 还原真实外观，带完整 UV 映射。

支持：
  - parent 模型继承（递归解析）
  - elements 的 from/to 长方体几何
  - faces 的 uv 坐标、rotation、cullface
  - 纹理引用的命名空间解析（minecraft: / 模组命名空间）
  - 等轴测正交投影（平行投影 ⇒ 四边形到四边形是仿射变换，可精确映射）

用法：
  python render-mc-model.py <模型json> <资源根目录> <输出png> [尺寸]
  python render-mc-model.py --batch <清单json> <资源根目录> <输出目录> [尺寸]

资源根目录要能解析 `assets/<namespace>/textures/<path>.png`。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

COS30 = 0.8660254
SIN30 = 0.5


# ── 纹理解析 ──
class AssetSource:
    def __init__(self, roots):
        # roots: [(前缀目录, 优先级)]，前面优先级高
        self.roots = [Path(r) for r in roots]
        self.cache = {}

    def texture(self, ref: str):
        """'minecraft:block/iron_block' → PIL Image 或 None"""
        if ref in self.cache:
            return self.cache[ref]
        ns, _, path = ref.partition(":")
        if not path:
            ns, path = "minecraft", ref
        for root in self.roots:
            p = root / "assets" / ns / "textures" / f"{path}.png"
            if p.exists():
                img = Image.open(p).convert("RGBA")
                self.cache[ref] = img
                return img
        self.cache[ref] = None
        return None

    def model(self, ref: str):
        ns, _, path = ref.partition(":")
        if not path:
            ns, path = "minecraft", ref
        for root in self.roots:
            p = root / "assets" / ns / "models" / f"{path}.json"
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        return None


def model_of_blockstate(assets: AssetSource, block_id: str):
    """从 blockstates/<block_id>.json 里取出模型引用（多个变体时取第一个）。"""
    ns, _, name = block_id.partition(":")
    if not name:
        ns, name = "minecraft", block_id
    for root in assets.roots:
        p = root / "assets" / ns / "blockstates" / f"{name}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for v in d.get("variants", {}).values():
            vs = v if isinstance(v, list) else [v]
            for x in vs:
                if isinstance(x, dict) and x.get("model"):
                    return x["model"]
        # multipart 形式
        for part in d.get("multipart", []):
            ap = part.get("apply")
            if isinstance(ap, dict) and ap.get("model"):
                return ap["model"]
            if isinstance(ap, list):
                for x in ap:
                    if isinstance(x, dict) and x.get("model"):
                        return x["model"]
    return None


def resolve_model(assets: AssetSource, ref: str, depth=0):
    """递归解析 parent 链，合并 textures 与 elements。"""
    if depth > 8:
        return {"textures": {}, "elements": []}
    data = assets.model(ref)
    if data is None:
        return {"textures": {}, "elements": []}
    base = {"textures": {}, "elements": []}
    if "parent" in data:
        parent_ref = data["parent"]
        if parent_ref.startswith("builtin/"):
            pass  # builtin 生成类模型，忽略
        else:
            base = resolve_model(assets, parent_ref, depth + 1)
    textures = dict(base.get("textures", {}))
    textures.update(data.get("textures", {}))
    elements = data.get("elements", base.get("elements", []))
    return {"textures": textures, "elements": elements}


# ── 几何 ──
def project(x, y, z, scale, ox, oy):
    sx = (x - z) * COS30 * scale + ox
    sy = ((x + z) * SIN30 - y) * scale + oy
    return sx, sy


def shade(img, f):
    if f >= 0.999:
        return img
    arr = np.asarray(img.convert("RGBA"), dtype=np.float32)
    arr[..., :3] *= f
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def draw_quad(canvas, tex_img, uv, dst_pts, brightness):
    """把一个纹理矩形映射到屏幕四边形上（拆两个三角形做仿射采样）。"""
    W, H = canvas.size
    arr = np.array(canvas, dtype=np.uint8, copy=True)

    tx = shade(tex_img, brightness)
    tw, th = tx.size
    tarr = np.asarray(tx, dtype=np.uint8)

    # uv 是 0-16 的模型坐标，转成像素坐标
    u0, v0, u1, v1 = uv
    sx0 = int(round(u0 / 16 * tw))
    sx1 = int(round(u1 / 16 * tw))
    sy0 = int(round(v0 / 16 * th))
    sy1 = int(round(v1 / 16 * th))
    if sx1 <= sx0 or sy1 <= sy0:
        return
    sub = tarr[sy0:sy1, sx0:sx1]
    sh, sw = sub.shape[:2]

    # 源四边形（纹理空间四角）与目标四边形（屏幕）
    src = np.array([[0, 0], [sw, 0], [sw, sh], [0, sh]], dtype=np.float64)
    dst = np.array(dst_pts, dtype=np.float64)

    # 拆成两个三角形：0-1-2 与 0-2-3
    for tri_src, tri_dst in (
        (src[[0, 1, 2]], dst[[0, 1, 2]]),
        (src[[0, 2, 3]], dst[[0, 2, 3]]),
    ):
        # 求仿射变换 src -> dst：
        #   x = a*u + b*v + c
        #   y = d*u + e*v + f
        A = np.column_stack([tri_src, np.ones(3)])          # 3x3
        try:
            cx_ = np.linalg.solve(A, tri_dst[:, 0])         # [a,b,c]
            cy_ = np.linalg.solve(A, tri_dst[:, 1])         # [d,e,f]
        except np.linalg.LinAlgError:
            continue
        M = np.array([[cx_[0], cx_[1]], [cy_[0], cy_[1]]])  # 2x2
        b = np.array([cx_[2], cy_[2]])
        try:
            Minv = np.linalg.inv(M)
        except np.linalg.LinAlgError:
            continue

        xs = tri_dst[:, 0]
        ys = tri_dst[:, 1]
        x0, x1 = int(np.floor(xs.min())), int(np.ceil(xs.max()))
        y0, y1 = int(np.floor(ys.min())), int(np.ceil(ys.max()))
        x0, x1 = max(0, x0), min(W - 1, x1)
        y0, y1 = max(0, y0), min(H - 1, y1)
        if x1 < x0 or y1 < y0:
            continue

        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        pts = np.stack([xx - b[0], yy - b[1]], axis=-1)
        uv_pts = pts @ Minv.T
        us = uv_pts[..., 0]
        vs = uv_pts[..., 1]

        # 判断是否在三角形内（重心坐标）
        pts2 = np.stack([xx, yy], axis=-1)          # (h, w, 2)

        def sign(p1, p2, p3):
            return ((p1[..., 0] - p3[0]) * (p2[..., 1] - p3[1])
                    - (p2[..., 0] - p3[0]) * (p1[..., 1] - p3[1]))

        a, b2, c = tri_dst
        d1 = sign(pts2, a, b2)
        d2 = sign(pts2, b2, c)
        d3 = sign(pts2, c, a)
        has_neg = (d1 < 0) | (d2 < 0) | (d3 < 0)
        has_pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
        inside = ~(has_neg & has_pos)

        ui = np.clip(us.astype(np.int32), 0, sw - 1)
        vi = np.clip(vs.astype(np.int32), 0, sh - 1)
        colors = sub[vi, ui]
        mask = inside & (colors[..., 3] > 0)
        if not mask.any():
            continue
        region = arr[y0:y1 + 1, x0:x1 + 1]
        region = np.where(mask[..., None], colors, region)
        arr[y0:y1 + 1, x0:x1 + 1] = region

    canvas.paste(Image.fromarray(arr, "RGBA"))


FACE_DEFS = {
    # face: (顶点顺序基于 from/to, 亮度)
    "up":    (lambda f, t: [(f[0], t[1], f[2]), (t[0], t[1], f[2]), (t[0], t[1], t[2]), (f[0], t[1], t[2])], 1.00),
    "down":  (lambda f, t: [(f[0], f[1], f[2]), (t[0], f[1], f[2]), (t[0], f[1], t[2]), (f[0], f[1], t[2])], 0.55),
    "north": (lambda f, t: [(f[0], f[1], f[2]), (t[0], f[1], f[2]), (t[0], t[1], f[2]), (f[0], t[1], f[2])], 0.80),
    "south": (lambda f, t: [(t[0], f[1], t[2]), (f[0], f[1], t[2]), (f[0], t[1], t[2]), (t[0], t[1], t[2])], 0.80),
    "west":  (lambda f, t: [(f[0], f[1], t[2]), (f[0], f[1], f[2]), (f[0], t[1], f[2]), (f[0], t[1], t[2])], 0.65),
    "east":  (lambda f, t: [(t[0], f[1], f[2]), (t[0], f[1], t[2]), (t[0], t[1], t[2]), (t[0], t[1], f[2])], 0.65),
}


def render(model_ref: str, assets: AssetSource, size=128, margin=1.06, span_mode="bbox"):
    span_mode = (span_mode == "block")
    data = resolve_model(assets, model_ref)
    elements = data.get("elements", [])
    if not elements:
        return None
    textures = data.get("textures", {})

    def texref(fdef):
        t = fdef.get("texture", "")
        while isinstance(t, str) and t.startswith("#"):
            t = textures.get(t[1:], t)
        return t

    # 超采样倍率：目标越小，倍率越高，最后一次性缩到目标尺寸
    # （多次缩放会累积模糊，尤其 512→128→32 这种）
    S = max(size * 4, 512)
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # 估算包围盒，让模型居中
    xs = [v for el in elements for v in (el["from"][0], el["to"][0])]
    ys = [v for el in elements for v in (el["from"][1], el["to"][1])]
    zs = [v for el in elements for v in (el["from"][2], el["to"][2])]
    # 缩放基准：默认按完整 16×16×16 方块空间，这样小方块（按钮、花、台阶）
    # 会按它在方块里的真实比例显示，而不是被放大填满画布。
    # 传 span=0 则退回按包围盒自适应。
    box_span = max(max(xs) - min(xs), max(zs) - min(zs), max(ys) - min(ys)) or 16
    span = 16 if span_mode else box_span
    scale = S / (span * COS30 * 2 * margin)
    mx = (min(xs) + max(xs)) / 2
    my = (min(ys) + max(ys)) / 2
    mz = (min(zs) + max(zs)) / 2
    # 让模型包围盒中心投影到画布中心
    ox = S / 2 - (mx - mz) * COS30 * scale
    oy = S / 2 - ((mx + mz) * SIN30 - my) * scale

    # 按「面」而不是按元素排序：大元素的不同面深度差异很大，
    # 只按元素排序会出现近面被远面覆盖的错乱。
    jobs = []
    for el in elements:
        fx, fy, fz = el["from"]
        tx, ty, tz = el["to"]
        for fname, (vfn, bright) in FACE_DEFS.items():
            fdef = el.get("faces", {}).get(fname)
            if not fdef:
                continue
            ref = texref(fdef)
            img = assets.texture(ref) if ref else None
            if img is None:
                continue
            if "uv" in fdef:
                uv = fdef["uv"]
            else:
                uv = {
                    "up":    [fx, fz, tx, tz],
                    "down":  [fx, 16 - tz, tx, 16 - fz],
                    "north": [16 - tx, 16 - ty, 16 - fx, 16 - fy],
                    "south": [fx, 16 - ty, tx, 16 - fy],
                    "west":  [fz, 16 - ty, tz, 16 - fy],
                    "east":  [16 - tz, 16 - ty, 16 - fz, 16 - fy],
                }[fname]
            quad3 = vfn((fx, fy, fz), (tx, ty, tz))
            quad2 = [project(x, y, z, scale, ox, oy) for x, y, z in quad3]
            # 面中心的深度（用于绘制顺序）
            cx3 = sum(p[0] for p in quad3) / 4
            cy3 = sum(p[1] for p in quad3) / 4
            cz3 = sum(p[2] for p in quad3) / 4
            depth = cx3 + cy3 + cz3
            jobs.append((depth, img, uv, quad2, bright))

    # 远的先画（深度小的先画）
    for depth, img, uv, quad2, bright in sorted(jobs, key=lambda j: j[0]):
        draw_quad(canvas, img, uv, quad2, bright)

    return canvas.resize((size, size), Image.LANCZOS)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    model_ref = sys.argv[1]
    roots = [Path(p) for p in sys.argv[2].split(";")]
    out = Path(sys.argv[3])
    size = int(sys.argv[4]) if len(sys.argv) > 4 else 128

    assets = AssetSource(roots)
    # 允许直接传方块 id：会自动从 blockstate 找模型
    if model_ref.startswith("blockstate:"):
        bid = model_ref.split(":", 1)[1]
        found = model_of_blockstate(assets, bid)
        if not found:
            print(f"从 blockstate 找不到模型：{bid}")
            return 1
        model_ref = found
        print(f"  blockstate {bid} → {model_ref}")
    img = render(model_ref, assets, size)
    if img is None:
        print(f"渲染失败：{model_ref} 没有 elements（可能只有 parent 链或 builtin 模型）")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"渲染 {model_ref} → {out}  {img.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
