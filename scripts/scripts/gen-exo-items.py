#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 EXO-Craft（classId 1556）新增 14 条资料的批量导入 JSON。

字段按 skill §6.6：id / name / ename / regname / category / type / remark / html / icon32 / maxstack
分类：装备（强化铁套装）、材料（Matrix / Unit）、模块（6 个模块）
名称用英文（mcmod 现有页面全部是英文名，且模组没有 zh_cn.json）
"""
import base64
import io
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow", file=sys.stderr)
    sys.exit(1)

JAR = Path(r"E:\Mod\百科-语料\jar-analyze\exo")
OUT = Path(r"E:\Mod\百科-语料\jar-analyze\exo-新增-1556.json")
NS = "exocraft"
REMARK = ("EXO-Craft 2.3.7 新增资料页：按模组源码的注册表、语言文件、配方与 "
          "loot table 整理，未添加源码中不存在的内容。辛苦喵呜机了")

# (注册id, 图标文件, 分类, 堆叠, 正文)
ITEMS = [
    # ── 5 个矩阵 ──
    ("matrix_atlas", "matrix_atlas.png", "材料", 64,
     "<p>Atlas 矩阵是合成 Atlas 单位的组件，本模组不直接提供合成配方。</p>"
     "<p><strong>获取</strong>：需要借助外部模组。装了 Energized Power 时，在装配机里用能量水晶矩阵、钻石、四份红石粉与一个基础电路产出；装了 Industrial Reborn 时，开启废料箱有 5% 概率得到。</p>"
     "<p><strong>用途</strong>：与空单位在工作台无序合成，得到 Atlas 单位，再用于锻造 Atlas 战甲。</p>"
     "<p>没有安装上述任一模组时，该矩阵无法获得，Atlas 战甲也就无法制作。</p>"),
    ("matrix_ion", "matrix_ion.png", "材料", 64,
     "<p>Ion 矩阵是合成 Ion 单位的组件，本模组不直接提供合成配方。</p>"
     "<p><strong>获取</strong>：需要借助外部模组。装了 Energized Power 时，在装配机里用能量水晶矩阵、钻石、四份红石粉与一个基础电路产出；装了 Industrial Reborn 时，开启废料箱有 5% 概率得到。</p>"
     "<p><strong>用途</strong>：与空单位在工作台无序合成，得到 Ion 单位，再用于锻造 Ion 战甲。</p>"),
    ("matrix_legion", "matrix_legion.png", "材料", 64,
     "<p>Legion 矩阵是合成 Legion 单位的组件，本模组不直接提供合成配方。</p>"
     "<p><strong>获取</strong>：需要借助外部模组。装了 Energized Power 时，在装配机里用能量水晶矩阵、钻石、四份红石粉与一个基础电路产出；装了 Industrial Reborn 时，开启废料箱有 5% 概率得到。</p>"
     "<p><strong>用途</strong>：与空单位在工作台无序合成，得到 Legion 单位，再用于锻造 Legion 战甲。</p>"),
    ("matrix_ogre", "matrix_ogre.png", "材料", 64,
     "<p>Ogre 矩阵是合成 Ogre 单位的组件，本模组不直接提供合成配方。</p>"
     "<p><strong>获取</strong>：需要借助外部模组。装了 Energized Power 时，在装配机里用能量水晶矩阵、钻石、四份红石粉与一个基础电路产出；装了 Industrial Reborn 时，开启废料箱有 5% 概率得到。</p>"
     "<p><strong>用途</strong>：与空单位在工作台无序合成，得到 Ogre 单位，再用于锻造 Ogre 战甲。</p>"),
    ("matrix_stryder", "matrix_stryder.png", "材料", 64,
     "<p>Stryder 矩阵是合成 Stryder 单位的组件，本模组不直接提供合成配方。</p>"
     "<p><strong>获取</strong>：需要借助外部模组。装了 Energized Power 时，在装配机里用能量水晶矩阵、钻石、四份红石粉与一个基础电路产出；装了 Industrial Reborn 时，开启废料箱有 5% 概率得到。</p>"
     "<p><strong>用途</strong>：与空单位在工作台无序合成，得到 Stryder 单位，再用于锻造 Stryder 战甲。</p>"),
    # ── 2 个单位 ──
    ("unit_empty", "unit_empty.png", "材料", 16,
     "<p>空单位是所有战甲单位的载体，本身没有套属效果。</p>"
     "<p><strong>获取</strong>：在工作台用四块铁锭与一个红石电路合成，配方为十字排列，中心放红石电路。</p>"
     "<p><strong>用途</strong>：与任一矩阵在工作台无序合成，得到对应的战甲单位。例如空单位加 Atlas 矩阵得到 Atlas 单位。</p>"),
    ("unit_old", "unit_old.png", "材料", 16,
     "<p>旧单位是可以开出战甲单位的消耗品。</p>"
     "<p><strong>获取</strong>：远古城市、堡垒宝箱与末地城宝藏的箱子中各有 10% 概率出现一个；也可以向流浪商人购买。</p>"
     "<p><strong>用途</strong>：右键使用会消耗一个，并随机开出一件战甲单位（Atlas、Ion、Legion、Ogre、Stryder 各 20%）。</p>"
     "<p>开出的单位要在锻造台上才能变成成品战甲，还需要强化铁部件与能量核心。</p>"),
    # ── 6 个模块 ──
    ("blank_module", "blank_module.png", "模块", 16,
     "<p>空白模块是其余五个模块的合成底材，本身没有功能。</p>"
     "<p><strong>获取</strong>：在工作台用三块铜锭、三块铁锭与一个红石电路合成，配方为三行：顶行三铜锭，中间行铁锭、红石电路、铁锭，底行三铁锭。</p>"
     "<p><strong>用途</strong>：与不同材料无序合成，产出雪地行者、高级护目镜、滑翔、威慑与防火涂层五种功能模块。</p>"),
    ("snow_walker_module", "snow_walker_module.png", "模块", 16,
     "<p>雪地行者模块让玩家可以在细雪上行走，不会陷进去。</p>"
     "<p><strong>获取</strong>：在工作台用空白模块与四张皮革无序合成。</p>"
     "<p><strong>安装</strong>：把模块拖到任意一件战甲上即可安装，安装后模块被消耗，效果记录在战甲的物品数据里。</p>"),
    ("advanced_visor_module", "advanced_visor_module.png", "模块", 16,
     "<p>高级护目镜模块让玩家直视末影人时不会引起它的敌意。</p>"
     "<p><strong>获取</strong>：在工作台用空白模块与三块淡蓝色染色玻璃板无序合成。</p>"
     "<p><strong>安装</strong>：把模块拖到任意一件战甲上即可安装，安装后模块被消耗，效果记录在战甲的物品数据里。适合需要频繁下矿或穿越末地的场合。</p>"),
    ("glider_module", "glider_module.png", "模块", 16,
     "<p>滑翔模块让玩家可以在空中滑翔。</p>"
     "<p><strong>获取</strong>：在工作台用空白模块与鞘翅无序合成。</p>"
     "<p><strong>安装</strong>：把模块拖到任意一件战甲上即可安装，安装后模块被消耗。戴上战甲后无需再占用胸甲栏放鞘翅，可以把它留给战甲本身。</p>"),
    ("deterrence_module", "deterrence_module.png", "模块", 16,
     "<p>威慑模块让猪灵接受玩家，不再主动攻击。</p>"
     "<p><strong>获取</strong>：在工作台用空白模块与四块金锭无序合成。</p>"
     "<p><strong>安装</strong>：把模块拖到任意一件战甲上即可安装，安装后模块被消耗。效果等同于始终穿着金制装备，进入堡垒遗迹时不会被猪灵敌视。</p>"),
    ("fire_resistant_coating_module", "fire_resistant_coating_module.png", "模块", 16,
     "<p>防火涂层模块让装有它的战甲掉落后不会被火焰或岩浆烧毁。</p>"
     "<p><strong>获取</strong>：模组当前版本没有提供该模块的合成配方，工作台与其它机器都无法制作，只能通过创造模式或其它模组的途径取得。</p>"
     "<p><strong>安装</strong>：把模块拖到任意一件战甲上即可安装，安装后模块被消耗。适合在下界活动时避免战甲因意外掉落而损毁。</p>"),
    # ── 强化铁套装（4 件合并成一页）──
    ("reinforced_iron_chestplate", "reinforced_iron_chestplate.png", "装备", 1,
     "<p>强化铁套装是本模组的基础护甲，也是锻造其余五套动力战甲时的模板。</p>"
     "<p><strong>组成</strong>：头盔、胸甲、护腿与靴子四件，全部由强化铁板按护甲形状在工作台合成。头盔需五块强化铁板，胸甲八块，护腿七块，靴子四块。</p>"
     "<p><strong>护甲值</strong>：头盔 3、胸甲 8、护腿 6、靴子 3，全套合计 20 点。耐久倍率 35，附魔能力 10，可以在附魔台正常附魔。</p>"
     "<p><strong>套装效果</strong>：无。这一套只提供基础护甲，不带任何能力加成，与其余五套的高阶战甲不同。</p>"
     "<p><strong>用途</strong>：在锻造台上把强化铁部件放在模板槽，配合能量核心与战甲单位，可以锻造成对应系列的动力战甲。因此这一套既是过渡装备，也是后续装备的原料。</p>"),
]


def b64_png(path: Path, size: int = 32) -> str:
    img = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    img.resize((size, size), Image.NEAREST).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    lang = json.loads((JAR / "assets" / NS / "lang" / "en_us.json").read_text(encoding="utf-8"))
    tex = JAR / "assets" / NS / "textures" / "item"

    rows = []
    missing_tex = []
    for rid, icon, cat, stack, html in ITEMS:
        # 英文名：装备类查 item.exocraft.<id>，套装页用胸甲的名字去掉 Chestplate
        en = lang.get(f"item.{NS}.{rid}") or lang.get(f"block.{NS}.{rid}") or ""
        if rid == "reinforced_iron_chestplate":
            en = "Reinforced Iron Exosuit 套装"
        p = tex / icon
        if not p.exists():
            missing_tex.append(icon)
            icon_b64 = ""
        else:
            icon_b64 = b64_png(p)

        rows.append({
            "id": rid,
            "name": en,
            "ename": en,
            "regname": f"{NS}:{rid}",
            "category": cat,
            "type": "物品/方块",
            "maxstack": stack,
            "remark": REMARK,
            "html": html,
            "icon32": icon_b64,
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    for r in rows:
        print(f"  {r['regname']:<36} {r['name']:<30} [{r['category']}] "
              f"正文 {len(r['html'])} 字符 图标 {len(r['icon32'])}")
    if missing_tex:
        print(f"⚠ 缺纹理：{missing_tex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
