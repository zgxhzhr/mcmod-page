#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把方块的 top / side 贴图渲染成等轴测立体图标（mcmod 审核要求）。

依据 skill §图标规范第 2 条：方块必须交立体图标，单面贴图会被退回。
明暗：顶面 1.0 / 左面 0.8 / 右面 0.6；512 超采样后缩到目标尺寸。

用法
----
    python render-block-iso.py --top top.png --side side.png --out icon.png --size 32
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def sample(tex: Image.Image, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """最近邻采样纹理，u/v 为 0..1 的网格。"""
    arr = np.array(tex.convert("RGBA"), dtype=np.uint8)
    th, tw = arr.shape[:2]
    xi = np.clip((u * tw).astype(np.int32), 0, tw - 1)
    yi = np.clip((v * th).astype(np.int32), 0, th - 1)
    return arr[yi, xi]


def render_iso(top: Image.Image, side: Image.Image, size: int = 512) -> Image.Image:
    """渲染等轴测立方体，返回 size×size RGBA。"""
    W = H = size
    # 2:1 等轴测几何：顶面菱形半宽 w、半高 w/2；侧面高 sh
    w = size * 0.42      # 顶面半宽
    hh = w / 2.0         # 顶面半高（2:1 菱形）
    sh = w               # 侧面高 = 半宽，使总高 2w = 总宽 2w（正方形）
    cx, cy = size / 2.0, size / 2.0

    top_c = (cx, cy - sh / 2.0)          # 顶面菱形中心
    # 顶面四顶点
    p_top = (cx, top_c[1] - hh)
    p_right = (cx + w, top_c[1])
    p_bottom = (cx, top_c[1] + hh)
    p_left = (cx - w, top_c[1])

    yy, xx = np.mgrid[0:H, 0:W]
    px = xx + 0.5
    py = yy + 0.5

    out = np.zeros((H, W, 4), dtype=np.float32)

    # ── 顶面：菱形 |dx/w| + |dy/hh| <= 1 ──
    dx = px - top_c[0]
    dy = py - top_c[1]
    m_top = (np.abs(dx / w) + np.abs(dy / hh)) <= 1.0
    if m_top.any():
        u = (dx[m_top] / w + dy[m_top] / hh + 1.0) / 2.0
        v = (1.0 - dx[m_top] / w + dy[m_top] / hh) / 2.0
        px_t = sample(top, u, v).astype(np.float32) * 1.00
        out[m_top] = px_t

    # ── 左面：左上 (cx-w, cy-hh)，顶边向量 (w, hh)，左边向量 (0, sh) ──
    lx0, ly0 = p_left
    m_left = np.zeros((H, W), dtype=bool)
    s = (px - lx0) / w
    t = (py - ly0 - s * hh) / sh
    m_left = (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1)
    if m_left.any():
        px_l = sample(side, s[m_left], t[m_left]).astype(np.float32) * 0.80
        look = out[m_left]
        # 已有顶面的地方不覆盖（顶面优先）
        keep = look[:, 3] < 1
        out[m_left] = np.where(keep[:, None], px_l, look)

    # ── 右面：左上 (cx, cy-hh+hh) = p_bottom，顶边向量 (w, -hh)，左边向量 (0, sh) ──
    rx0, ry0 = p_bottom
    s2 = (px - rx0) / w
    t2 = (py - ry0 + s2 * hh) / sh
    m_right = (s2 >= 0) & (s2 <= 1) & (t2 >= 0) & (t2 <= 1)
    if m_right.any():
        px_r = sample(side, s2[m_right], t2[m_right]).astype(np.float32) * 0.60
        look = out[m_right]
        keep = look[:, 3] < 1
        out[m_right] = np.where(keep[:, None], px_r, look)

    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    return img


def fit(im: Image.Image, size: int) -> Image.Image:
    """放大用 NEAREST（保留硬边缘），缩小用 LANCZOS。"""
    if im.width < size:
        return im.resize((size, size), Image.NEAREST)
    return im.resize((size, size), Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", required=True)
    ap.add_argument("--side", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=32)
    ap.add_argument("--preview", type=int, default=128, help="额外导出的预览尺寸，0=不要")
    args = ap.parse_args()

    top = Image.open(args.top).convert("RGBA")
    side = Image.open(args.side).convert("RGBA")
    iso = render_iso(top, side, 512)

    out = Path(args.out)
    fit(iso, args.size).save(out, format="PNG", optimize=True)
    print(f"已生成 {args.size}×{args.size}：{out}")

    if args.preview:
        pv = out.with_name(out.stem + f"-{args.preview}.png")
        fit(iso, args.preview).save(pv, format="PNG", optimize=True)
        print(f"预览图 {args.preview}×{args.preview}：{pv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
