#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promenade（classId 5300）自然生成页 —— 5 个生物群系 + 1 个结构 + 1 个植被汇总。

不建物品/方块页（用户明确要求）。

数据来源：
  data/promenade/worldgen/biome/*.json         生物群系定义（含 attributes 里的生物生成）
  data/promenade/worldgen/structure/*.json     结构定义
  data/promenade/worldgen/structure_set/*.json 生成间距
  data/promenade/worldgen/feature/*.json       地物
  assets/promenade/lang/*.json                 中英文名
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
OUT = BASE / "prom-自然生成-5300.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# 群系：id, 显示名, 中文名有无, 温度, downfall, 降水, 维度, 生物统计, 描述
BIOMES = [
    ("blush_sakura_grove", "Blush Sakura Grove", None, 0.6, 0.4, True, "主世界",
     [("monster", "蜘蛛 100、僵尸 95、僵尸村民 5、骷髅 100、苦力怕 100、史莱姆 100、末影人 10、女巫 5"),
      ("creature", "羊 12、猪 10、鸡 10、牛 8、狼 5、狐 16、熊猫 2"),
      ("ambient", "蝙蝠 10"),
      ("underground_water_creature", "发光鱿鱼 10")],
     "两片樱花林之一，粉色调。温度 0.6、有降水，气候与平原接近。"
     "树木为樱花木，地面散布落叶堆与花丛。熊猫只在这一类群系出现，是它与普通森林的主要区别。"),

    ("cotton_sakura_grove", "Cotton Sakura Grove", None, 0.6, 0.4, True, "主世界",
     [("monster", "蜘蛛 100、僵尸 95、僵尸村民 5、骷髅 100、苦力怕 100、史莱姆 100、末影人 10、女巫 5"),
      ("creature", "羊 12、猪 10、鸡 10、牛 8、狼 5、狐 16、熊猫 2"),
      ("ambient", "蝙蝠 10"),
      ("underground_water_creature", "发光鱿鱼 10")],
     "与 Blush Sakura Grove 并列为两片樱花林，温度、生物构成完全一致，"
     "差异在树的品种与整体配色——这一种偏白，对应「棉」的命名。"),

    ("carnelian_treeway", "Carnelian Treeway", None, 1.2, 0.9, True, "主世界",
     [("monster", "蜘蛛 100、僵尸 95、僵尸村民 5、骷髅 100、苦力怕 100、史莱姆 100、末影人 10、女巫 5"),
      ("creature", "羊 12、猪 10、鸡 10、牛 8、狼 5、狐 7"),
      ("ambient", "蝙蝠 10"),
      ("underground_water_creature", "发光鱿鱼 10")],
     "枫树林，温度 1.2、湿度 0.9，是四个主世界新群系里最温暖潮湿的一个。"
     "树冠呈橙红色，地面覆盖枫叶堆。这一种没有熊猫，狐的权重也比樱花林低。"),

    ("glacarian_taiga", "Glacarian Taiga", None, -0.7, 0.8, True, "主世界",
     [("monster", "蜘蛛 100、僵尸 95、僵尸村民 5、骷髅 100、苦力怕 100、史莱姆 100、末影人 10、女巫 5"),
      ("creature", "鸭 4、狼 8、狐 8"),
      ("ambient", "蝙蝠 10"),
      ("underground_water_creature", "发光鱿鱼 10")],
     "雪原针叶林，温度 -0.7，是全模组最冷的群系。降水量 0.8，地表有积雪。"
     "生物最少，只有鸭、狼与狐三种被动生物。积雪转化机制在这一带生效——部分方块在降雪时逐渐被雪覆盖。"),

    ("dark_amaranth_forest", "Dark Amaranth Forest", "苋菜林", 2.0, 0.0, False, "下界",
     [("monster", "末影人 1"),
      ("creature", "炽足兽 60")],
     "唯一的下界群系。温度 2.0、无降水，判定为下界环境。"
     "地表是苋菜菌岩，生长苋菜菌柄与菌核，是模组里第三种菌类木材的来源。"
     "生物构成接近原版下界森林——只有末影人与炽足兽。"),
]

# 结构
STRUCTURE = {
    "id": "dark_forest_witch_hut",
    "name": "黑森林女巫小屋",
    "spacing": 32,
    "separation": 8,
    "salt": 14357620,
    "biome_tag": "#promenade:has_structure/dark_forest_witch_huts",
    "desc": "只在黑森林群系生成的女巫小屋。采用拼图式结构生成，内部有多个房间分区，"
            "箱子中放置女巫相关的战利品。生成间距 32 区块、分离距离 8，"
            "在同类结构中属于较密的分布。",
}

# 地物
FEATURES = [
    ("blueberry_bush", "蓝莓丛", "可采集的浆果灌木，结果后可收获蓝莓。"),
    ("coiled_vines", "缠绕藤蔓", "垂挂生长的藤蔓，带有卷曲形态。"),
    ("cute_little_rock", "小型岩石", "成簇生成的小石块，用于填充地表。"),
    ("dark_amaranth_forest_vegetation", "苋菜林植被", "苋菜林的整体植被配置。"),
    ("fallen_fulvous_maple_leaves", "黄色枫叶堆", "黄色枫木的落叶层。"),
    ("fallen_mikado_maple_leaves", "深黄枫叶堆", "深黄枫木的落叶层。"),
    ("fallen_vermilion_maple_leaves", "朱红枫叶堆", "朱红枫木的落叶层。"),
    ("water_pool_gravel_decorated", "砾石水潭", "带砾石装饰的小型水潭。"),
]


def biome_html(b):
    bid, en, zh, temp, downfall, precip, dim, spawns, desc = b
    title = f"{en}（{zh}）" if zh else en
    rows = "".join(
        f"<tr><td>{cat}</td><td>{val}</td></tr>" for cat, val in spawns
    )
    return (
        f"<p>{title} 是 Promenade 新增的生物群系，位于{dim}。</p>"
        "<table><thead><tr><th>属性</th><th>数值</th></tr></thead><tbody>"
        f"<tr><td>维度</td><td>{dim}</td></tr>"
        f"<tr><td>温度</td><td>{temp}</td></tr>"
        f"<tr><td>湿度</td><td>{downfall}</td></tr>"
        f"<tr><td>降水</td><td>{'有' if precip else '无'}</td></tr>"
        "</tbody></table>"
        f"<p><strong>特点</strong>：{desc}</p>"
        "<p><strong>生物生成</strong>（括号内为权重）：</p>"
        f"<table><thead><tr><th>类别</th><th>生物</th></tr></thead><tbody>{rows}</tbody></table>"
        "<p>生物权重决定生成比例，数值越大的生物出现越频繁。</p>"
    )


def main() -> int:
    rows = []

    # 5 个群系
    for b in BIOMES:
        bid, en, zh = b[0], b[1], b[2]
        rows.append({
            "id": f"biome_{bid}",
            "name": en,
            "ename": "",
            "regname": f"promenade:{bid}",
            "category": "生物群系",
            "type": "自然生成",
            "maxstack": 64,
            "remark": (
                "Promenade 新增自然生成页：温湿度、降水、维度与生物生成权重"
                "取自 data/promenade/worldgen/biome 下的定义，名称取自 lang/en_us.json。"
                f"{tail()}"
            ),
            "html": biome_html(b),
            "icon32": "",
        })

    # 结构
    s = STRUCTURE
    rows.append({
        "id": f"structure_{s['id']}",
        "name": s["name"],
        "ename": "",
        "regname": f"promenade:{s['id']}",
        "category": "结构",
        "type": "自然生成",
        "maxstack": 64,
        "remark": (
            "Promenade 新增自然生成页：结构类型、生成间距与群系标签"
            "取自 data/promenade/worldgen/structure 与 structure_set。"
            f"{tail()}"
        ),
        "html": (
            f"<p>{s['name']}是 Promenade 新增的唯一结构，只在黑森林群系生成。</p>"
            "<table><thead><tr><th>属性</th><th>数值</th></tr></thead><tbody>"
            "<tr><td>结构类型</td><td>jigsaw（拼图）</td></tr>"
            "<tr><td>拼图尺寸</td><td>1</td></tr>"
            f"<tr><td>生成间距</td><td>{s['spacing']} 区块</td></tr>"
            f"<tr><td>分离距离</td><td>{s['separation']}</td></tr>"
            f"<tr><td>生成群系</td><td>{s['biome_tag']}</td></tr>"
            "<tr><td>地形适配</td><td>beard_thin</td></tr>"
            "</tbody></table>"
            f"<p><strong>说明</strong>：{s['desc']}</p>"
        ),
        "icon32": "",
    })

    # 地物汇总
    feat_rows = "".join(
        f"<tr><td>{en}</td><td>{zh}</td><td>{desc}</td></tr>"
        for _, zh, desc in FEATURES
        for en in [dict((z, e) for e, z, _ in FEATURES).get(zh, "")]
    )
    # 更直接地构造
    feat_rows = ""
    for fid, zh, desc in FEATURES:
        feat_rows += f"<tr><td>{fid}</td><td>{zh}</td><td>{desc}</td></tr>"

    rows.append({
        "id": "features",
        "name": "地物与植被",
        "ename": "",
        "regname": "",
        "category": "地物",
        "type": "自然生成",
        "maxstack": 64,
        "remark": (
            "Promenade 新增自然生成页：地物清单与作用取自 "
            "data/promenade/worldgen/feature 下的定义，名称取自 lang/en_us.json。"
            f"{tail()}"
        ),
        "html": (
            "<p>模组新增的地物，用于填充各群系的地表。</p>"
            "<table><thead><tr><th>id</th><th>名称</th><th>用途</th></tr></thead><tbody>"
            f"{feat_rows}</tbody></table>"
            "<p><strong>落叶堆</strong>：三种枫叶堆分别对应枫木的三个品种，"
            "铺在地面形成落叶层，可用铲子处理。原版各树种也各有一种落叶堆。</p>"
            "<p><strong>蓝莓丛</strong>：可采集的浆果灌木，成熟后可收获。</p>"
            "<p><strong>小型岩石</strong>：成簇生成的小石块，仅作装饰。</p>"
        ),
        "icon32": "",
    })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    for r in rows:
        print(f"  {r['category']:<8} {r['name']:<26} {len(r['html']):>5} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
