#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apple Expand（classId 27316）—— 6 种苹果 + 1 个苹果箱。

数据来源（MC 1.20.1 Forge）：
  食物属性  *AppleItem.java 的 FoodProperties.Builder（nutrition + saturationModifier）
            实际饱和度 = nutrition × saturationModifier × 2
  药水效果  *AppleEatProcedure.java 的 MobEffectInstance。SRG 名（f_196xx_）已用
            MCP 的 joined.tsrg + Mojang 官方 client.txt 双向对上，不是猜的
  配方      data/apple_expand/recipes/*.json，全部是 aaa/aba/aaa 的八围一
  苹果箱    AppleCrateBlock.java：普通 Block，SoundType.WOOD，硬度 1.5，抗爆 10
  名称      assets/apple_expand/lang/zh_cn.json（模组自带中文）
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
I128 = BASE / "ae1-icons128"
I32 = BASE / "ae1-icons32"
OUT_ITEMS = BASE / "ae1-物品导入-27316.json"
NS = "apple_expand"

_PAW = ["呜喵", "喵呜", "喵喵"]
ROMAN = {0: "I", 1: "II", 2: "III", 3: "IV", 4: "V"}


def b64(p: Path) -> str:
    if not p.exists():
        return ""
    buf = io.BytesIO()
    Image.open(p).convert("RGBA").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def eff(name: str, ticks: int, amp: int, instant: bool = False) -> str:
    lvl = ROMAN.get(amp, str(amp + 1))
    return f"{name} {lvl}" if instant else f"{name} {lvl}（{ticks // 20} 秒）"


# (id, 中文, 英文, 饥饿, 饱和, 效果, 材料, 特色句, 补充)
APPLES = [
    ("amethyst_apple", "紫水晶苹果", "Amethyst Apple", 4, 11.2,
     [eff("漂浮", 100, 0), eff("发光", 2400, 0), eff("隐身", 2400, 0)],
     "紫水晶碎片",
     "效果侧重位移与状态切换",
     "<p><strong>注意</strong>：发光会让隐身状态下的轮廓重新显现，两个效果同时生效时隐身基本等于失效。</p>"),

    ("diamond_apple", "钻石苹果", "Diamond Apple", 4, 11.2,
     [eff("抗性提升", 2400, 2), eff("瞬间治疗", 1, 2, instant=True), eff("饱和", 200, 2)],
     "钻石",
     "效果侧重防御与即时恢复",
     "<p><strong>瞬间治疗</strong>：只有 1 tick，属于立即回复，不是持续回血。</p>"),

    ("echo_apple", "回响苹果", "Echo Apple", 4, 20.0,
     [eff("抗性提升", 2400, 1), eff("抗火", 2400, 1), eff("力量", 1200, 4)],
     "回响碎片",
     "六种中效果覆盖范围最广的一种",
     "<p><strong>饱和度</strong>：六种中唯一的 20 点，其余五种介于 8 至 11.2 之间。</p>"),

    ("iron_apple", "铁苹果", "Iron Apple", 4, 11.2,
     [eff("抗性提升", 1200, 1)],
     "铁锭",
     "六种中效果最单一的一种",
     ""),

    ("lapis_apple", "青金石苹果", "Lapis Apple", 4, 11.2,
     [],
     "青金石",
     "不以状态效果为目的，用于换取经验",
     "<p><strong>用途</strong>：用于替代刷取经验的过程，代价为八颗青金石与一颗苹果。</p>"),

    ("pufferfish_apple", "河豚果", "Pufferfish Apple", 4, 8.0,
     [eff("水下呼吸", 9600, 0), eff("海豚的恩惠", 1200, 0)],
     "河豚",
     "效果侧重水下活动",
     "<p><strong>对比河豚</strong>：原版河豚给的是中毒与反胃，这一颗给的是水下呼吸与海豚的恩惠，方向正好相反。</p>"),
]


def main() -> int:
    rows = []

    for rid, zh, en, hunger, sat, effects, material, lead, extra in APPLES:
        html = f"<p>{zh}是 Apple Expand 添加的苹果之一，{lead}。</p>"
        html += (
            f'<p><strong>饥饿值</strong>：[icon:hunger-level={hunger},点]　'
            f'<strong>饱和度</strong>：[icon:saturation-level={sat:g},点]</p>'
        )
        if rid == "lapis_apple":
            html += "<p><strong>食用效果</strong>：不附加状态效果，直接给使用者提升 1 级经验等级。</p>"
        else:
            html += "<p><strong>食用效果</strong>：" + "、".join(effects) + "。</p>"
        html += extra
        html += (
            f"<p><strong>合成</strong>：八颗{material}围住一个苹果，"
            "摆成环形，一次产出一颗。</p>"
        )
        html += "<p><strong>食用方式</strong>：不受饥饿值限制，饱食状态下亦可食用；食用速度快于普通食物。</p>"

        rows.append({
            "id": rid,
            "name": zh,
            "ename": en,
            "regname": f"{NS}:{rid}",
            "category": "食物",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                f"Apple Expand 资料页：名称取自模组自带的 lang/zh_cn.json，"
                f"饥饿值与饱和度取自对应的 AppleItem 类 FoodProperties 构造，"
                f"药水效果取自对应的 EatProcedure，配方取自 data/apple_expand/recipes。"
                f"{tail()}"
            ),
            "html": html,
            "icon32": b64(I32 / f"ae1__item_{rid}.png"),
            "icon128": b64(I128 / f"ae1__item_{rid}.png"),
        })

    rows.append({
        "id": "apple_crate",
        "name": "苹果箱",
        "ename": "Apple Crate",
        "regname": f"{NS}:apple_crate",
        "category": "建筑方块",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Apple Expand 资料页：名称取自 lang/zh_cn.json，破坏掉落取自 "
            "data/apple_expand/loot_tables/blocks/apple_crate.json（掉落 8 个苹果），方块属性取自 "
            "AppleCrateBlock.java 的 BlockBehaviour.Properties（SoundType.WOOD、"
            "硬度 1.5、抗爆 10），模型为 models/block/apple_crate.json 的 cube_all，"
            "配方取自 data/apple_expand/recipes/apple_crate_recipe.json。"
            f"{tail()}"
        ),
        "html": (
            "<p>苹果箱是 Apple Expand 添加的方块，用于把苹果压缩存放。</p>"
            "<p><strong>合成</strong>：八颗苹果围住一块木板，摆成环形，一次产出一个。</p>"
            "<p><strong>破坏返还</strong>：破坏苹果箱会掉落八颗苹果，箱体本身不返还。"
            "所以它没有存储上限，也不能当作容器反复使用——放下去再敲掉，拿回的就是原来的八颗苹果。</p>"
            "<p><strong>用途</strong>：把八颗苹果压进一个方块，省下箱子与背包空间。"
            "代价是每箱多花一块木板，且取出时箱体消失，需要重新合成。</p>"
            "<p><strong>属性</strong>：以斧类工具开采最快，硬度 1.5，抗爆值 10，音效为木质。"
            "不使用工具亦可破坏，但耗时显著增加。</p>"
            "<p><strong>交互</strong>：右键不会打开界面。方块继承自普通的 Block，"
            "没有注册方块实体，也没有挂任何容器逻辑。</p>"
        ),
        "icon32": b64(I32 / "ae1__block_apple_crate.png"),
        "icon128": b64(I128 / "ae1__block_apple_crate.png"),
    })

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT_ITEMS.name}  ({OUT_ITEMS.stat().st_size/1024:.1f} KB)\n")
    for r in rows:
        print(f"  {r['name']:<12}{r['ename']:<20}{r['category']:<6}{len(r['html']):>4} 字符")
    texts = [r["html"] for r in rows]
    print(f"\n  正文唯一: {len(set(texts))}/{len(texts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
