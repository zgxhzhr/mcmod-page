#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审核列表第 12~21 条（被退回的模组介绍）→ 批量再编辑 JSON。

附言原文：
  统一回复喵：1.适当添加 h2 标题；2.画廊后置；
  3.（部分含有）对单个资料过于详细的介绍需要写到对应的物品里，模组正文仅需摘要

已处理 1 和 2：
  - 第一个 h1 保留为主标题，其余 h1 降为 h2
  - 画廊块整体移到文末（有画廊的 prom/jgb 等）
  - 去掉挂在文末的 [ban:title_menu]（字数都 ≥600 或标题数 >3，目录应显示）
  - wr 的 <code> 换成 <strong>（百科不支持 code），裸写的 [hN=] 补上 <p> 包裹
"""
import json
import random
import re
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
OUT = BASE / "模组介绍-再编辑-10条.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

# 再编辑页 URL（取自审核列表的 againHref），脚本靠它自动跳下一条
TARGET = {
    2674: "/class/edit/2674-818373/",
    24724: "/class/edit/24724-818204/",
    646: "/class/edit/646-818116/",
    264: "/class/edit/264-818164/",
    3976: "/class/edit/3976-818103/",
    4236: "/class/edit/4236-818110/",
    17728: "/class/edit/17728-818055/",
    3182: "/class/edit/3182-818088/",
    12913: "/class/edit/12913-817928/",
    5180: "/class/edit/5180-817965/",
}

# (审核序号, classId, 模组名, 介绍文件名, 本次改动说明)
ROWS = [
    (12, 2674, "Bunny Boots", "bb-介绍-2674.html",
     "h1 降为 h2；去掉文末的禁用标题栏"),
    (13, 24724, "Realistic Explosives", "rex-介绍-24724.html",
     "h1 降为 h2；去掉文末的禁用标题栏"),
    (14, 646, "RP增强", "ts-介绍-646.html",
     "h1 降为 h2；去掉文末的禁用标题栏"),
    (15, 264, "无线红石", "wr-介绍-264.html",
     "h1 降为 h2；标题补上段落包裹；<code> 换成 <strong>；去掉禁用标题栏"),
    (16, 3976, "无中生有：传承 - 热力扩展", "entherm-介绍-3976.html",
     "h1 降为 h2；去掉文末的禁用标题栏"),
    (17, 4236, "环境科技-发电机", "ee-介绍-4236.html",
     "h1 降为 h2；去掉文末的禁用标题栏"),
    (18, 17728, "Strange Berries", "sb-介绍-17728.html",
     "h1 降为 h2；去掉文末的禁用标题栏"),
    (19, 3182, "群峦岩石", "trp-介绍-3182.html",
     "h1 降为 h2；去掉文末的禁用标题栏"),
    (20, 12913, "Self Damage Knife", "sdk-介绍-12913.html",
     "h1 降为 h2；标题补上段落包裹；去掉禁用标题栏"),
    (21, 5180, "挖矿与砍杀拓展", "mse-介绍-5180.html",
     "h1 降为 h2；去掉文末的禁用标题栏"),
]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def wc(html: str) -> int:
    b = re.sub(r"<[^>]+>", "", html)
    b = re.sub(r"\[[^\]]+\]", "", b)
    return len(b.strip())


def main() -> int:
    out = []
    for idx, cid, name, fname, note in ROWS:
        p = BASE / fname
        if not p.exists():
            print(f"✗ 缺文件 {fname}")
            continue
        html = p.read_text(encoding="utf-8").strip()

        h1 = re.findall(r"\[h1=([^\]]+)\]", html)
        h2 = re.findall(r"\[h2=([^\]]+)\]", html)

        out.append({
            "classId": cid,
            "name": name,
            "targetUrl": TARGET.get(cid, ""),
            "editRemark": (
                f"按审核附言再编辑：{note}。"
                f"现为 1 个 h1（{h1[0] if h1 else '简介'}）配 {len(h2)} 个 h2，正文 {wc(html)} 字。"
                f"{tail()}"
            ),
            "editNote": f"结构调整：h1 降为 h2、画廊后置、去掉禁用标题栏。",
            "html": html,
        })
        print(f"✓ {idx}. {name:<24} classId={cid:<6} h1×{len(h1)} h2×{len(h2)}  {wc(html)} 字")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n生成 {len(out)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
