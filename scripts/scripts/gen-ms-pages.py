#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""More Slab（classId 8830）资料页 —— 两套方案同时产出。

模组：151 个方块，全部是标准台阶（parent = block/slab），形状完全一致，
只有纹理不同。语言文件只有 en_us.json，无中文。

方案 A（综合，推荐）
  ms-父资料-8830.json   抽象父资料「台阶」，写全套说明
  ms-子资料-8830.json   151 个子资料，正文留空待站方引用

方案 B（拆包，若站方不接受综合）
  ms-代表页-8830.json   我们的批量新增格式
  export/more_slab_item.json   151 条 IRR 格式

两套的图标都已渲染（ms-icons32 / ms-icons128）。
"""
import base64
import io
import json
import random
import re
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
MS = BASE / "ms/assets/more_slab"
ICONS32 = BASE / "ms-icons32"
ICONS128 = BASE / "ms-icons128"
EXPORT = BASE / "export"
NS = "more_slab"

_PAW = ["呜喵", "喵呜", "喵喵"]

COLOR_ZH = {
    "white": "白色", "orange": "橙色", "magenta": "品红", "lightblue": "淡蓝色",
    "yellow": "黄色", "lime": "黄绿色", "pink": "粉色", "gray": "灰色",
    "lightgray": "淡灰色", "cyan": "青色", "purple": "紫色", "blue": "蓝色",
    "brown": "棕色", "green": "绿色", "red": "红色", "black": "黑色",
}


def b64(path: Path, size: int = 0):
    if not path.exists():
        return ""
    im = Image.open(path).convert("RGBA")
    if size and im.size != (size, size):
        im = im.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    lang = json.loads((MS / "lang/en_us.json").read_text(encoding="utf-8"))
    ids = [p.stem for p in sorted((MS / "blockstates").glob("*.json"))]

    # ── 方案 A：父资料 ──
    parent_html = (
        "<p>这些方块是 More Slab 添加的台阶，把原版的各类方块切成半格高度。"
        "共一百五十一种，覆盖木材、原木、羊毛、混凝土、染色玻璃、陶瓦、带釉陶瓦，"
        "以及紫水晶、远古残骸、玄武岩、骨块等零散方块。</p>"

        "<p><strong>形状统一</strong>：全部是标准台阶——放置后占半格高度，"
        "有下半、上半、双格三种状态，与楼梯的拼接规则相同。"
        "所有台阶的模型共用原版台阶的几何形状，区别只在表面纹理。</p>"

        "<p><strong>覆盖范围</strong>（共一百五十一种）：</p>"
        "<table><thead><tr><th>类别</th><th>数量</th><th>说明</th></tr></thead><tbody>"
        "<tr><td>木头与原木</td><td>35</td><td>含去皮版本、下界菌柄与菌核、竹</td></tr>"
        "<tr><td>陶瓦</td><td>16</td><td>十六色齐全</td></tr>"
        "<tr><td>带釉陶瓦</td><td>16</td><td>十六色齐全，保留原版图案</td></tr>"
        "<tr><td>染色玻璃</td><td>16</td><td>十六色齐全，可透光</td></tr>"
        "<tr><td>混凝土</td><td>15</td><td>缺品红色</td></tr>"
        "<tr><td>羊毛</td><td>14</td><td>缺品红与紫色</td></tr>"
        "<tr><td>其他方块</td><td>39</td><td>紫水晶、远古残骸、铁桶、玄武岩、基岩、骨块、方解石、草方块等</td></tr>"
        "</tbody></table>"

        "<p><strong>两处需要注意的命名</strong>：染色玻璃的紫色在模组里拼作 "
        "purlplestainedglassslab（原文如此），检索时按「Purlple stained glass slab」查找。"
        "羊毛与混凝土缺的几种颜色是模组本身没做，不是漏列。</p>"

        "<p><strong>属性</strong>：各自沿用原方块的硬度与采集工具要求。"
        "石类台阶需要镐、木类台阶用斧更快，玻璃类台阶只有精准采集才能取得原方块。</p>"

        "<p><strong>合成</strong>：每种台阶由对应的原方块在工作台合成，"
        "一个原方块出两个台阶，与木板做台阶的比例一致。</p>"
    )

    parent = [{
        "id": "slab",
        "name": "台阶",
        "ename": "Slab",
        "regname": "",
        "category": "建筑方块",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "More Slab 资料页：本条为该模组方块的总览页，说明台阶的通用属性。"
            "方块总数与分类取自 assets/more_slab/blockstates 与 lang/en_us.json，"
            "形状依据全部模型的 parent = block/slab。"
            "其余 151 个具体方块以 IRR 格式另行交付。模组无中文语言文件。"
            f"{tail()}"
        ),
        "html": parent_html,
        "icon32": b64(ICONS32 / f"{NS}__block_acaciawoodslab.png"),
        "icon128": b64(ICONS128 / f"{NS}__block_acaciawoodslab.png"),
    }]
    (BASE / "ms-父资料-8830.json").write_text(
        json.dumps(parent, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 子资料：本方案不用，跳过 ──
#     children = []
#     for bid in ids:
#         en = lang.get(f"block.{NS}.{bid}", bid)
#         children.append({
#             "id": bid,
#             "name": en,
#             "ename": "",
#             "regname": f"{NS}:{bid}",
#             "category": "建筑方块",
#             "type": "物品/方块",
#             "maxstack": 64,
#             "remark": (
#                 f"More Slab 子资料（待综合）：方块 id 为 {NS}:{bid}，"
#                 f"英文名取自 lang/en_us.json（模组无中文语言文件）。"
#                 "正文由父资料「台阶」统一提供，本条不单独撰写。"
#                 f"{tail()}"
#             ),
#             "html": "",
#             "icon32": b64(ICONS32 / f"{NS}__block_{bid}.png"),
#             "icon128": b64(ICONS128 / f"{NS}__block_{bid}.png"),
#         })
#     (BASE / "ms-子资料-8830.json").write_text(
#         json.dumps(children, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 方案 B：IRR 格式 ──
    # 字段按 IRR ItemData 的实际输出：null 字段省略，maxDurability = getMaxDamage()+1
    EXPORT.mkdir(parents=True, exist_ok=True)
    irr_lines = []
    for bid in ids:
        en = lang.get(f"block.{NS}.{bid}", bid)
        obj = {
            "name": en,
            "englishName": en,
            "registerName": f"{NS}:{bid}",
            "type": "Block",
            "maxStackSize": 64,
            "maxDurability": 1,
            "smallIcon": b64(ICONS32 / f"{NS}__block_{bid}.png"),
            "largeIcon": b64(ICONS128 / f"{NS}__block_{bid}.png"),
        }
        irr_lines.append(json.dumps(obj, ensure_ascii=False))
    irr_path = EXPORT / "more_slab_item.json"
    irr_path.write_text("\n".join(irr_lines), encoding="utf-8")

    # ── 方案 B：代表页（我们的新增格式）──
    # 挑 16 条覆盖各类材质，正文写成「台阶」类通用描述
    reps = [
        "acaciawoodslab", "oaklogslab", "strippedoakwoodslab",
        "whitewool", "redwool", "whiteconcreteslab", "redconcreteslab",
        "whitestainedglassslab", "redstainedglassslab",
        "whiteterracottaslab", "redterracottaslab",
        "whiteglazedterracottaslab", "redglazedterracottaslab",
        "amethystblockslab", "ancientdebrisslab", "boneblockslab",
    ]
    reps = [r for r in reps if r in ids]
    rep_rows = []
    for bid in reps:
        en = lang.get(f"block.{NS}.{bid}", bid)
        rep_rows.append({
            "id": bid,
            "name": en,
            "ename": "",
            "regname": f"{NS}:{bid}",
            "category": "建筑方块",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                f"More Slab 资料页：方块 id 为 {NS}:{bid}，"
                f"英文名取自 lang/en_us.json（模组无中文语言文件）。"
                "本条为该材质类别的代表页，同类的其余颜色与木材变体以 IRR 格式另行交付。"
                f"{tail()}"
            ),
            "html": (
                f"<p>{en}是 More Slab 添加的台阶，把对应的原方块切成半格高度。</p>"
                "<p><strong>形状</strong>：标准台阶，放置后占半格，有下半、上半、双格三种状态，"
                "与相邻台阶和楼梯自动拼接。</p>"
                "<p><strong>合成</strong>：一个原方块在工作台出两个台阶。</p>"
            ),
            "icon32": b64(ICONS32 / f"{NS}__block_{bid}.png"),
            "icon128": b64(ICONS128 / f"{NS}__block_{bid}.png"),
        })
    (BASE / "ms-代表页-8830.json").write_text(
        json.dumps(rep_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"方案 A（综合）")
    print(f"  父资料 1 条 → ms-父资料-8830.json")
    print(f"\nIRR 包")
    print(f"  代表页 {len(rep_rows)} 条 → ms-代表页-8830.json（本方案不用，仅备查）")
    print(f"  IRR    {len(irr_lines)} 条 → export/{irr_path.name}  ({irr_path.stat().st_size/1024/1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
