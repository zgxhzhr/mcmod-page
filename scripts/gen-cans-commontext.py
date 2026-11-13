#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canned Food and Drinks（14363）通用文本方案。

29 条（22 罐装食品 + 7 果汁）里「合成」那句话完全相同：
    合成：罐子加原版食材，无序合成，摆位随意。   ×29

建一条通用文本承接「罐子怎么来 + 怎么装罐」这套共通机制，
29 条只留「是什么 + 数值 + 特殊效果」。

罐子本身（Food Can / Drinking Can）不引用——它们就是配方的载体，
自己的合成说明必须留在页面上。
"""
import json
import random
import re
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "cans-物品导入-14363.json"
OUT_ITEMS = BASE / "cans-物品导入-14363.json"
OUT_COMMON = BASE / "cans-通用文本-14363.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

# 每种成品对应的原版食材（取自 assets/cannedfoodanddrinks/recipes 下的配方）
SOURCE_FOOD = {
    "cannedapple": "苹果", "cannedbakedpotato": "烤土豆", "cannedbeetroot": "甜菜根",
    "cannedbeetrotsoup": "甜菜汤", "cannedbread": "面包", "cannedcake": "蛋糕",
    "cannedcarrot": "胡萝卜", "cannedchicken": "熟鸡肉", "cannedcod": "熟鳕鱼",
    "cannedenchantedgoldenapple": "附魔金苹果", "cannedgoldenapple": "金苹果",
    "cannedgoldencarrot": "金胡萝卜", "cannedmelon": "西瓜片",
    "cannedmushroomstew": "蘑菇煲", "cannedmutton": "熟羊肉",
    "cannedporkchop": "熟猪排", "cannedpotato": "土豆", "cannedpumpkinpie": "南瓜派",
    "cannedrabbit": "熟兔肉", "cannedrabbitstew": "兔肉煲",
    "cannedsalmon": "熟鲑鱼", "cannedsteak": "牛排",
    "applejuice": "苹果", "beetrootjuice": "甜菜根", "carrotjuice": "胡萝卜",
    "melonjuice": "西瓜片", "goldencarrotjuice": "金胡萝卜",
    "goldenapplejuice": "金苹果", "enchantedgoldenapplejuice": "附魔金苹果",
}

COMMON_HTML = (
    "<p>罐装食品是把原版食物装进食品罐做成的同一份食物，饥饿值与饱和度沿用原版数值；"
    "果汁是把食物装进饮料罐榨成的饮料，大多不恢复饥饿值。</p>"
    "<p>两者都靠「罐子 + 原版食材」在合成台做出来：无序合成，摆位随意，一次产出一件。</p>"
    "<p><strong>罐子</strong>：食品罐用八颗铁粒围成一圈合成，饮料罐用六颗铁粒分两行合成，"
    "两者都是一次产出八个。</p>"
    "<p><strong>消耗</strong>：罐子在合成时被消耗掉，装配成品不退还。</p>"
    "<p><strong>数值来历</strong>：罐装食品的饥饿值与饱和度与原版食物一致；"
    "金胡萝卜汁是唯一恢复饥饿值的果汁，其余果汁均为 0。</p>"
    "<p><strong>药水效果</strong>：只有金苹果与附魔金苹果的四件成品"
    "（两种罐装、两种果汁）在食用后会附加状态效果，其余只回饥饿值。</p>"
)


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    # 通用文本
    common = [{
        "id": "common_canned",
        "name": "罐装食品与果汁",
        "ename": "Canned Food and Drinks",
        "regname": "",
        "category": "{文本}",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Canned Food and Drinks 通用文本：本条不针对具体物品，"
            "用于承接罐装食品与果汁的共通合成说明，供各物品页在附言中引用。"
            "罐子配方取自 assets/cannedfoodanddrinks/recipes 下的 can1、can2 两个 json。"
            f"{tail()}"
        ),
        "html": COMMON_HTML,
        "icon32": "",
        "icon128": "",
    }]
    OUT_COMMON.write_text(json.dumps(common, ensure_ascii=False, indent=2), encoding="utf-8")

    # 29 条去掉合成句
    changed = 0
    for r in rows:
        if r["category"] == "罐子":
            # 罐子保留自己的合成说明
            r["remark"] = r["remark"].replace(
                "配方取自 assets/recipes 下的 json。",
                "配方取自 assets/recipes 下的 can1 / can2。",
            )
            continue

        # 删掉模板首句——「X 是 Canned Food and Drinks 添加的罐装食品…」这句
        # 结构与事实都由通用文本承担，各条只留数据
        r["html"] = re.sub(
            r"<p>[^<]*是 Canned Food and Drinks 添加的(罐装食品|果汁)，[^<]*。</p>",
            "", r["html"], count=1,
        )
        # 删掉「合成」那一段
        r["html"] = re.sub(r"<p><strong>合成</strong>：罐子加原版食材，无序合成，摆位随意。</p>", "", r["html"])
        # 果汁的「不恢复饥饿值」是功能信息（§6.4 要求正文必须写功能），
        # 虽然几条相同也不能省——省了页面就只剩一句「是什么」
        # 只把措辞改成更明确的「喝了没用」表述
        r["html"] = r["html"].replace(
            "<p><strong>恢复</strong>：不恢复饥饿值与饱和度。</p>",
            "<p><strong>饮用效果</strong>：不恢复饥饿值与饱和度，也没有额外状态效果。</p>",
        )
        # 若干成品的数值完全相同（烤土豆 / 面包 / 鳕鱼 / 兔肉都是 5 饿 6.0 饱和），
        # 只留数值会让正文一模一样，补一句来源食物区分
        src = SOURCE_FOOD.get(r["id"])
        if src:
            r["html"] = f"<p>把原版的{src}装罐做成。</p>" + r["html"]

        r["remark"] = (
            r["remark"].replace(
                "配方取自 assets/recipes 下的 json。",
                "合成方式与罐子来源需引用通用文本「罐装食品与果汁」。",
            )
        )
        changed += 1

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"通用文本 1 条 → {OUT_COMMON.name}  ({OUT_COMMON.stat().st_size/1024:.1f} KB)")
    print(f"物品页 {len(rows)} 条 → {OUT_ITEMS.name}  ({OUT_ITEMS.stat().st_size/1024:.1f} KB)")
    print(f"  改写 {changed} 条（罐子 2 条不动）\n")
    print("  正文长度变化：")
    for r in rows[:4]:
        print(f"    {r['name']:<28}{len(r['html']):>4} 字符")
    print(f"\n  引用检查: {sum(1 for r in rows if '引用通用文本' in r['remark'])}/{len(rows)} 条引用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
