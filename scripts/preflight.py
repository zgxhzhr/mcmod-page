#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preflight.py —— 交付前的「总闸」：一次跑完所有检查，并强制声明读了哪些规则块。

为什么要有它
------------
过去的问题不是「不知道规则」，而是**没全读就开始写**，以及**写的时候多补了一句不需要的话**
（典型：把「挖掘等级为木级」写进每一件工具、把「由 X 和 Y 合成」写进每一条）。

这个脚本把两件事变成一次性动作：

1. **跑完所有能自动测的检查**（结构 / AI 味 / 字段 / 图标 / 重复率 / 多余描述模式）；
2. **核对交付说明里有没有「规则块阅读声明」**——没有就阻断。
   声明格式固定，逼着人先读再写：

       ## 规则块阅读声明
       - rules/03-语体与去AI味.md 全文
       - rules/04-资料页与图标.md 全文
       - rules/09-核实纪律.md §6.10.3
       - rules/06-分类与判定.md §6.5

用法
----
    python preflight.py 交付目录
    python preflight.py 交付目录 --type 资料页
    python preflight.py 交付目录 --no-declaration   # 跳过声明核对（仅调试）

退出码：0 全过；1 有阻断项。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable

# 多余描述的模式：这些句子几乎总是「补出来的」，不是读者需要的
REDUNDANT = [
    (r"挖掘等级(?:为|是)(?:木|石|铁|金)级", "挖掘等级：只有与同类不同（如镐是钻石级）才写，默认值不写"),
    (r"(?:由|用|把).{0,12}(?:和|加|与).{0,12}(?:合成|做出来|压成)", "合成材料：配方表/合成节已经写了，正文不必逐条重复"),
    (r"是(?:本模组|模组)添加的(?:食物|物品|方块)", "「模组添加的」是自明信息：资料页本来就只收模组内容"),
    (r"可以(?:随时|直接)(?:食用|使用|放置)", "「可以随时食用」这类口语化补语，删掉不影响信息"),
    (r"与本模组.{0,8}一致|沿用原版", "「沿用/一致」属于对比句式，除非差异本身重要"),
    # 只有「百科有对应图标」的属性才必须走 [icon:…]；攻击速度 / 耐久 / 挖掘速度没有图标，写数字是对的
    (r"(?:生命值|血量|饥饿值|饱食度|护甲值|盔甲值|护甲韧性|饱和度)\s*[:：]?\s*\d", "裸数字：生命/饥饿/护甲/韧性/饱和度必须走 [icon:…] 标签"),
    (r"https?://|github\.com|wiki|参考|出处|详见", "正文不写来源：链接/仓库/反编译路径只进 remark"),
]

# 每类交付必须读的规则块（预检会把这些列出来，要求声明里逐条出现）
REQUIRED_READS = {
    "资料页": ["rules/04-资料页与图标.md", "rules/03-语体与去AI味.md", "rules/09-核实纪律.md", "rules/01-语法与规范.md"],
    "模组页": ["rules/02-模组页.md", "rules/03-语体与去AI味.md", "rules/09-核实纪律.md"],
    "批量": ["rules/05-批量与合并综合.md", "rules/07-工具与交付.md", "rules/03-语体与去AI味.md"],
}


def run(script: str, *args: str) -> str:
    p = subprocess.run([PY, str(HERE / script), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def pick_json_files(d: Path) -> list[Path]:
    return sorted(p for p in d.glob("*.json") if not p.name.startswith("."))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--type", default="资料页", choices=list(REQUIRED_READS))
    ap.add_argument("--no-declaration", action="store_true")
    a = ap.parse_args()

    d = Path(a.dir)
    if not d.is_dir():
        print(f"目录不存在：{d}")
        return 1

    blocks: list[str] = []
    warns: list[str] = []
    infos: list[str] = []

    # ① 规则块阅读声明
    readme = next((d / n for n in ("README.md", "readme.md") if (d / n).exists()), None)
    if not a.no_declaration:
        if not readme:
            blocks.append("缺 README.md —— 无法核对规则块阅读声明")
        else:
            txt = readme.read_text(encoding="utf-8", errors="replace")
            if "规则块阅读声明" not in txt:
                blocks.append("README 里没有「## 规则块阅读声明」小节 —— 先读规则再写，读完把清单抄进来")
            else:
                need = REQUIRED_READS[a.type]
                miss = [r for r in need if r.split("/")[-1].split("-")[0] not in txt]
                if miss:
                    blocks.append("规则块阅读声明缺：" + "、".join(miss))
                else:
                    infos.append(f"规则块声明完整（{len(need)} 个必读块）")

    # ② 每个 json 跑 audit
    files = pick_json_files(d)
    if not files:
        blocks.append("目录里没有 JSON")
    for f in files:
        out = run("audit-delivery.py", str(f), "--json-only")
        m = re.search(r"结论：(PASS|FAIL)", out)
        verdict = m.group(1) if m else "?"
        b = re.search(r"阻断 (\d+) 条", out)
        w = re.search(r"提醒 (\d+) 条", out)
        infos.append(f"{f.name}: {verdict} 阻断 {b.group(1) if b else 0} 提醒 {w.group(1) if w else 0}")
        if verdict == "FAIL":
            for line in out.split("\n"):
                if line.strip().startswith("X ["):
                    blocks.append(f"{f.name} {line.strip()}")

    # ③ 正文的「多余描述」扫描
    for f in files:
        try:
            rows = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        for r in rows:
            html = r.get("html") or ""
            if not html:
                continue
            # 通用文本的职责就是承接「这批东西是什么、怎么来的」，不按多余描述判
            if str(r.get("category") or "").strip() == "{文本}":
                continue
            plain = re.sub(r"<[^>]+>", "", html)
            # 整句里已经有 [icon:…] 的，不算裸数字
            plain = re.sub(r"[^。；<]*\[icon:[^\]]*\][^。；]*[。；]?", "", plain)
            plain = re.sub(r"\[icon:[^\]]*\]", "", plain)
            for pat, why in REDUNDANT:
                if re.search(pat, plain):
                    warns.append(f"[{r.get('name') or r.get('id')}] 多余描述：{why}")

    # ④ 输出
    print("=" * 60)
    print(f"preflight · {d.name} · 类型 {a.type}")
    print("=" * 60)
    for s in infos:
        print(f"  · {s}")
    if warns:
        print("  ── 提醒 ──")
        for w in warns:
            print(f"  ! {w}")
    if blocks:
        print("  ── 阻断 ──")
        for b in blocks:
            print(f"  X {b}")
    print()
    print(f"改完之后重跑：python scripts/preflight.py \"{d}\" --type {a.type}")
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
