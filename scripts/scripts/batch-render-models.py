#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量渲染模组方块模型 —— 支持并行。

用法：
  python batch-render-models.py <清单txt> <资源根目录> <输出目录> <尺寸> [并发数]

清单 txt：每行一个模型引用，可以是
  - 直接模型路径      nemos-carpentry:block/oak_chair
  - 方块 id 自动解析   blockstate:nemos-carpentry:oak_chair
输出文件名取 <namespace>__<path 用 / 换 _>.png
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module

_render_mod = None


def _worker(args):
    ref, roots, outdir, size = args
    global _render_mod
    if _render_mod is None:
        _render_mod = import_module("render-mc-model")
    from pathlib import Path as P

    AssetSource = _render_mod.AssetSource
    render = _render_mod.render
    model_of_blockstate = _render_mod.model_of_blockstate

    assets = AssetSource([P(r) for r in roots])
    # 输出文件名默认用模型路径；给了 blockstate 时改用方块 id，
    # 因为门的模型路径带 _bottom_left 这类后缀，用模型名会和方块 id 对不上。
    name = ref
    if ref.startswith("blockstate:"):
        bid = ref.split(":", 1)[1]      # 例 nemos-carpentry:oak_glass_door
        found = model_of_blockstate(assets, bid)
        if not found:
            return (ref, "no-model", "")
        ns, _, bname = bid.partition(":")
        name = f"{ns}:block/{bname}"     # 统一成 nemos-carpentry:block/oak_glass_door
        ref2 = found
    else:
        ref2 = ref

    img = render(ref2, assets, size)
    if img is None:
        return (ref, "no-elements", "")

    safe = name.replace(":", "__").replace("/", "_").replace(".", "_")
    out = P(outdir) / f"{safe}.png"
    img.save(out)
    return (ref, "ok", str(out))


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return 1
    listfile = Path(sys.argv[1])
    roots = sys.argv[2].split(";")
    outdir = Path(sys.argv[3])
    size = int(sys.argv[4])
    workers = int(sys.argv[5]) if len(sys.argv) > 5 else 6
    outdir.mkdir(parents=True, exist_ok=True)

    refs = [ln.strip() for ln in listfile.read_text(encoding="utf-8").splitlines() if ln.strip()]
    print(f"共 {len(refs)} 个模型，{workers} 并发，输出 {size}px → {outdir}")

    ok = fail = 0
    jobs = [(r, roots, str(outdir), size) for r in refs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, (ref, status, out) in enumerate(ex.map(_worker, jobs), 1):
            if status == "ok":
                ok += 1
            else:
                fail += 1
                if fail <= 15:
                    print(f"  ✗ {ref}: {status}")
            if i % 50 == 0 or i == len(refs):
                print(f"  进度 {i}/{len(refs)}  成功 {ok}  失败 {fail}")

    print(f"\n完成：成功 {ok}，失败 {fail}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
