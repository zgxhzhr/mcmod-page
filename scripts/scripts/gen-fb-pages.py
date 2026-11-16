#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Factory Blocks（classId 20843）资料页 —— 按「综合」方案交付。

49 个方块全部叫「工厂方块」，只靠物品提示的副标题区分外观变体。
按 MC百科编辑规范第 33 条，这种「介绍几乎完全一样」的同族方块应申请「综合」：

  抽象父资料：工厂方块（1 条，正文写全套说明）
  子资料：49 个变体（每条的正文都从父资料固定引用，不写自己的内容）

本脚本产出：
  fb-父资料-20843.json    抽象父资料（综合用）
  fb-子资料-20843.json    49 个子资料（name 用变体副标题，正文留空待站方引用）
  fb-综合申请-20843.md    给审核员看的申请文本
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
FB = BASE / "fb/assets/factory_blocks"
SRC = BASE / "fb-src"
OUT_PARENT = BASE / "fb-父资料-20843.json"
OUT_CHILD = BASE / "fb-子资料-20843.json"
OUT_APPLY = BASE / "fb-综合申请-20843.md"
ICONS128 = BASE / "fb-icons128"
ICONS32 = BASE / "fb-icons32"

_PAW = ["呜喵", "喵呜", "喵喵"]
NS = "factory_blocks"


def b64(path: Path):
    """读 PNG 转裸 base64。"""
    import base64
    import io

    from PIL import Image

    if not path.exists():
        return ""
    buf = io.BytesIO()
    Image.open(path).convert("RGBA").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# 从 RegisterBlocks.java 提取 (id, 类型)
def block_list():
    t = (list(SRC.rglob("RegisterBlocks.java"))[0]).read_text(encoding="utf-8", errors="ignore")
    import re
    rows = []
    for m in re.finditer(r'addFactoryBlock\(\s*"([^"]+)"\s*,\s*Type\.(\w+)', t):
        rows.append((m.group(1), m.group(2)))
    return rows


def main() -> int:
    zh = json.loads((FB / "lang/zh_cn.json").read_text(encoding="utf-8"))
    en = json.loads((FB / "lang/en_us.json").read_text(encoding="utf-8"))
    blocks = block_list()

    # 变体副标题
    def tip(bid, key_prefix):
        return zh.get(f"{key_prefix}.{NS}.{bid}.tooltip") or en.get(f"{key_prefix}.{NS}.{bid}.tooltip") or bid

    FAN_TYPES = {"baseFan": "常开风扇", "redFan": "红石驱动风扇", "mediumFan": "中型风扇"}

    # 红石驱动款与故障款静置时外观完全相同（两者模型均无 elements，
    # 共用 block/fan/still 贴图），物品栏图标因此一样——这是模组真实情况。
    SAME_ICON_NOTE = {
        "fan": "该方块与「风扇（红石故障）」静置外观完全相同，只在通电后叶片状态不同，物品栏图标因此一致。",
        "fan_malfunction": "该方块与「风扇（红石驱动）」静置外观完全相同，只在通电后叶片状态不同，物品栏图标因此一致。",
    }

    # 模组 lang 的 tooltip 有误，按实际纹理修正：
    #   caution 的 tooltip 被误写成 "Rusty Scaffold"，与 rusty_scaffold 撞名；
    #   它的纹理其实是黄绿方格（警示类），不是脚手架。
    NAME_FIX = {
        "caution": ("警示方格", "Caution Grid"),
    }

    # ── 父资料正文 ──
    parent_html = (
        "<p>工厂方块是 Factory Blocks 添加的工业风格外观件，共四十九种。"
        "它们不参与任何生产流程，用途是给建筑补工业质感的细节——"
        "锈蚀金属板、电路、管道、格栅、脚手架、警示条纹、风扇等。</p>"

        "<p><strong>名称与辨识</strong>：四十九种方块的主名全部是「工厂方块」，"
        "分辨具体是哪种要看物品提示里的副标题，例如「生锈金属板」「镀金电路」「大型管道」。"
        "在物品栏里它们排成一片，外观相近但纹理不同。</p>"

        "<table><thead><tr><th>类别</th><th>数量</th><th>说明</th></tr></thead><tbody>"
        "<tr><td>装饰方块</td><td>42</td><td>纯外观件，无功能</td></tr>"
        "<tr><td>风扇</td><td>7</td><td>分常开、红石驱动、中型三类，有实际吹动效果</td></tr>"
        "</tbody></table>"

        "<p><strong>材质与属性</strong>：四十九种方块的属性全部复制自铁块——"
        "硬度与爆炸抗性同铁块，需要铁镐或更高级的镐才能采集。"
        "这一点与外观无关：看起来像薄铁皮的面板，实际强度和铁块一样。"
        "属性统一意味着选型时不用考虑耐用性，只看外观搭不搭。</p>"

        "<p><strong>风扇</strong>：七个风扇是这套方块里唯一有功能的。按驱动方式分三类：</p>"
        "<table><thead><tr><th>类型</th><th>数量</th><th>行为</th></tr></thead><tbody>"
        "<tr><td>常开风扇</td><td>3</td><td>放置后一直转动，不受红石影响</td></tr>"
        "<tr><td>红石驱动风扇</td><td>3</td><td>需要红石信号才转动，信号消失后停转</td></tr>"
        "<tr><td>中型风扇</td><td>1</td><td>体积更大，按朝向判定碰撞箱</td></tr>"
        "</tbody></table>"
        "<p>常开与红石驱动的三类各有三种外观：单面、四向、故障样式。"
        "故障样式是叶片卡住或歪斜的造型，用来做废弃厂房的场景。</p>"

        "<p><strong>与 Chisel 的关系</strong>：模组的定位是给 Chisel Reborn 或 Chipped 补充方块集。"
        "装了这两个模组之一时，四十九种工厂方块会被加入 Chisel 的 factory 分组，"
        "可以用凿子在同一组内互相转换——砌墙时凿几下就能换一种纹理，不用拆了重放。</p>"
        "<p>没装 Chisel 也能正常使用，只是失去组内转换这个便利，"
        "每种方块要单独做、单独放。</p>"

        "<p><strong>版本</strong>：1.4.2 对应 Minecraft 26.3 与 NeoForge。作者 slaincow。</p>"
    )

    parent = [{
        "id": "factory_block",
        "name": "工厂方块",
        "ename": "Factory Block",
        "regname": "",
        "category": "建筑方块",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Factory Blocks 抽象父资料（综合用）：方块总数与类型分布取自 RegisterBlocks 的 "
            "addFactoryBlock 调用，属性复制自 Blocks.IRON_BLOCK，Chisel 联动取自 FactoryBlocksMod.post "
            "与 ChiselSupport，变体副标题取自 lang/zh_cn.json 的 tooltip 条目。"
            f"{tail()}"
        ),
        "html": parent_html,
        "icon32": b64(ICONS32 / f"{NS}__block_factory.png"),
        "icon128": b64(ICONS128 / f"{NS}__block_factory.png"),
    }]
    OUT_PARENT.write_text(json.dumps(parent, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 子资料（变体）──
    children = []
    for bid, typ in blocks:
        if bid in NAME_FIX:
            sub_zh, sub_en = NAME_FIX[bid]
            name_note = "（该方块在模组 lang 里的 tooltip 被误写成 Rusty Scaffold，与实际纹理不符，此处按外观修正）"
        else:
            sub_zh = zh.get(f"item.{NS}.{bid}.tooltip") or zh.get(f"block.{NS}.{bid}.tooltip") or bid
            sub_en = en.get(f"item.{NS}.{bid}.tooltip") or en.get(f"block.{NS}.{bid}.tooltip") or bid
            name_note = ""
        children.append({
            "id": bid,
            "name": sub_zh,
            "ename": sub_en,
            "regname": f"{NS}:{bid}",
            "category": "建筑方块",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                f"Factory Blocks 子资料（待综合）：方块 id 为 {NS}:{bid}，"
                f"副标题取自 lang/zh_cn.json，类型 {typ}。{name_note}"
                + SAME_ICON_NOTE.get(bid, "")
                + "正文由父资料「工厂方块」统一提供，本条不单独撰写。"
                f"{tail()}"
            ),
            "html": "",
            "icon32": b64(ICONS32 / f"{NS}__block_{bid}.png"),
            "icon128": b64(ICONS128 / f"{NS}__block_{bid}.png"),
        })
    OUT_CHILD.write_text(json.dumps(children, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 综合申请文本 ──
    fans = [(b, t) for b, t in blocks if t != "base"]
    apply_md = f"""# Factory Blocks（20843）综合申请

## 申请内容

功能：综合

抽象父资料：**工厂方块**（本次提交，id `factory_block`）

子资料：共 {len(children)} 条，见 `fb-子资料-20843.json`。

## 申请理由

依据主站编辑规范第 33 条：多个同类资料的相互文本重复率较高时，应使用「综合」功能创建父资料。

本模组的实际情况：

1. **{len(children)} 个方块共用一个名称**。语言文件里 `block.factory_blocks.*` 的主名全是
   「工厂方块」，只在 `.tooltip` 里写外观副标题（如「生锈金属板」「镀金电路」）。
2. **属性完全一致**。四十九种方块的属性都复制自铁块（`Blocks.IRON_BLOCK`），
   硬度、爆炸抗性、采集工具全部相同，没有任何数值差异。
3. **正文会完全重复**。除七个风扇外，其余 42 个方块的说明只有外观描述不同，
   逐条写等于把同一段话复制 42 遍。

这符合「综合」的典型场景（对照规范里的「彩色玻璃 -(橙色玻璃、白色玻璃…)」
「大理石装饰方块 -(大理石、大理石楼梯…)」）。

## 七个风扇的处理

{len(fans)} 个风扇有实际功能差异（常开 / 红石驱动 / 中型），
这部分说明已写进父资料正文，不另设页面：

| 方块 | 副标题 | 类型 |
|---|---|---|
""" + "\n".join(
        f"| `{b}` | {zh.get(f'item.{NS}.{b}.tooltip') or en.get(f'item.{NS}.{b}.tooltip') or b} | {FAN_TYPES.get(t, t)} |"
        for b, t in fans
    ) + f"""

## 提交顺序

1. 本文件（父资料 `factory_block`）先提交；
2. 审核通过、拿到父资料 URL 后，由管理协助把 `fb-子资料-20843.json` 里的 {len(children)} 条
   合并到父资料下（子资料正文会自动引用父资料，不需要各写一遍）。

## 附注

模组本身依赖可选的 Chisel Reborn / Chipped——装了它们时，这 49 个方块会被加进
Chisel 的 factory 分组，可用凿子互相转换。这一点已写进父资料正文。
"""
    OUT_APPLY.write_text(apply_md, encoding="utf-8")

    print(f"父资料 1 条 → {OUT_PARENT.name}  ({OUT_PARENT.stat().st_size/1024:.1f} KB)")
    print(f"子资料 {len(children)} 条 → {OUT_CHILD.name}  ({OUT_CHILD.stat().st_size/1024:.1f} KB)")
    print(f"综合申请 → {OUT_APPLY.name}  ({OUT_APPLY.stat().st_size/1024:.1f} KB)")
    print(f"\n类型分布：装饰 {sum(1 for _,t in blocks if t=='base')} / 风扇 {len(fans)}")
    print(f"父资料正文 {len(parent_html)} 字符，表格 {parent_html.count('<table')} 张")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
