#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""De-Extinction（classId 12157）物品/实体批量新增 JSON。

27 条：
  14 生物（实体，图标留空）
   2 植物（方块，立体图标）
   6 机器（方块，立体图标）
   5 通用物品（平面图标）

每种生物的化石 / 清理后化石 / DNA 瓶 / 数据盘不单独建页，
在生物页正文里说明这条物品链，避免同类页面重复。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
MOD = BASE / "de"
TEX = MOD / "assets/deextinction/textures"
OUT = BASE / "de-物品导入-12157.json"
NS = "deextinction"
ISO_DIR = BASE / "de-block-icons"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def shade(img, f):
    a = img.copy()
    px = a.load()
    for y in range(a.height):
        for x in range(a.width):
            r, g, b, al = px[x, y]
            px[x, y] = (int(r * f), int(g * f), int(b * f), al)
    return a


def iso_icon(tex_path: Path, size: int = 32) -> str:
    """单纹理等轴测立方体。"""
    if not tex_path.exists():
        return ""
    tex = Image.open(tex_path).convert("RGBA")
    S = 256
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cx, cy = S / 2, S / 2
    w = S * 0.40
    h = w
    top_p = [(cx, cy - h), (cx + w, cy - h / 2), (cx, cy), (cx - w, cy - h / 2)]
    left_p = [(cx - w, cy - h / 2), (cx, cy), (cx, cy + h), (cx - w, cy + h / 2)]
    right_p = [(cx, cy), (cx + w, cy - h / 2), (cx + w, cy + h / 2), (cx, cy + h)]

    def draw(poly, factor):
        t = shade(tex, factor)
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, x1 = int(min(xs)), int(max(xs))
        y0, y1 = int(min(ys)), int(max(ys))
        if x1 <= x0 or y1 <= y0:
            return
        small = t.resize((x1 - x0, y1 - y0), Image.NEAREST)
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).polygon([(p[0], p[1]) for p in poly], fill=255)
        layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        layer.paste(small, (x0, y0))
        canvas.paste(layer, (0, 0), mask)

    draw(top_p, 1.0)
    draw(left_p, 0.8)
    draw(right_p, 0.6)
    out = canvas.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def flat_icon(p: Path) -> str:
    if not p.exists():
        return ""
    img = Image.open(p).convert("RGBA")
    if img.size != (32, 32):
        img = img.resize((32, 32), Image.LANCZOS if img.width > 32 else Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# 14 种生物：id, 显示名, 中文名, 分类, 生境, 繁殖方式(egg/syringe)
BEASTS = [
    ("anthropornis", "Anthropornis", "巨型企鹅", "企鹅目", "海洋", "egg"),
    ("arctotherium", "Arctotherium", "巨型短面熊", "食肉目，熊科", "陆地", "syringe"),
    ("basilosaurus", "Basilosaurus", "龙王鲸", "偶蹄目，鲸目", "海洋", "syringe"),
    ("canis_nehringi", "Canis nehringi", "内林氏犬", "食肉目，犬科", "陆地", "syringe"),
    ("cuvieronius", "Cuvieronius", "居维叶象", "长鼻目，嵌齿象科", "陆地", "syringe"),
    ("kelenken", "Kelenken", "恐鹤", "叫鹤目，恐鹤科", "陆地", "egg"),
    ("kimmerosaurus", "Kimmerosaurus", "启莫里龙", "蛇颈龙目", "海洋", "syringe"),
    ("livyatan", "Livyatan", "利维坦鲸", "偶蹄目，鲸目", "海洋", "syringe"),
    ("macrauchenia", "Macrauchenia", "后弓兽", "滑距骨目", "陆地", "syringe"),
    ("pelagornis", "Pelagornis", "远洋鸟", "齿翼鸟目", "空中", "egg"),
    ("pliosaurus", "Pliosaurus", "上龙", "鳍龙超目，上龙科", "海洋", "syringe"),
    ("sebecus", "Sebecus", "西贝鳄", "西贝鳄类", "陆地", "egg"),
    ("smilodon", "Smilodon", "剑齿虎", "食肉目，猫科", "陆地", "syringe"),
    ("theriodictis", "Theriodictis", "兽犬", "食肉目，犬科", "陆地", "syringe"),
    ("thylacosmilus", "Thylacosmilus", "袋剑虎", "袋犬目", "陆地", "syringe"),
]

PLANTS = [
    ("banksia", "Banksia", "斑克木", "山龙眼目，山龙眼科", "橙、红、白、黄四色花"),
    ("lygodium", "Lygodium", "海金沙", "莎草蕨目，海金沙科", "普通与密集两种形态"),
]

MACHINES = [
    ("block_de_extinction_machine", "De-extinction Machine", "去灭绝机器",
     "复活流程的最后一步。放入整理好的数据盘，机器据此生成对应的生物或蛋。", "block_machine_monitor.png"),
    ("block_dna_extractor", "DNA Extractor", "DNA 提取器",
     "从已清理的化石中提取遗传物质，产出对应的 DNA 瓶。", "block_machine_scanner.png"),
    ("block_dna_decoder", "DNA Decoder", "DNA 解码器",
     "把 DNA 瓶中的序列读出并写入空数据盘，产出该物种的数据盘。", "block_machine_keyboard.png"),
    ("block_dna_editor", "DNA Editor", "DNA 编辑器",
     "对解码后的数据做调整与筛选。位于解码与生成之间的中间环节。", "block_machine_logo.png"),
    ("block_microscope", "Microscope", "显微镜",
     "用于观察与鉴定样本，是化石研究环节的辅助设备。", "block_microscope_scopes.png"),
    ("block_cleaning_table", "Cleaning Table", "清洗台",
     "放置未清理化石的工作台，配合刷子使用。有十六种颜色，材质不同但功能一致。", "block_machine_base.png"),
]

GENERIC = [
    ("item_rockpick", "Rockpick", "岩石镐",
     "专门用于开采化石方块的工具。普通镐挖化石会破坏样本，需用这种镐取。"),
    ("item_brush", "Brush", "刷子",
     "清理化石的工具。对未清理的化石使用可去除附着物，得到已清理的样本。"),
    ("item_radiometric_dating", "Radiometric Dating Instrument", "放射性测年仪",
     "测定化石的年代归属，用于判断样本属于古生代、中生代还是新生代。"),
    ("item_data_disk", "Empty Data Disk", "空数据盘",
     "写入遗传数据的载体。DNA 解码器用它接收序列，产出各物种专属的数据盘。"),
    ("item_de_pad", "DePad", "研究终端",
     "查看研究进度与数据整理情况的界面工具，界面上会显示 DNA 研究状态。"),
]

# 通用物品的纹理文件名与 key 不同
GENERIC_TEX = {
    "item_data_disk": "item_data_disk_empty.png",
}

FOSSIL_ERA = {
    "cenozoic": "新生代",
    "mesozoic": "中生代",
    "paleozoic": "古生代",
}


def beast_html(name, zh, cls, habitat, breed):
    breed_desc = (
        "产蛋——复活后先得到一枚蛋，放置等待孵化，临近孵化时会有提示。"
        if breed == "egg" else
        "注射——用注射器从个体取得血样后再注射，走胎生路线，不经过蛋的阶段。"
    )
    return (
        f"<p>{name}（{zh}）是 De-Extinction 复活的灭绝动物，分类归属为{cls}。</p>"
        f"<p><strong>生境</strong>：{habitat}。需要安置在对应环境中才能正常活动。</p>"
        f"<p><strong>繁殖方式</strong>：{breed_desc}</p>"
        "<p><strong>物品链</strong>：该物种有五个专属物品，构成一条从化石到复活的完整链条。</p>"
        "<table><thead><tr><th>物品</th><th>作用</th></tr></thead><tbody>"
        f"<tr><td>{name} Fossil</td><td>未清理的化石，从化石方块中挖出</td></tr>"
        f"<tr><td>{name} Cleaned Fossil</td><td>用刷子清理后的样本</td></tr>"
        f"<tr><td>{name} DNA Bottle</td><td>从已清理化石中提取出的遗传物质</td></tr>"
        f"<tr><td>{name} Data Disk</td><td>解码后的可用数据</td></tr>"
        f"<tr><td>{name} {'Egg' if breed == 'egg' else 'Syringe'}</td>"
        f"<td>{'孵化用的蛋' if breed == 'egg' else '用于繁殖的注射器'}</td></tr>"
        "</tbody></table>"
        "<p><strong>获取</strong>：挖化石 → 清理 → 提取 DNA → 解码 → 去灭绝机器。"
        "具体流程见模组页的复活流程表。</p>"
    )


def main() -> int:
    rows = []
    TEXITEM = TEX / "items"
    TEXBLOCK = TEX / "blocks"

    # 14 生物
    for rid, name, zh, cls, habitat, breed in BEASTS:
        rows.append({
            "id": f"entity_{rid}",
            "name": name,
            "ename": "",
            "regname": f"{NS}:entity_{rid}",
            "category": "灭绝生物",
            "type": "生物/实体",
            "maxstack": 64,
            "remark": (
                "De-Extinction 新增生物资料页：名称与分类取自 lang/en_us.json，"
                "物品链依据同文件下该物种的五件专属物品条目。实体无静态图标，"
                "图标留空并按规则勾选删除。"
                f"{tail()}"
            ),
            "html": beast_html(name, zh, cls, habitat, breed),
            "icon32": "",
        })

    # 2 植物
    for rid, name, zh, cls, form in PLANTS:
        rows.append({
            "id": f"block_{rid}",
            "name": name,
            "ename": "",
            "regname": f"{NS}:block_{rid}",
            "category": "灭绝植物",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "De-Extinction 新增方块资料页：名称与分类取自 lang/en_us.json，"
                "图标按方块纹理渲染成等轴测立体图。"
                f"{tail()}"
            ),
            "html": (
                f"<p>{name}（{zh}）是 De-Extinction 复活的已灭绝植物，分类归属为{cls}。</p>"
                f"<p><strong>形态</strong>：{form}。</p>"
                "<p><strong>物品链</strong>：与动物相同，有未清理化石、已清理化石、DNA 瓶与数据盘四件，"
                "但不需要孵化环节，直接在去灭绝机器中培育出可放置的植株。</p>"
                "<p><strong>获取</strong>：挖化石 → 清理 → 提取 DNA → 解码 → 去灭绝机器。</p>"
            ),
            # 植物是 cross 模型（十字贴图），等轴测无意义，用平面纹理
            "icon32": flat_icon(TEX / f"deextincted/{rid}/block_{rid}_plant.png"
                              if rid == "banksia"
                              else TEX / f"deextincted/{rid}/block_{rid}_normal.png"),
        })

    # 6 机器
    for key, name, zh, desc, texfile in MACHINES:
        rows.append({
            "id": key,
            "name": name,
            "ename": "",
            "regname": f"{NS}:{key}",
            "category": "机器",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "De-Extinction 新增方块资料页：名称取自 lang/en_us.json 的 block 条目，"
                "作用依据复活流程中该机器所处的位置。图标按方块纹理渲染成等轴测立体图。"
                f"{tail()}"
            ),
            "html": (
                f"<p>{name}（{zh}）是 De-Extinction 复活流程中的一台机器。</p>"
                f"<p><strong>作用</strong>：{desc}</p>"
                "<p><strong>流程位置</strong>：见模组页的复活流程表——挖掘、清理、提取、解码、生成五个环节。</p>"
            ),
            "icon32": iso_icon(TEXBLOCK / texfile),
        })

    # 5 通用物品
    for key, name, zh, desc in GENERIC:
        rows.append({
            "id": key,
            "name": name,
            "ename": "",
            "regname": f"{NS}:{key}",
            "category": "工具",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "De-Extinction 新增资料页：名称取自 lang/en_us.json，"
                "作用依据其在复活流程中的用途，图标使用该物品的独立纹理。"
                f"{tail()}"
            ),
            "html": (
                f"<p>{name}（{zh}）是 De-Extinction 添加的工具或通用物品。</p>"
                f"<p><strong>作用</strong>：{desc}</p>"
            ),
            "icon32": flat_icon(TEXITEM / GENERIC_TEX.get(key, f"{key}.png")),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    noicon = [r["id"] for r in rows if not r["icon32"]]
    print(f"无图标 {len(noicon)} 个（实体）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
