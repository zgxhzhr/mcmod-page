#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Headphones（classId 12911）2 个物品的批量新增 JSON。

模组没有 zh_cn，按规则名称只用英文（ename 留空）。

图标来源：两个物品都是 Blockbench 3D 模型（models/custom/*.json），
没有可直接使用的 2D 贴图，所以用 render-item-3d.py 按模型 + 纹理渲染成 32×32。
"""
import base64
import io
import json
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
ICONS = BASE / "hdp-icons"
OUT = BASE / "hdp-物品导入-12911.json"
NS = "headphones"

# ── 物品数据 ──
ITEMS = [
    {
        "id": "headphone",
        "name": "Headphone",
        "category": "道具",
        "maxstack": 1,
        "icon": "headphones",
        "html": (
            "<p>Headphone 是 Headphones 添加的可穿戴物品，右击会把它戴到头上，占用头盔槽。</p>"
            "<p><strong>用法</strong>：手持右击即可装备，装备时会播放一次合金盔甲的穿脱音效。"
            "戴上后它替代头盔的位置，原本戴着的头盔会被替换下来。</p>"
            "<p><strong>播放音乐</strong>：戴上耳机后，用 Headphones Control 选曲，音乐就会通过耳机播放，"
            "支持全部原版音乐唱片。</p>"
            "<p><strong>获取</strong>：在工作台按固定形状合成，材料为黑曜石、钻石、一个铁头盔和两个红石块。</p>"
            "<p><strong>注意</strong>：戴耳机时不能同时戴头盔，防护会掉一档。</p>"
        ),
    },
    {
        "id": "headphones_control",
        "name": "Headphones Control",
        "category": "道具",
        "maxstack": 1,
        "icon": "headphones_control",
        "html": (
            "<p>Headphones Control 是 Headphones 添加的控制终端，用来给耳机选曲与归还唱片。</p>"
            "<p><strong>用法</strong>：手持右击打开选曲界面，界面里列出可播放的唱片，"
            "点一下对应项就开始播放。想要停下或换曲时再次右击。</p>"
            "<p><strong>唱片管理</strong>：控制器自带一个内部槽位，放进去的唱片会在关闭播放后自动退回到世界或背包，"
            "不会平白消耗掉。</p>"
            "<p><strong>支持曲目</strong>：原版的全部音乐唱片，包括 13、cat、blocks、chirp、far、mall、mellohi、"
            "stal、strad、ward、11、wait 与 Pigstep。</p>"
            "<p><strong>获取</strong>：在工作台按固定形状合成，材料为黑曜石、钻石、红石与一个红石块。</p>"
        ),
    },
]


def b64(p: Path) -> str:
    img = Image.open(p).convert("RGBA")
    if img.size != (32, 32):
        img = img.resize((32, 32), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    rows = []
    for it in ITEMS:
        ip = ICONS / f"{it['icon']}.png"
        icon = b64(ip) if ip.exists() else ""
        rows.append({
            "id": it["id"],
            "name": it["name"],
            "ename": "",
            "regname": f"{NS}:{it['id']}",
            "category": it["category"],
            "type": "物品/方块",
            "maxstack": it["maxstack"],
            "remark": ("Headphones 新增资料页：名称取自 lang/en_us.json（模组没有 zh_cn，按规则只写英文）。"
                       "用法与配方依据 HeadphoneItem / HeadphonesControlItem 的反编译结果与 data 下的合成配方。"
                       "辛苦喵呜机了"),
            "html": it["html"],
            "icon32": icon,
        })
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.1f} KB)")
    for r in rows:
        print(f"  {r['name']:<20} [{r['category']}] 图标 {len(r['icon32'])} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
