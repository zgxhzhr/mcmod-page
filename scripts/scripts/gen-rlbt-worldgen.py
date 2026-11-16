#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RLBT（classId 28249）自然生成页 —— 8 页，按结构类别拆分。

数据来源：
  structure_set     → 生成间距
  template_pool     → 结构配置与 nbt 模板的映射
  structures/*.nbt  → 尺寸、实心方块数、刷怪笼与箱子数量、主要建材
  解析结果缓存在 rlbt-structures.json

不建页：new_1~new_11（开发中的测试内容）。
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
DATA = json.loads((BASE / "rlbt-structures.json").read_text(encoding="utf-8"))
OUT = BASE / "rlbt-自然生成-28249.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def fmt(n: int) -> str:
    return f"{n:,}"


def table(names, desc_map=None):
    desc_map = desc_map or {}
    rows = []
    for n in names:
        d = DATA.get(n, {})
        if not d:
            rows.append(f"<tr><td>{n}</td><td>—</td><td>—</td><td>{desc_map.get(n, '')}</td></tr>")
            continue
        sz = "×".join(str(x) for x in d["size"])
        rows.append(f"<tr><td>{n}</td><td>{sz}</td><td>{fmt(d['blocks_solid'])}</td>"
                    f"<td>{d['spacing'] or '—'}</td><td>{desc_map.get(n, '')}</td></tr>")
    return ("<table><thead><tr><th>结构</th><th>尺寸（长×宽×高）</th><th>实心方块</th>"
            "<th>生成间距</th><th>说明</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def spawners(names):
    """刷怪笼与箱子数量表。"""
    rows = []
    for n in names:
        d = DATA.get(n, {})
        if not d:
            continue
        w = d.get("watch", {})
        rows.append(f"<tr><td>{n}</td><td>{w.get('刷怪笼', 0)}</td><td>{w.get('箱子', 0)}</td>"
                    f"<td>{d['entities']}</td></tr>")
    return ("<table><thead><tr><th>结构</th><th>刷怪笼</th><th>箱子</th><th>预设实体</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def materials(names):
    """主要建材，取每个结构方块数前 4 的方块。"""
    lines = []
    for n in names:
        d = DATA.get(n, {})
        if not d:
            continue
        mats = "、".join(f"{k}（{fmt(v)}）" for k, v in d["materials"][:4])
        lines.append(f"<li><p>{n}：{mats}</p></li>")
    if not lines:
        return ""
    return '<p><strong>主要建材</strong>：</p><ul class="list-paddingleft-2">' + "".join(lines) + "</ul>"


TOWERS = [f"battle_tower_{i}" for i in range(1, 7)]

PAGES = [
    {
        "id": "battle_towers",
        "name": "战斗高塔",
        "html": (
            "<p>战斗高塔是模组的主体，共六座，全部生成在主世界地表。前四座为普通塔，"
            "后两座为 Boss 塔，尺寸与内部配置都有明显差异。</p>"
            + table(TOWERS, {"battle_tower_1": "普通塔", "battle_tower_2": "普通塔",
                             "battle_tower_3": "普通塔", "battle_tower_4": "普通塔",
                             "battle_tower_5": "Boss 塔", "battle_tower_6": "Boss 塔"})
            + "<p><strong>两种规格</strong>：普通塔为 14×64×15，实心方块约 3,200 个；"
              "Boss 塔为 16×77×16，比普通塔高 13 格、宽 2 格，实心方块约 4,150 个。"
              "编号越高尺寸越大，五、六号是同一规格的两座 Boss 塔。</p>"
            + "<p><strong>内部配置</strong>：刷怪笼与箱子是塔的两类核心方块，决定了战斗强度与收益。</p>"
            + spawners(TOWERS)
            + "<p>普通塔每座有 16 个刷怪笼，Boss 塔则有 18 个。箱子上，普通塔为 14 到 16 个，"
              "Boss 塔固定 20 个。刷怪笼密度是塔内战斗强度的直接来源——玩家每上升一层都要面对新的刷怪点。</p>"
            + materials(TOWERS)
            + "<p><strong>建材特征</strong>：六座塔都用苔石圆石、苔石砖、圆石与平滑石台阶堆砌，"
              "风格统一，呈残破的石造塔外观。</p>"
            + "<p><strong>模板映射</strong>：battle_tower_1 用 rlcraft_battle_tower_1，"
              "battle_tower_2 用 rlcraft_battle_tower_3，battle_tower_3 用 rlcraft_battle_tower_2，"
              "battle_tower_4 用 rlcraft_battle_tower_4，五、六号分别为 rlcraft_battle_tower_boss_1 与 boss_2。"
              "模板编号与塔编号并非一一对应。</p>"
            + "<p><strong>生成频率</strong>：间距依次为 40、80、120、200、240、350。"
              "编号越高越罕见，一级塔约每 40 区块出现一座，六级塔要 350 区块才有一座。</p>"
            + "<p><strong>守卫</strong>：塔内驻守 Tower Golem，生命值 200、护甲 22，索敌范围 64 格。"
              "属性见「游戏设定」中的 Tower Golem 属性页。</p>"
        ),
    },
    {
        "id": "megatower",
        "name": "巨型塔",
        "html": (
            "<p>巨型塔（megatower）是尺度最大的一座单体塔，生成间距 100。</p>"
            + table(["megatower"], {"megatower": "尺度最大的塔"})
            + "<p><strong>规模</strong>：60×55×60 的占地与高度，实心方块近五万个，"
              "是普通战斗塔的十五倍。体积上它更接近一座建筑群而非单塔。</p>"
            + "<p><strong>内部配置</strong>：61 个刷怪笼、26 个箱子，两项都远超常规塔。"
              "按体积平均，它的刷怪笼密度不算高，但因为基数大，实际遭遇战次数会明显更多。</p>"
            + spawners(["megatower"])
            + "<p><strong>预设实体</strong>：结构内自带 1 个实体，在生成时直接放置。</p>"
            + materials(["megatower"])
            + "<p><strong>方块种类</strong>：调色板包含 112 种方块，是全模组最丰富的一个结构，"
              "不同区域使用不同材质，而非单一风格的重复堆叠。</p>"
            + "<p><strong>地形适配</strong>：使用 beard_thin 适配，会在地表产生地形过渡，"
              "不像常规塔那样直接贴合地表。</p>"
        ),
    },
    {
        "id": "skycastle",
        "name": "天空城堡",
        "html": (
            "<p>天空城堡（skycastle）是悬浮在空中的大型结构，生成间距 80。</p>"
            + table(["skycastle"], {"skycastle": "空中结构"})
            + "<p><strong>规模与密度</strong>：占地 90×100×64，体积是巨型塔的两倍多，"
              "但实心方块只有约一万个——大量空间是空的，结构本身是悬空的平台与塔楼，"
              "不是实心建筑。</p>"
            + "<p><strong>内部配置</strong>：6 个刷怪笼、4 个箱子，密度远低于地面建筑。"
              "它的主要价值在地理位置而非战利品堆叠。</p>"
            + spawners(["skycastle"])
            + materials(["skycastle"])
            + "<p><strong>抵达方式</strong>：不贴地生成，需要玩家自行搭建通路或飞行才能到达。"
              "在生存前期基本无法进入。</p>"
        ),
    },
    {
        "id": "rlcraft_castles",
        "name": "RLCraft 城堡与要塞",
        "html": (
            "<p>以 rlcraft 命名的六个结构，来自 RLCraft 整合包的地表建筑。</p>"
            + table(["rlcraf_tcastle", "rlcraft_1", "rlcraft_2", "rlcraft_3", "rlcraft_5", "rlcraft_fortress"],
                    {"rlcraf_tcastle": "城堡", "rlcraft_fortress": "要塞",
                     "rlcraft_1": "小型建筑", "rlcraft_2": "小型建筑",
                     "rlcraft_3": "小型建筑", "rlcraft_5": "小型建筑"})
            + "<p><strong>规模差异</strong>：六个结构体量悬殊。要塞 64×45×64、约一万八千方块，"
              "城堡 35×55×35、约四千九百方块，而 rlcraft_1 只有 18×45×18、五百余方块，"
              "属于点缀用的小型建筑。</p>"
            + spawners(["rlcraf_tcastle", "rlcraft_1", "rlcraft_2", "rlcraft_3", "rlcraft_5", "rlcraft_fortress"])
            + "<p><strong>刷怪与战利品</strong>：这一组普遍没有刷怪笼，要塞与城堡也没有预设实体，"
              "属于探索型结构而非战斗型。箱子上，城堡有 14 个，要塞只有 1 个，"
              "rlcraft_1 与 rlcraft_5 完全没有箱子。</p>"
            + materials(["rlcraf_tcastle", "rlcraft_fortress"])
            + "<p><strong>命名说明</strong>：结构名 rlcraf_tcastle 少了一个 t，属拼写笔误，不影响功能。"
              "编号里缺 rlcraft_4，作者没有注册这一号。</p>"
        ),
    },
    {
        "id": "rlcraft_ruins",
        "name": "RLCraft 遗迹",
        "html": (
            "<p>五个遗迹类结构，规模小于城堡，通常由残垣与零散房间组成。</p>"
            + table(["ruins_r_lcraft_1", "ruins_r_lcraft_2", "ruins_r_lcraft_3",
                     "ruins_r_lcraft_4", "ruinsnew"], {"ruinsnew": "新增遗迹"})
            + "<p><strong>规模</strong>：从 5×8×5 到 48×32×44 不等。ruins_r_lcraft_3 是其中最大的一座，"
              "约四千四百方块；ruins_r_lcraft_4 最小，只有 50 个实心方块，几乎只剩地基。</p>"
            + spawners(["ruins_r_lcraft_1", "ruins_r_lcraft_2", "ruins_r_lcraft_3",
                        "ruins_r_lcraft_4", "ruinsnew"])
            + "<p><strong>内容</strong>：五个遗迹里只有 ruins_r_lcraft_3 有 2 个刷怪笼、"
              "ruins_r_lcraft_4 有 1 个，其余三个没有刷怪点也没有箱子。"
              "它们更像是地表的装饰性残迹，而非资源点。</p>"
            + "<p><strong>生成频率</strong>：间距在 80 到 100 之间，与城堡相当。"
              "由于数量多、体量小，跑图时最容易遇到的正是这一组。</p>"
        ),
    },
    {
        "id": "dragon_eggs",
        "name": "龙蛋结构",
        "html": (
            "<p>三种以龙蛋为主题的结构，是本模组相对独立的内容，不来自 RLCraft。</p>"
            + table(["firedragonegg", "icedragonegg", "lightdrgaonegg"],
                    {"firedragonegg": "火焰龙蛋", "icedragonegg": "冰霜龙蛋", "lightdrgaonegg": "光明龙蛋"})
            + "<p><strong>结构形态</strong>：三者高度都只有 5 格，占地 12 到 15 格见方，"
              "实心方块在 450 到 650 之间。它们是平铺在地表的小型祭坛式结构，"
              "中央放置一颗龙蛋，四周环绕装饰方块。</p>"
            + spawners(["firedragonegg", "icedragonegg", "lightdrgaonegg"])
            + "<p><strong>差异</strong>：只有冰霜龙蛋结构带 2 个箱子，火焰与光明两种没有。"
              "三者都没有刷怪笼与预设实体。</p>"
            + "<p><strong>命名说明</strong>：lightdrgaonegg 里的 drgaon 是 dragon 的拼写笔误，"
              "属作者笔误，不影响功能。</p>"
        ),
    },
    {
        "id": "other_buildings",
        "name": "其他建筑",
        "html": (
            "<p>七个零散的地表建筑，风格不统一，属于作者一并打包的内容。</p>"
            + table(["church", "home", "homesweethome", "article", "glass", "glassbottle", "tree"],
                    {"church": "教堂", "home": "小屋", "homesweethome": "小屋变体",
                     "article": "遗迹建筑", "glass": "玻璃结构", "glassbottle": "玻璃瓶建筑",
                     "tree": "大树"})
            + "<p><strong>大树</strong>：tree 的模板为 big_tree，65×80×65、一万七千余方块，"
              "是这一组里最大的一个，也是全模组体积第三的结构。</p>"
            + "<p><strong>教堂</strong>：50×64×50、约五千八百方块，带 4 个刷怪笼，"
              "是这一组里唯一有刷怪点的结构。</p>"
            + "<p><strong>小屋</strong>：home 只有 10×10×10、190 个方块，是全模组最小的结构之一；"
              "homesweethome 则有 25×14×45、四千二百余方块，带 6 个箱子与 6 个预设实体。</p>"
            + spawners(["church", "home", "homesweethome", "article", "glass", "glassbottle", "tree"])
            + "<p><strong>玻璃结构</strong>：glass 与 glassbottle 分别 16×32×16 与 10×14×10，"
              "体量小且不含刷怪笼与箱子，外观上是装饰性建筑。</p>"
            + "<p><strong>预设实体</strong>：homesweethome 带 6 个实体，"
              "意味着结构生成时就已放置生物，进入时需要先清理。</p>"
        ),
    },
    {
        "id": "stone_structures",
        "name": "石质结构",
        "html": (
            "<p>六个以石头为主体的小型结构。</p>"
            + table([f"stone_{i}" for i in range(1, 7)])
            + "<p><strong>规模</strong>：全部在 10 到 16 格见方、8 到 16 格高之间，"
              "实心方块从 112 到 499 不等。stone_1 最高（13×16×13），"
              "stone_4 最小（10×10×10、112 方块）。</p>"
            + spawners([f"stone_{i}" for i in range(1, 7)])
            + "<p><strong>内容</strong>：六个都没有刷怪笼、没有箱子、没有预设实体。"
              "它们是纯粹的景观方块堆，没有可交互内容。</p>"
            + "<p><strong>生成密度</strong>：六个的间距全部是 10，是模组内最密集的一组结构。"
              "按间距推算，每 10 区块就有一个候选点，实际跑图时几乎随处可见。</p>"
            + "<p><strong>作用</strong>：以极高的密度填充地表，让世界看起来不那么空旷。"
              "由于没有箱子与刷怪点，路过时可无视。</p>"
        ),
    },
]


def main() -> int:
    rows = []
    for pg in PAGES:
        rows.append({
            "id": pg["id"],
            "name": pg["name"],
            "ename": "",
            "regname": "",
            "category": "结构",
            "type": "自然生成",
            "maxstack": 64,
            "remark": (
                "RLBT - kimohapng 新增自然生成页：结构与生成间距取自 data/kimohpangs_bs/worldgen，"
                "尺寸、实心方块数、刷怪笼与箱子数量由 structures 下的 nbt 模板解析得出。"
                f"{tail()}"
            ),
            "html": pg["html"],
            "icon32": "",
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    for r in rows:
        print(f"  {r['name']:<20} 正文 {len(r['html']):>5} 字符  表 {r['html'].count('<table')} 张")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
