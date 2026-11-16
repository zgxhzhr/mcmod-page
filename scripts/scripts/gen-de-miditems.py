#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""De-Extinction（classId 12157）中间产物页：化石 / 清理化石 / DNA 瓶 / 数据盘。

17 个物种（15 动物 + 2 植物）× 4 件 = 68 条。

正文规则（skill §「同类物品只写一条正文」）：
  - 每一类只写第一条的正文，其余留空
  - 留空的条目在 remark 里写明「需协助创建抽象类」
  - 页数照建，不因正文重复就少建

图标：每种物种各有独立纹理，全部带图标。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
TEX = BASE / "de/assets/deextinction/textures/deextincted"
OUT = BASE / "de-中间产物-12157.json"
NS = "deextinction"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def flat_icon(p: Path) -> str:
    if not p.exists():
        return ""
    img = Image.open(p).convert("RGBA")
    if img.size != (32, 32):
        # 16→32 是放大，必须 NEAREST（skill 图标规范第 1 条）
        method = Image.NEAREST if img.width < 32 else Image.LANCZOS
        img = img.resize((32, 32), method)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


BEASTS = [
    ("anthropornis", "Anthropornis", "巨型企鹅"),
    ("arctotherium", "Arctotherium", "巨型短面熊"),
    ("basilosaurus", "Basilosaurus", "龙王鲸"),
    ("canis_nehringi", "Canis nehringi", "内林氏犬"),
    ("cuvieronius", "Cuvieronius", "居维叶象"),
    ("kelenken", "Kelenken", "恐鹤"),
    ("kimmerosaurus", "Kimmerosaurus", "启莫里龙"),
    ("livyatan", "Livyatan", "利维坦鲸"),
    ("macrauchenia", "Macrauchenia", "后弓兽"),
    ("pelagornis", "Pelagornis", "远洋鸟"),
    ("pliosaurus", "Pliosaurus", "上龙"),
    ("sebecus", "Sebecus", "西贝鳄"),
    ("smilodon", "Smilodon", "剑齿虎"),
    ("theriodictis", "Theriodictis", "兽犬"),
    ("thylacosmilus", "Thylacosmilus", "袋剑虎"),
]

PLANTS = [
    ("banksia", "Banksia", "斑克木"),
    ("lygodium", "Lygodium", "海金沙"),
]

# 四类中间产物：后缀, 中文类别, 显示名后缀, 正文模板
KINDS = [
    ("fossil_broken", "化石", "Fossil",
     lambda n, zh: (
         f"<p>{n} Fossil 是 {n}（{zh}）的未清理化石，从化石方块中挖出。</p>"
         "<p><strong>获取</strong>：用岩石镐开采化石方块。普通镐会破坏样本，需用这种专用工具。</p>"
         "<p><strong>用途</strong>：清理后可得到已清理样本，进而提取遗传物质。"
         "这是整条复活流程的起点。</p>"
         "<p><strong>外观</strong>：表面裹着岩层，需要清理才能看清内部的化石结构。</p>"
     )),
    ("fossil_clean", "清理化石", "Cleaned Fossil",
     lambda n, zh: (
         f"<p>{n} Cleaned Fossil 是 {n}（{zh}）的已清理化石。</p>"
         "<p><strong>获取</strong>：用刷子对未清理化石使用，去除附着岩层后得到。</p>"
         "<p><strong>用途</strong>：放入 DNA 提取器，提取该物种的遗传物质。</p>"
         "<p><strong>说明</strong>：清理后的样本才能用于提取，未清理的化石直接放进提取器不会有产出。</p>"
     )),
    ("dna_bottle", "DNA", "DNA Bottle",
     lambda n, zh: (
         f"<p>{n} DNA Bottle 是装有 {n}（{zh}）遗传物质的瓶子。</p>"
         "<p><strong>获取</strong>：把该物种的已清理化石放入 DNA 提取器后产出。</p>"
         "<p><strong>用途</strong>：放入 DNA 解码器，将序列写入空数据盘。</p>"
         "<p><strong>说明</strong>：DNA 瓶只是中间产物，不能直接用来生成生物，必须经过解码与编辑。</p>"
     )),
    ("data_disk", "数据盘", "Data Disk",
     lambda n, zh: (
         f"<p>{n} Data Disk 是记录 {n}（{zh}）完整遗传数据的数据盘。</p>"
         "<p><strong>获取</strong>：把该物种的 DNA 瓶与空数据盘一起放入 DNA 解码器后产出。</p>"
         "<p><strong>用途</strong>：放入去灭绝机器，即可生成对应生物或蛋。</p>"
         "<p><strong>说明</strong>：数据盘是复活流程的最后一个环节，也是唯一能直接产生活体的物品。</p>"
     )),
]


def main() -> int:
    rows = []
    species = BEASTS + PLANTS
    # 每类记录是否已经写过正文
    seen_kind = set()

    for kind_key, kind_zh, kind_en, html_fn in KINDS:
        for rid, name, zh in species:
            is_plant = rid in ("banksia", "lygodium")
            # 中文显示名：物种中文名 + 类别
            disp = f"{name} {kind_en}" if not is_plant else f"{name} {kind_en}"
            zh_full = f"{zh}{kind_zh}"

            if kind_key in seen_kind:
                html = ""
                note = (f"同类物品的正文已集中在「{kind_zh}」类的首条页面，本条留空，"
                        "需协助创建抽象类以统一展示。")
            else:
                seen_kind.add(kind_key)
                html = html_fn(name, zh)
                note = f"本条为「{kind_zh}」类的正文代表页，同类其余条目留空并引用同一套说明。"

            rows.append({
                "id": f"item_{rid}_{kind_key}",
                "name": disp,
                "ename": "",
                "regname": f"{NS}:item_{rid}_{kind_key}",
                "category": kind_zh,
                "type": "物品/方块",
                "maxstack": 64,
                "remark": (
                    "De-Extinction 新增资料页：名称取自 lang/en_us.json 的物品条目，"
                    "用途依据该物品在复活流程中的位置。"
                    + note + tail()
                ),
                "html": html,
                "icon32": flat_icon(TEX / rid / f"item_{rid}_{kind_key}.png"),
            })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    noicon = [r["id"] for r in rows if not r["icon32"]]
    print(f"无图标 {len(noicon)} 个" + (f": {noicon[:5]}" if noicon else " ✓"))
    withhtml = [r["name"] for r in rows if r["html"]]
    print(f"\n有正文 {len(withhtml)} 条（每类 1 条）:")
    for n in withhtml:
        print(f"  {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
