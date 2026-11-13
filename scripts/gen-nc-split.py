#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nemo's Carpentry（classId 31737）拆包交付。

632 条 = 586 条带木种变体 + 34 条特殊物件 + 12 个门框。
按 skill §6.2.0 拆成两包：

  A 包（我们的批量 JSON）：55 条代表页
     - 50 种家具造型各 1 条（oak 版优先）
     - 吧椅 / 理发椅 各 1 条（white 版）
     - 木工工作台、绑扎竹梯
     - 门框 1 条
  B 包（IRR 格式，交百科团队）：577 条其余变体
     每行一个 JSON（JSONL），字段按 IRR 的 ItemData
"""
import base64
import io
import json
import random
import re
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "nc-物品导入-31737.json"
ICONS = BASE / "nc-icons128"
OUT_A = BASE / "nc-代表页-31737.json"
OUT_B = BASE / "export" / "nemos-carpentry_item.json"

NS = "nemos-carpentry"
_PAW = ["呜喵", "喵呜", "喵喵"]

WOODS = ["acacia", "bamboo", "birch", "cherry", "crimson", "dark_oak",
         "jungle", "mangrove", "oak", "pale_oak", "spruce", "warped"]

WOOD_ZH = {
    "acacia": "金合欢", "bamboo": "竹", "birch": "白桦", "cherry": "樱花",
    "crimson": "绯红", "dark_oak": "深色橡木", "jungle": "丛林",
    "mangrove": "红树", "oak": "橡木", "pale_oak": "苍白橡木",
    "spruce": "云杉", "warped": "诡异",
}

# 造型说明
TYPE_DESC = {
    "chair": "基础款椅子，直靠背、四条腿，没有软垫。",
    "chair_pascal": "带软垫的椅子，造型圆润、靠背略矮。",
    "chair_felix": "靠背更高的椅款，椅背延伸到头部以上。",
    "chair_gregory": "造型较宽的椅款，座面与扶手都更开阔。",
    "chair_lukas": "带软垫的椅款，另有纯木版本。",
    "chair_lukas_natural": "Lukas 椅去掉软垫的版本，全木制作。",
    "chair_tommy": "带软垫的椅款，靠背为竖条板结构。",
    "chair_tommy_natural": "Tommy 椅去掉软垫的版本，全木制作。",
    "coffee_table": "矮桌，桌面大而腿短，适合放在沙发或椅子前。",
    "coffee_table_pascal": "咖啡桌的 Pascal 设计款。",
    "standing_table": "高脚桌，只有一根中心柱支撑。",
    "table_the_classic": "桌面较厚、单柱支撑的桌款。",
    "park_bench": "长条形座椅，可坐多人。",
    "barrel_seat": "以木桶为造型的座椅，上沿有金属箍。",
    "glass_door": "带玻璃的门，需要先放置配套门框。",
    "ladder": "靠墙放置的梯子，用于垂直移动。",
    "stem_seat": "以菌柄为造型的座椅，下界木材专用。",
}

COLOR_ZH = {
    "white": "白色", "orange": "橙色", "magenta": "品红", "light_blue": "淡蓝",
    "yellow": "黄色", "lime": "黄绿", "pink": "粉色", "gray": "灰色",
    "light_gray": "淡灰", "cyan": "青色", "purple": "紫色", "blue": "蓝色",
    "brown": "棕色", "green": "绿色", "red": "红色", "black": "黑色",
}


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def split_id(rid: str):
    """block_<wood>_<type> → (wood, type)；无木种前缀返回 (None, id)。"""
    core = rid.replace("block_", "").replace("item_", "")
    for w in sorted(WOODS, key=len, reverse=True):
        if core.startswith(w + "_"):
            return w, core[len(w) + 1:]
    return None, core


def b64_file(p: Path):
    if not p.exists():
        return ""
    buf = io.BytesIO()
    Image.open(p).convert("RGBA").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


ICONS32 = BASE / "nc-icons32"


def icon_path(rid: str, size: int = 128):
    """块用 block_<id>，物品用 item_<id>。size 决定取哪个目录。"""
    d = ICONS if size == 128 else ICONS32
    core = rid
    if core.startswith("block_"):
        return d / f"{NS}__block_{core[6:]}.png"
    if core.startswith("item_"):
        return d / f"{NS}__item_{core[5:]}.png"
    return d / f"{NS}__block_{core}.png"


def type_zh(ftype: str) -> str:
    """把造型 id 转成中文名称。"""
    # 染色椅子：<color>_chair_pascal
    m = re.match(r"(.+)_chair_pascal$", ftype)
    if m and m.group(1) in COLOR_ZH:
        return f"{COLOR_ZH[m.group(1)]} Pascal 椅"
    # 染色玻璃门：<color>_stained_glass_door
    m = re.match(r"(.+)_stained_glass_door$", ftype)
    if m and m.group(1) in COLOR_ZH:
        return f"{COLOR_ZH[m.group(1)]}染色玻璃门"
    simple = {
        "chair": "椅子", "coffee_table": "咖啡桌", "coffee_table_pascal": "Pascal 咖啡桌",
        "standing_table": "立桌", "table_the_classic": "经典桌", "park_bench": "公园长椅",
        "barrel_seat": "木桶座椅", "glass_door": "玻璃门", "ladder": "梯子",
        "stem_seat": "菌柄座椅",
        "chair_felix": "Felix 椅", "chair_gregory": "Gregory 椅",
        "chair_lukas": "Lukas 椅", "chair_lukas_natural": "Lukas 椅（纯木）",
        "chair_tommy": "Tommy 椅", "chair_tommy_natural": "Tommy 椅（纯木）",
    }
    return simple.get(ftype, ftype.replace("_", " "))


def body_for(ftype, wood, name):
    zh, _ = TYPE_DESC.get(ftype, ("家具", "")), None
    desc = TYPE_DESC.get(ftype, "Nemo's Carpentry 添加的家具。")
    wzh = WOOD_ZH.get(wood, wood) if wood else ""
    head = f"{name}是 Nemo's Carpentry 添加的{type_zh(ftype)}"
    if wzh:
        head += f"，材质为{wzh}"
    head += "。</p>"
    return (
        f"<p>{head}"
        f"<p><strong>造型</strong>：{desc}</p>"
        + (f"<p><strong>木材</strong>：同一种造型有十二种木材可选，本条目为{wzh}版。"
           "更换木材只改变材质，几何形状完全一致。</p>" if wzh else "")
        + "<p><strong>合成</strong>：在木工工作台（Carpenter's Workbench）中制作。</p>"
    )


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    # 分组
    types = {}
    special = []
    frames = []
    for r in rows:
        rid = r["id"]
        if "door_frame" in rid:
            frames.append(r)
            continue
        w, t = split_id(rid)
        if w:
            types.setdefault(t, {})[w] = r
        else:
            special.append(r)

    # A 包选取
    a_rows = []
    a_ids = set()

    # 1) 每种造型取 oak（没有就取第一个）
    for t, variants in sorted(types.items()):
        pick = variants.get("oak") or list(variants.values())[0]
        a_rows.append(pick)
        a_ids.add(pick["id"])

    # 2) 特殊物件：吧椅/理发椅各取 white，其余全取
    bar = [r for r in special if r["id"].endswith("_bar_chair") and "barber" not in r["id"]]
    barber = [r for r in special if r["id"].endswith("_barber_chair")]
    others = [r for r in special if r not in bar and r not in barber]

    for group, label in ((bar, "吧椅"), (barber, "理发椅")):
        if not group:
            continue
        pick = next((r for r in group if "white" in r["id"]), group[0])
        a_rows.append(pick)
        a_ids.add(pick["id"])

    for r in others:
        a_rows.append(r)
        a_ids.add(r["id"])

    # 3) 门框取 oak
    if frames:
        pick = next((r for r in frames if "oak" in r["id"]), frames[0])
        a_rows.append(pick)
        a_ids.add(pick["id"])

    # A 包正文
    for r in a_rows:
        core = r["id"].replace("block_", "").replace("item_", "")
        if "door_frame" in core:
            r["html"] = (
                "<p>玻璃门框是 Nemo's Carpentry 添加的门配件，是安装玻璃门的前提。</p>"
                "<p><strong>用途</strong>：先在地面放置门框，再把玻璃门装到门框上。"
                "没有门框的门无法直接放置。</p>"
                "<p><strong>木材</strong>：十二种木材各有一种门框，材质需要与门保持一致。</p>"
                "<p><strong>合成</strong>：在木工工作台中制作。</p>"
            )
        elif core == "carpenters_workbench":
            r["html"] = (
                "<p>Carpenter's Workbench（木工工作台）是 Nemo's Carpentry 的核心方块，"
                "整套家具都从它产出。</p>"
                "<p><strong>作用</strong>：把原版木材加工成家具部件，再组装成成品。</p>"
                "<p><strong>与工作台的区别</strong>：普通工作台只处理配方，"
                "木工工作台还承担家具的成型环节。</p>"
            )
        elif core == "bound_bamboo_ladder":
            r["html"] = (
                "<p>Bound Bamboo Ladder（绑扎竹梯）是模组添加的梯子。</p>"
                "<p><strong>用途</strong>：竖直放置用于垂直移动，与普通梯子功能一致，"
                "材质为绑扎的竹材，外观更贴合竹制建筑。</p>"
                "<p><strong>合成</strong>：在木工工作台中制作。</p>"
            )
        elif core.endswith("_bar_chair") or core.endswith("_barber_chair"):
            kind = "吧椅" if core.endswith("_bar_chair") else "理发椅"
            r["html"] = (
                f"<p>{r['name']}是 Nemo's Carpentry 添加的{kind}。</p>"
                f"<p><strong>颜色</strong>：共十六种颜色，本条目为其中一种。"
                f"颜色只影响外观，形状完全一致。</p>"
                "<p><strong>合成</strong>：在木工工作台中制作。</p>"
            )
        else:
            w, t = split_id(r["id"])
            r["html"] = body_for(t, w, r["name"])
        # icon32 用独立渲染的 32px 图，不从 128 缩，避免糊
        import base64 as _b64
        import io as _io
        from PIL import Image as _Img
        p32 = icon_path(r["id"], 32)
        if p32.exists():
            buf = _io.BytesIO()
            _Img.open(p32).convert("RGBA").save(buf, format="PNG", optimize=True)
            r["icon32"] = _b64.b64encode(buf.getvalue()).decode("ascii")

        r["remark"] = (
            "Nemo's Carpentry 资料页：名称取自 lang/en_us.json（模组无中文语言文件）。"
            "本条为该类造型的代表页，同一造型的其余木材变体以 IRR 格式另行交付。"
            + tail()
        )

    OUT_A.write_text(json.dumps(a_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # B 包：其余全部，IRR 格式（JSONL）
    OUT_B.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for r in rows:
        if r["id"] in a_ids:
            continue
        rid = r["id"]
        core = rid.replace("block_", "").replace("item_", "")
        # type 判据对应 getBlockFromItem(item) != Blocks.AIR：
        # 有 blockstates/<id>.json 的就是方块，否则是纯物品
        is_item = not (BASE / "nc/assets/nemos-carpentry/blockstates" / f"{core}.json").exists()
        # smallIcon 与 largeIcon 是两个独立尺寸，不能复用同一张图
        small = b64_file(icon_path(rid, 32))
        large = b64_file(icon_path(rid, 128))
        # 严格照 ItemData 的字段与取值：
        #   maxDurability = getMaxDamage() + 1，所以无耐久物品是 1 不是 0
        #   TagList 空时设为 null，Gson 默认不序列化 null → 字段直接不出现
        #   CreativeTabName 同理（只有拿到创造标签页名才有值）
        obj = {
            "name": r["name"],          # zh_cn 环境下的显示名
            "englishName": r["name"],   # en_us 环境下的显示名
            "registerName": f"{NS}:{core}",
            "type": "Item" if is_item else "Block",
            "maxStackSize": r.get("maxstack", 64),
            "maxDurability": 1,         # 0 + 1
            "smallIcon": small,
            "largeIcon": large,
        }
        lines.append(json.dumps(obj, ensure_ascii=False))
    OUT_B.write_text("\n".join(lines), encoding="utf-8")

    print(f"A 包（代表页）{len(a_rows)} 条 → {OUT_A.name}  ({OUT_A.stat().st_size/1024:.1f} KB)")
    print(f"B 包（IRR）   {len(lines)} 条 → {OUT_B.relative_to(BASE)}  ({OUT_B.stat().st_size/1024/1024:.2f} MB)")
    print(f"合计 {len(a_rows)+len(lines)} 条（原 {len(rows)} 条）")

    from collections import Counter
    print(f"\nA 包分类: {dict(Counter(r['category'] for r in a_rows))}")
    print(f"B 包 type: {dict(Counter('Item' if r['id'].startswith('item_') else 'Block' for r in rows if r['id'] not in a_ids))}")
    # 抽查 A 包正文
    print("\nA 包正文抽样:")
    for r in a_rows[:3]:
        print(f"  [{r['name']}] {r['html'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
