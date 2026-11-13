#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nemo's Carpentry（classId 31737）通用文本 + A 包正文精简。

在 55 条代表页之上再建 5 条通用文本（按家具大类），代表页正文只留造型特点。
这样：
  - 大类共通说明只在通用文本里写一次
  - 50 种造型的差异写在各自的代表页
  - 577 条木材变体交给百科团队用 IRR 导入
"""
import json
import random
import re
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
A_SRC = BASE / "nc-代表页-31737.json"
OUT_A = BASE / "nc-代表页-31737.json"
OUT_COMMON = BASE / "nc-通用文本-31737.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

COLOR_ZH = {
    "white": "白色", "orange": "橙色", "magenta": "品红", "light_blue": "淡蓝",
    "yellow": "黄色", "lime": "黄绿", "pink": "粉色", "gray": "灰色",
    "light_gray": "淡灰", "cyan": "青色", "purple": "紫色", "blue": "蓝色",
    "brown": "棕色", "green": "绿色", "red": "红色", "black": "黑色",
}


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    return f"辛苦{s}机了"


# 5 条通用文本
COMMON = [
    ("common_chair", "椅子", "Chair",
     "<p>这些物品是 Nemo's Carpentry 添加的椅子类家具。</p>"
     "<p><strong>款式</strong>：椅子是模组里造型最多的一类，分基础款与五种命名款式"
     "（Pascal、Felix、Gregory、Lukas、Tommy）。其中 Pascal 与 Lukas、Tommy 带软垫，"
     "Lukas 与 Tommy 另有纯木版本。</p>"
     "<p><strong>颜色</strong>：Pascal 椅的软垫可染成十六种颜色；"
     "另有十六色吧椅与十六色理发椅，颜色只影响外观。</p>"
     "<p><strong>木材</strong>：每种造型都有十二种木材可选，"
     "更换木材只改变材质，几何形状完全一致。</p>"
     "<p><strong>合成</strong>：在木工工作台（Carpenter's Workbench）中制作。</p>"),

    ("common_table", "桌子", "Table",
     "<p>这些物品是 Nemo's Carpentry 添加的桌类家具。</p>"
     "<p><strong>款式</strong>：分咖啡桌（矮桌，桌面大而腿短）、立桌（高脚、单柱支撑）"
     "与经典桌（桌面较厚、单柱支撑）三种，另有咖啡桌的 Pascal 设计款。</p>"
     "<p><strong>用途</strong>：矮桌适合放在椅子或长椅前，"
     "高脚桌适合吧台或站立使用。</p>"
     "<p><strong>木材</strong>：每种造型都有十二种木材可选。</p>"
     "<p><strong>合成</strong>：在木工工作台中制作。</p>"),

    ("common_door", "玻璃门", "Glass Door",
     "<p>这些物品是 Nemo's Carpentry 添加的玻璃门及其门框。</p>"
     "<p><strong>安装</strong>：先在地面放置门框，再把玻璃门装到门框上。"
     "没有门框的门无法直接放置。</p>"
     "<p><strong>颜色</strong>：玻璃有十六种染色版本，另有不染色的普通玻璃门。</p>"
     "<p><strong>木材</strong>：门与门框的木材需要保持一致，十二种木材各有配对。</p>"
     "<p><strong>功能</strong>：与原版门一致，可双开，支持红石控制。</p>"
     "<p><strong>合成</strong>：在木工工作台中制作。</p>"),

    ("common_seat", "座椅", "Seat",
     "<p>这些物品是 Nemo's Carpentry 添加的座椅类家具。</p>"
     "<p><strong>款式</strong>：分散座款式——木桶座椅（以木桶为造型、上沿有金属箍）、"
     "公园长椅（长条多人座）、原木座椅（以整段原木为造型，九种木材）、"
     "菌柄座椅（下界木材专用，绯红与诡异各一）。</p>"
     "<p><strong>用途</strong>：与原版台阶或楼梯不同，这些座椅有明确的座位概念，"
     "适合作为装饰性家具摆在建筑里。</p>"
     "<p><strong>木材</strong>：每种造型都有多种木材可选。</p>"
     "<p><strong>合成</strong>：在木工工作台中制作。</p>"),

    ("common_carpentry", "木工设备", "Carpentry",
     "<p>这些物品是 Nemo's Carpentry 的木工设备与附属件。</p>"
     "<p><strong>木工工作台</strong>：整套家具都从它产出。在工作台界面中按配方直接做出成品，"
     "不需要额外的中间部件。</p>"
     "<p><strong>梯子</strong>：竖直放置用于垂直移动，与普通梯子功能一致。"
     "除绑扎竹梯外，十一种木材各有一把梯子，共十二种。"
     "其中橡木梯子沿用原版配方，其余为模组新增。</p>"
     "<p><strong>合成</strong>：木工工作台由两个工作台与四块木板合成，"
     "梯子与其余设备在工作台中制作。</p>"),
]

# 造型 → 通用文本
TYPE_TO_COMMON = {
    # 椅子
    "chair": "common_chair",
    "chair_pascal": "common_chair",
    "chair_felix": "common_chair",
    "chair_gregory": "common_chair",
    "chair_lukas": "common_chair",
    "chair_lukas_natural": "common_chair",
    "chair_tommy": "common_chair",
    "chair_tommy_natural": "common_chair",
    # 桌子
    "coffee_table": "common_table",
    "coffee_table_pascal": "common_table",
    "standing_table": "common_table",
    "table_the_classic": "common_table",
    # 门
    "glass_door": "common_door",
    "door_frame": "common_door",
    # 座椅
    "barrel_seat": "common_seat",
    "park_bench": "common_seat",
    "stem_seat": "common_seat",
    # 木工设备
    "ladder": "common_carpentry",
    "carpenters_workbench": "common_carpentry",
    "bound_bamboo_ladder": "common_carpentry",
}

COMMON_ZH = {c[0]: c[1] for c in COMMON}

# 造型特点（要保留在代表页的差异信息）
FEATURE = {
    # 以下按 models/block/seats 下各模型的实际 elements 尺寸描述：
    # 基础款背高 16、Pascal 21、Gregory 23、Lukas/Tommy 23
    "chair": "背高 16 格的基础款，整块背板、四条腿，没有软垫。",
    "chair_pascal": "背高 21 格，整块背板，座面与靠背带软垫。",
    "chair_felix": "背高仍为 16 格，但背板改为多根竖条拼成，并非整块（元素数最多的一款）。",
    "chair_gregory": "背高 23 格，双层靠背结构，是椅背最高的一款。",
    "chair_lukas": "背高 23 格，背板为竖条结构（非整块），座面带软垫。",
    "chair_lukas_natural": "Lukas 椅去掉软垫的全木版本，背板仍为竖条结构。",
    "chair_tommy": "背高 23 格，整块实心背板，结构最简洁（仅 6 个模型元素）。",
    "chair_tommy_natural": "Tommy 椅去掉软垫的全木版本，仍为整块背板。",
    "coffee_table": "矮桌，桌面大而腿短，四条腿支撑。",
    "coffee_table_pascal": "咖啡桌的 Pascal 设计款，桌面比例更紧凑。",
    "standing_table": "高脚桌，只有一根中心柱支撑。",
    "table_the_classic": "桌面较厚、单柱支撑的桌款。",
    "glass_door": "带玻璃的门，门板通透。",
    "barrel_seat": "以木桶为造型的座椅，上沿有金属箍。",
    "park_bench": "长条形座椅，可坐多人。",
    "stem_seat": "以菌柄为造型的座椅，下界木材专用。",
    "ladder": "靠墙放置的梯子，用于垂直移动。",
    "carpenters_workbench": "整套家具的产出点，承担家具的成型环节。",
    "bound_bamboo_ladder": "绑扎竹材制成的梯子，外观贴合竹建筑。",
}


def split_id(rid: str):
    WOODS = ["acacia", "bamboo", "birch", "cherry", "crimson", "dark_oak",
             "jungle", "mangrove", "oak", "pale_oak", "spruce", "warped"]
    core = rid.replace("block_", "").replace("item_", "")
    for w in sorted(WOODS, key=len, reverse=True):
        if core.startswith(w + "_"):
            return w, core[len(w) + 1:]
    return None, core


def common_of(r):
    """这条代表页该引用哪条通用文本。"""
    core = r["id"].replace("block_", "").replace("item_", "")
    w, t = split_id(r["id"])
    key = t if t else core      # 去掉木种前缀后判断

    # 染色椅子 / 染色门（颜色在 type 开头）
    m = re.match(r"(.+)_chair_pascal$", key)
    if m and m.group(1) in COLOR_ZH:
        return "common_chair"
    m = re.match(r"(.+)_stained_glass_door$", key)
    if m and m.group(1) in COLOR_ZH:
        return "common_door"
    if key.endswith("_bar_chair") or key.endswith("_barber_chair"):
        return "common_chair"
    if key == "glass_door_frame" or key.endswith("_glass_door_frame"):
        return "common_door"
    if key == "log_seat":
        return "common_seat"
    return TYPE_TO_COMMON.get(key)


def main() -> int:
    rows = json.loads(A_SRC.read_text(encoding="utf-8"))

    # 1) 通用文本
    common_rows = []
    for cid, name, en, html in COMMON:
        common_rows.append({
            "id": cid,
            "name": name,
            "ename": en,
            "regname": "",
            "category": "{文本}",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "Nemo's Carpentry 通用文本：本条不针对具体物品，"
                "用于承接同大类家具的共通说明，供代表页在附言中引用。"
                f"{tail()}"
            ),
            "html": html,
            "icon32": "",
            "icon128": "",
        })
    OUT_COMMON.write_text(json.dumps(common_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) A 包正文精简
    from collections import Counter
    refs = Counter()
    for r in rows:
        core = r["id"].replace("block_", "").replace("item_", "")
        cid = common_of(r)
        w, t = split_id(r["id"])

        # 造型特点
        key = t if t else core
        if key.endswith("_bar_chair"):
            feature = "吧台高度的高脚椅，座面较小。"
        elif key.endswith("_barber_chair"):
            feature = "理发椅造型，带可调靠背与脚踏。"
        elif "_stained_glass_door" in key:
            m = re.match(r"(.+)_stained_glass_door$", key)
            color = m.group(1) if m else ""
            feature = f"染色玻璃门，玻璃为{COLOR_ZH.get(color, color)}。"
        elif "_chair_pascal" in key:
            m = re.match(r"(.+)_chair_pascal$", key)
            color = m.group(1) if m else ""
            feature = f"Pascal 椅的{COLOR_ZH.get(color, color)}软垫版本。"
        elif key == "glass_door_frame" or key.endswith("_glass_door_frame"):
            feature = "玻璃门的配套门框，装门之前必须先放门框。"
        elif key == "log_seat":
            feature = "以原木为造型的座椅。"
        else:
            feature = FEATURE.get(key, "Nemo's Carpentry 添加的家具。")

        wood_note = ""
        if w:
            wood_zh = {
                "acacia": "金合欢", "bamboo": "竹", "birch": "白桦", "cherry": "樱花",
                "crimson": "绯红", "dark_oak": "深色橡木", "jungle": "丛林",
                "mangrove": "红树", "oak": "橡木", "pale_oak": "苍白橡木",
                "spruce": "云杉", "warped": "诡异",
            }.get(w, w)
            wood_note = (f"<p><strong>木材</strong>：本条目为{wood_zh}版。"
                         "同款另有其余木材可选，只改变材质、不改形状。</p>")

        r["html"] = (
            f"<p><strong>造型特点</strong>：{feature}</p>"
            + wood_note
        )
        if cid:
            refs[COMMON_ZH[cid]] += 1
        if cid:
            r["remark"] = (
                "Nemo's Carpentry 资料页：名称取自 lang/en_us.json（模组无中文语言文件）。"
                f"正文只写该造型的差异，共通说明需引用通用文本「{COMMON_ZH[cid]}」。"
                "同一造型的其余木材变体以 IRR 格式另行交付。"
                + tail()
            )
        else:
            r["remark"] = (
                "Nemo's Carpentry 资料页：名称取自 lang/en_us.json（模组无中文语言文件）。"
                "同一造型的其余木材变体以 IRR 格式另行交付。" + tail()
            )

    OUT_A.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"通用文本 {len(common_rows)} 条 → {OUT_COMMON.name}  ({OUT_COMMON.stat().st_size/1024:.1f} KB)")
    print(f"A 包 {len(rows)} 条 → {OUT_A.name}  ({OUT_A.stat().st_size/1024:.1f} KB)")
    print(f"\n引用分布: {dict(refs)}")
    print(f"无引用的: {[r['name'] for r in rows if not common_of(r)]}")
    print("\n正文抽样:")
    for r in rows[:3]:
        print(f"  [{r['name']}] {r['html'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
