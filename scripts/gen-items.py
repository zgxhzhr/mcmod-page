#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从模组源码生成「MC百科 批量新增」用的 items.json（通用版）。

做法：扫 assets/<ns>/textures/item/*.png 拿到所有物品 id，配 lang/zh_cn.json 与
en_us.json 取中英文名，把 16x16 原版纹理用最近邻放大到 32x32 转成 base64，
拼成 mcmod-batch.user.js 需要的数据格式。

用法示例：
  python gen-items.py ^
      --assets "<模组>/src/main/resources/assets/<命名空间>" ^
      --namespace <命名空间> ^
      --category <资料分类> ^
      --maxstack 1 --damage 1 ^
      --out "items.json"

正文（html 字段）留空时，脚本只负责名称/图标/注册名；正文按 skill §6.4 另行撰写，
可用 --html-dir 指定一个「<注册id>.html」目录批量带上。
"""
import argparse
import base64
import io
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow：pip install pillow", file=sys.stderr)
    sys.exit(1)


def b64_png(img: Image.Image, size: int) -> str:
    buf = io.BytesIO()
    img.resize((size, size), Image.NEAREST).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True, help="assets/<命名空间> 目录")
    ap.add_argument("--namespace", required=True, help="注册名前缀（模组的 namespace，如 mymod）")
    ap.add_argument("--out", required=True, help="输出 items.json")
    ap.add_argument("--category", default="", help="资料分类（留空则脚本不碰分类）")
    ap.add_argument("--type", dest="type_name", default="物品/方块", help="资料类型")
    ap.add_argument("--remark", default="批量录入", help="改动附言")
    ap.add_argument("--maxstack", type=int, default=None)
    ap.add_argument("--damage", type=int, default=None)
    ap.add_argument("--size", type=int, default=32, help="图标边长，百科要求 32")
    ap.add_argument("--html-dir", default="", help="可选：<注册id>.html 目录，作为正文")
    ap.add_argument("--lore-prefix", default="", help="可选：把以该前缀开头的 lang 键拼成「游戏内描述」")
    args = ap.parse_args()

    assets = Path(args.assets)
    tex_dir = assets / "textures" / "item"
    if not tex_dir.is_dir():
        print(f"找不到纹理目录：{tex_dir}", file=sys.stderr)
        return 1

    def load_lang(name):
        p = assets / "lang" / name
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    zh, en = load_lang("zh_cn.json"), load_lang("en_us.json")
    html_dir = Path(args.html_dir) if args.html_dir else None

    rows = []
    for png in sorted(tex_dir.glob("*.png")):
        item_id = png.stem
        zh_name = zh.get(f"item.{args.namespace}.{item_id}") or zh.get(f"block.{args.namespace}.{item_id}") or ""
        en_name = en.get(f"item.{args.namespace}.{item_id}") or en.get(f"block.{args.namespace}.{item_id}") or ""

        html = ""
        if html_dir and (html_dir / f"{item_id}.html").exists():
            html = (html_dir / f"{item_id}.html").read_text(encoding="utf-8")

        if not html and args.lore_prefix:
            lore = [v for k, v in zh.items() if k.startswith(args.lore_prefix) and item_id.split("_")[0] in k]
            if lore:
                html = "<p>游戏内描述：" + "".join(lore) + "</p>"

        rec = {
            "id": item_id,
            "name": zh_name,
            "ename": en_name,
            "regname": f"{args.namespace}:{item_id}",
            "category": args.category,
            "type": args.type_name,
            "remark": args.remark,
            "html": html,
            "icon32": b64_png(Image.open(png).convert("RGBA"), args.size),
        }
        if args.maxstack is not None:
            rec["maxstack"] = args.maxstack
        if args.damage is not None:
            rec["damage"] = args.damage
        rows.append(rec)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    no_name = [r["id"] for r in rows if not r["name"]]
    print(f"生成 {len(rows)} 条 -> {out}  ({out.stat().st_size / 1024:.0f} KB)")
    if no_name:
        print(f"⚠ 有 {len(no_name)} 条 lang 里查不到中文名，需手工补：{', '.join(no_name[:10])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
