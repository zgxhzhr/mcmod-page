#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Animania Cats & Dogs（classId 3863）23 个品种实体页。

按品种合并（公/母/幼三种形态写在一页里），不是每个实体一页。

属性来源（1.12.2 SRG）：
  EntityAnimaniaCat / Dog  基类血量 18、速度 0.3，狗另有攻击 2.5
  EntityTomBase / MaleDogBase  公 20 血
  EntityQueenBase / FemaleDogBase  母（继承基类 18 血）
  EntityKittenBase / PuppyBase  幼 12 血、速度 0.315

模组只有 en_us，名称用英文；实体无可用图标，icon32 留空。
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
OUT = BASE / "acd-实体导入-3863.json"
NS = "animania"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# 品种表：(显示名, 中文品种名, 类型, 是否自然生成, 备注)
BREEDS = [
    # ── 猫 8 种 ──
    ("Ragdoll", "布偶猫", "cat", False, None),
    ("American Shorthair", "美国短毛猫", "cat", False, None),
    ("Asiatic", "亚洲猫", "cat", False, None),
    ("Exotic", "异国猫", "cat", False, None),
    ("Norwegian", "挪威森林猫", "cat", False, None),
    ("Ocelot", "豹猫", "cat", True, "wild"),
    ("Siamese", "暹罗猫", "cat", False, None),
    ("Tabby", "虎斑猫", "cat", False, None),
    # ── 犬科 15 种 ──
    ("Bloodhound", "寻血猎犬", "dog", False, None),
    ("Chihuahua", "吉娃娃", "dog", False, None),
    ("Collie", "柯利犬", "dog", False, None),
    ("Corgi", "柯基犬", "dog", False, None),
    ("Dachshund", "腊肠犬", "dog", False, None),
    ("Fox", "狐狸", "dog", True, "wild"),
    ("German Shepherd", "德国牧羊犬", "dog", False, "shepherd"),
    ("Great Dane", "大丹犬", "dog", False, None),
    ("Greyhound", "灵缇犬", "dog", False, None),
    ("Husky", "哈士奇", "dog", False, None),
    ("Labrador", "拉布拉多犬", "dog", False, None),
    ("Pomeranian", "博美犬", "dog", False, None),
    ("Poodle", "贵宾犬", "dog", False, None),
    ("Pug", "巴哥犬", "dog", False, None),
    ("Wolf", "狼", "dog", True, "wild"),
]

# 属性表：类型 → (公) / (母) / (幼)
ATTR = {
    "cat": {
        "male":   {"hp": 20, "spd": 0.3,   "dmg": None, "label": "Tom（公）"},
        "female": {"hp": 18, "spd": 0.3,   "dmg": None, "label": "Queen（母）"},
        "young":  {"hp": 12, "spd": 0.315, "dmg": None, "label": "Kitten（幼）"},
    },
    "dog": {
        "male":   {"hp": 20, "spd": 0.3,   "dmg": 2.5, "label": "Male（公）"},
        "female": {"hp": 18, "spd": 0.3,   "dmg": 2.5, "label": "Female（母）"},
        "young":  {"hp": 12, "spd": 0.315, "dmg": 2.5, "label": "Puppy（幼）"},
    },
}

CAT_ATTACK = "小鸡、小孔雀、青蛙、仓鼠、雪貂、刺猬"
DOG_ATTACK = "山羊、绵羊、兔子"


def build_html(name: str, zh: str, kind: str, natural: bool, note) -> str:
    a = ATTR[kind]
    is_cat = kind == "cat"
    group = "猫科" if is_cat else "犬科"
    parts = [f"<p>{name}（{zh}）是 Cats &amp; Dogs 添加的{group}品种，"
             f"有成年公、成年母与幼崽三种形态。</p>"]

    # 属性表
    rows = []
    for key in ("male", "female", "young"):
        d = a[key]
        dmg = f"{d['dmg']} 点" if d["dmg"] else "默认值"
        rows.append(f"<tr><td>{d['label']}</td><td>{d['hp']}</td><td>{d['spd']}</td><td>{dmg}</td></tr>")
    parts.append(
        "<table><thead><tr><th>形态</th><th>生命值</th><th>移动速度</th><th>攻击伤害</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )
    parts.append("<p>公兽比母兽多 2 点生命值，幼崽只有 12 点但移动更快，长大后会补齐。</p>")

    # 行为
    target = CAT_ATTACK if is_cat else DOG_ATTACK
    parts.append(f"<p><strong>行为</strong>：未驯服时会攻击{target}这类动物，不针对玩家。"
                 f"驯服后停止攻击，转而保护主人并听从命令。</p>")

    # 生成方式
    if natural:
        parts.append("<p><strong>生成</strong>：可以在野外自然生成，属于野生" + group + "。</p>")
    else:
        parts.append("<p><strong>生成</strong>：不会自然生成，只能从宠物商人村民处购买。</p>")

    # 睡觉地点
    bed = "猫床或猫爬架" if is_cat else "狗垫或狗屋"
    parts.append(f"<p><strong>休息</strong>：睡在{bed}上，空闲时会自行回去。</p>")

    # 特例
    if note == "shepherd":
        parts.append("<p><strong>特殊能力</strong>：附近的绵羊与山羊会跟随它的移动路线。"
                     "狗跟在玩家身后时，羊也会跟着狗走，等于一个会自己移动的赶羊器。</p>")
    if note == "wild":
        parts.append("<p><strong>说明</strong>：这是模组里少数能在野外直接遇到的品种之一。</p>")

    parts.append(f"<p><strong>注册名</strong>：{NS} 命名空间下的 "
                 f"{'tom/queen/kitten' if is_cat else 'male/female/puppy'}_{name.lower().replace(' ', '_')}"
                 f" 三个实体。</p>")
    return "".join(parts)


def main() -> int:
    rows = []
    for name, zh, kind, natural, note in BREEDS:
        slug = name.lower().replace(" ", "_")
        rows.append({
            "id": slug,
            "name": name,
            "ename": "",
            "regname": f"{NS}:{slug}",
            "category": "被动生物",
            "type": "生物/实体",
            "maxstack": 64,
            "remark": (
                "Cats & Dogs 新增生物资料页：名称取自 lang/en_us.json（模组只有 en_us）。"
                "生命值、移动速度与攻击伤害取自 EntityAnimaniaCat / EntityAnimaniaDog 及"
                " EntityTomBase / EntityMaleDogBase / EntityKittenBase / EntityPuppyBase 的属性设置。"
                f"{tail()}"
            ),
            "html": build_html(name, zh, kind, natural, note),
            "icon32": "",
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    print(f"\n猫 {sum(1 for b in BREEDS if b[2]=='cat')} 种 / 犬科 {sum(1 for b in BREEDS if b[2]=='dog')} 种")
    print("\n=== 抽样 ===")
    for i in (0, 5, 6, 14):
        print(f"\n[{rows[i]['name']}]")
        print(f"  {rows[i]['html'][:220]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
