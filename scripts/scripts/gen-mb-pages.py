#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Moar Boats（classId 1252）批量编辑 JSON —— 给 23 个资料页补正文。

这些页面已经存在（id 352175–352199），是「编辑」而不是「新增」，
所以只带 5 个字段：id / name / editRemark / editNote / html。

「座椅」页已有可用正文（讲的是怎么装、怎么卸），保留并在其后补充属性说明；
其余 22 页从零写。

物品名与作用来自：
  assets/moarboats/lang/en_us.json   （英文名、GUI 提示语、槽位分类）
  assets/moarboats/lang/zh_cn.json   （中文名，只有 26 条，覆盖 helm/rope/modular_boat）
  data/moarboats/recipes/            （合成配方）
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = Path(r"C:\Users\MKIII\Downloads\mcmod-全部原文-2026-11-11T03-01-08.json")
OUT = BASE / "mb-编辑-1252.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# 每页正文：{页面 id: (editNote, html)}
PAGES = {
    352176: ("补充属性说明，保留原有的安装/卸载方法", None),  # 座椅，特殊处理

    352177: ("说明船舵的用途与自动驾驶功能",
             "<p>船舵是模块化船的导航模块，决定船的行驶方向。</p>"
             "<p><strong>用途</strong>：装上之后船才有明确的前进方向，可以手动驾驶。"
             "配合 Mapping table 还能编辑航线，让船按预设路线自动航行。</p>"
             "<p><strong>安装位置</strong>：导航（navigation）槽位，每艘船只装一个。</p>"
             "<p><strong>路径编辑</strong>：装上船舵后，界面里会多出「编辑路径」入口，"
             "可以绘制直线、环路、单向路线，也可以打开寻路让船自己绕开地形。</p>"),

    352178: ("说明 Rudder 与船舵的区别",
             "<p>Rudder 是船的转向部件，控制船的左右转向。</p>"
             "<p><strong>与船舵的区别</strong>：船舵（helm）负责整体导航与航线编辑，"
             "决定船往哪里走；Rudder 只负责转向动作本身。两者装在不同槽位，可以同时存在。</p>"
             "<p><strong>安装位置</strong>：导航（navigation）槽位。</p>"),

    352179: ("说明破冰模块的作用",
             "<p>Icebreaker 是破冰模块，装在船上后可以撞碎冰面前进。</p>"
             "<p><strong>用途</strong>：解决冰原与冻洋水域的通行问题。原版的船会被冰面挡住，"
             "装上这个模块后可连续破冰行驶，无需避开冰面。</p>"
             "<p><strong>安装位置</strong>：杂项（misc）槽位。</p>"),

    352180: ("说明船绳的连接方式与限制",
             "<p>船绳用于把多条船连接成一列。</p>"
             "<p><strong>用法</strong>：先对船链最后一艘使用，再对前一艘使用，两者即建立连接。"
             "连接后前船会拖动后船一同行驶，适合大批量货物运输。</p>"
             "<p><strong>限制</strong>：已经连上前端或后端的船无法再连（界面会提示「无法往前」「无法后退」），"
             "也不能把船连到自己身上。</p>"),

    352181: ("说明潜水瓶的作用",
             "<p>Diving Bottle 是船用的潜水装备。</p>"
             "<p><strong>用途</strong>：装在船上之后，船可以下潜到水面以下行驶。"
             "用于探索海底、穿越水下洞穴或绕开水面障碍。</p>"
             "<p><strong>安装位置</strong>：杂项（misc）槽位。</p>"),

    352182: ("说明跨水红石导线的用途",
             "<p>Waterborne redstone conductor 是跨水传输红石信号的元件。</p>"
             "<p><strong>用途</strong>：原版的红石无法在水面上传递信号，"
             "这个元件用来把红石线路跨过水域连接起来，让两岸的红石装置保持联通。</p>"),

    352183: ("说明跨水比较器的用途",
             "<p>Waterborne comparator 是跨水使用的红石比较器。</p>"
             "<p><strong>用途</strong>：在水面上传递并比较红石信号强度。"
             "与 Waterborne redstone conductor 配合，可以在水上搭出完整的红石逻辑线路。</p>"),

    352184: ("说明创造引擎的特性",
             "<p>Creative mode Engine 是仅创造模式可用的船用引擎。</p>"
             "<p><strong>特性</strong>：提供无限动力，不需要燃料，也不会耗尽。"
             "界面显示为「无限动力」。用于创造模式下的建造与测试，生存模式无法正常获得。</p>"
             "<p><strong>安装位置</strong>：引擎（engine）槽位。</p>"),

    352185: ("说明金票的用途",
             "<p>Golden Ticket (Empty) 是一张空白的金票。</p>"
             "<p><strong>用途</strong>：属于模组内的凭证类物品，空白状态需要经过处理后才能使用。"
             "具体用途在模组内没有额外说明，属预留或未完成的内容。</p>"),

    352186: ("说明带路径地图与自动驾驶的关系",
             "<p>Map with path 是记录了航线的地图。</p>"
             "<p><strong>来源</strong>：在 Mapping table 里给船绘制路线后生成。</p>"
             "<p><strong>用途</strong>：把地图放进装了船舵的船，船就会按地图上的路线自动航行。"
             "这是模组实现自动驾驶的方式——玩家不必全程坐在船上。</p>"
             "<p>路线可以设置为直线、环路、单向或末端反向，也可以打开寻路让船绕开地形。</p>"),

    352187: ("说明区块加载器的作用",
             "<p>Boat Chunk Loader 是船用的区块加载模块。</p>"
             "<p><strong>用途</strong>：让船所在的区块保持加载状态。"
             "船在自动航行时若离开玩家视野，所在区块会被卸载并导致船停止；"
             "装上这个模块后区块持续加载，船可长期航行。</p>"
             "<p><strong>搭配</strong>：通常与 Map with path 一起用，实现无人值守的长途运输。</p>"
             "<p><strong>安装位置</strong>：杂项（misc）槽位。</p>"),

    352188: ("说明桨作为引擎的特点",
             "<p>Paddles（桨）是模块化船的人力引擎。</p>"
             "<p><strong>特点</strong>：不消耗任何燃料，装上即可划动。速度慢于熔炉引擎与太阳能引擎，"
             "优势在于零消耗，适合短途或前期使用。</p>"
             "<p><strong>安装位置</strong>：引擎（engine）槽位。</p>"),

    352189: ("说明货物限制器的作用",
             "<p>Cargo Stopper 是限制货物堆积的组件。</p>"
             "<p><strong>用途</strong>：控制船上货物槽位的填充上限，避免物品无序堆叠导致取用困难。"
             "用于整理运输船的储物空间。</p>"),

    352190: ("说明船用电池的作用",
             "<p>Boat Energy Battery 是储存船用能量的方块。</p>"
             "<p><strong>用途</strong>：为船上的用电设备提供能量储备。"
             "可以放在岸边作为补给站，也可以随船携带。</p>"
             "<p><strong>配合</strong>：与 Boat Energy Charger、Boat Energy Discharger 一起构成完整的充放电链路。</p>"),

    352191: ("说明充能器的作用",
             "<p>Boat Energy Charger 是给船上电池充能的方块。</p>"
             "<p><strong>用法</strong>：放在岸边，船停靠在旁边即可自动为船上的电池补充能量。"
             "适合长距离航线——中途返回补一次，比随船携带大量燃料节省空间。</p>"),

    352192: ("说明放电器的作用",
             "<p>Boat Energy Discharger 是把船上能量放出的方块。</p>"
             "<p><strong>用法</strong>：放在岸边，把船上电池中储存的能量转移到外部设备或电网。</p>"
             "<p><strong>与充能器的区别</strong>：Charger 是岸上给船充电，Discharger 是把船上的电取出来，方向相反。</p>"),

    352193: ("说明流体罐的作用",
             "<p>Boat Fluid Tank 是储存流体的方块。</p>"
             "<p><strong>用途</strong>：作为船用流体的容器，可以装在船上随船运输，也可以放在岸边作为中转储罐。</p>"
             "<p><strong>配合</strong>：与 Boat Fluid Loader、Boat Fluid Unloader 配合完成装卸。</p>"),

    352194: ("说明流体装载器的作用",
             "<p>Boat Fluid Loader 是把流体装入船上储罐的方块。</p>"
             "<p><strong>用法</strong>：放在岸边，船停靠在旁边时把流体从外部储罐转移到船上的流体罐中。</p>"),

    352195: ("说明流体卸载器的作用",
             "<p>Boat Fluid Unloader 是把船上流体卸出的方块。</p>"
             "<p><strong>用法</strong>：放在岸边，船停靠时把船上流体罐中的流体转移到外部储罐。</p>"
             "<p><strong>与装载器的区别</strong>：Loader 是往船上装，Unloader 是从船上卸，方向相反。</p>"),

    352196: ("说明地图台的作用",
             "<p>Mapping table 是用来绘制船用航线的方块。</p>"
             "<p><strong>用途</strong>：打开界面后可以给船编辑航行路线，生成带路径的地图。"
             "编辑器支持直线、环路、单向路线与末端反向，也可以打开寻路让船自动绕开地形。</p>"
             "<p><strong>操作</strong>：拖动右键移动视图，鼠标滚轮缩放。"
             "工具栏里有标记与橡皮擦两种笔刷。</p>"),

    352199: ("说明模块化船的组装方式与槽位",
             "<p>模块化船是本模组的核心，一条可以自己组装的船。</p>"
             "<p><strong>槽位</strong>：船上有四类安装点，每类只能装一个模块。</p>"
             "<table><thead><tr><th>槽位</th><th>可装的模块</th></tr></thead><tbody>"
             "<tr><td>引擎（engine）</td><td>熔炉引擎、太阳能引擎、桨、创造引擎</td></tr>"
             "<tr><td>导航（navigation）</td><td>船舵、Rudder</td></tr>"
             "<tr><td>存储（storage）</td><td>箱子、流体罐、发射器、投掷器</td></tr>"
             "<tr><td>杂项（misc）</td><td>座椅、锚、潜水瓶、破冰装置、钓鱼模块、区块加载器</td></tr>"
             "</tbody></table>"
             "<p><strong>组装</strong>：先放置船，再打开船的界面把模块放进对应槽位。"
             "手持模块对船右键亦可直接装入。</p>"
             "<p><strong>颜色</strong>：船体有十六种颜色，对应原版染料色系，只影响外观不影响功能。</p>"),

    352175: ("说明动物船的用途",
             "<p>Animal Boat 是专用于运输动物的船型。</p>"
             "<p><strong>用途</strong>：与普通模块化船不同，它的船上空间用于安置动物，"
             "适合把牛羊等生物跨水域搬运，不必再赶着它们涉水。</p>"
             "<p><strong>与模块化船的区别</strong>：模块化船安装的是功能模块，动物船承载的是生物，用途不同。</p>"),
}

# 「座椅」原有正文保留，追加属性说明
SEAT_APPEND = (
    "<p><strong>槽位</strong>：占用杂项（misc）安装点。</p>"
    "<p><strong>坐下</strong>：坐在船上时，空手右键船体即可就座，界面会提示「坐下享受旅程」。</p>"
    "<p><strong>配置</strong>：座椅本身没有可调选项，打开界面只会提示无需配置。</p>"
)


def main() -> int:
    src = json.loads(SRC.read_text(encoding="utf-8-sig"))
    rows = []

    for it in src["items"]:
        rid = it["id"]
        name = it["name"]
        old_html = it.get("html", "")

        if rid == 352176:
            # 座椅：保留原正文，追加属性段
            body = old_html.rstrip()
            note, _ = PAGES[352176]
            html = body + SEAT_APPEND
            edit_note = note
        else:
            entry = PAGES.get(rid)
            if not entry:
                print(f"  ⚠ 未覆盖: {rid} {name}")
                continue
            edit_note, html = entry
            if html is None:
                continue

        rows.append({
            "id": rid,
            "name": name,
            "editRemark": (
                "Moar Boats 资料页补充正文：物品作用依据 assets/moarboats/lang 下的英文名、"
                "GUI 提示语与槽位分类，合成与用途参照模组内实现。"
                f"{tail()}"
            ),
            "editNote": edit_note,
            "html": html,
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    print("字段:", list(rows[0].keys()))
    for r in rows:
        print(f"  {r['id']} {r['name']:<32} {len(r['html']):>5} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
