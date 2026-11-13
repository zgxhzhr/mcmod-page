#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""补上被 PowerShell 反引号搞坏的两步：04 的指路、路由表的两个任务行。"""
from pathlib import Path

ROOT = Path(r"E:\Mod\模板与工具\发布\mcmod-page")
R04 = ROOT / "rules" / "04-资料页与图标.md"
SKILL = ROOT / "SKILL.md"


def main() -> int:
    # ① 04 顶部的指路：02 → 09
    t = R04.read_text(encoding="utf-8")
    before = t
    t = t.replace("先读 `rules/02-模组页.md` 的 §6.10.1",
                  "先读 `rules/09-核实纪律.md` 的 §6.10.1")
    if t != before:
        R04.write_text(t, encoding="utf-8")
        print("✓ 04 指路改为 09")
    else:
        print("  04 无需改（可能已是 09）")

    # ② 路由表加两个任务行
    s = SKILL.read_text(encoding="utf-8")
    if "核实某个数值 / 机制的来源" in s:
        print("  路由表已含，跳过")
    else:
        anchor = "| **被退回后要再编辑** |"
        new = (
            "| **核实某个数值 / 机制的来源** | `rules/09-核实纪律.md` | — |\n"
            "| **模组有前置，要确认机制到底谁提供的** | `rules/09-核实纪律.md`（§6.10.2 连前置一起反编译） | — |\n"
            "| **被退回后要再编辑** |"
        )
        assert anchor in s, "找不到路由表插入点"
        s = s.replace(anchor, new, 1)
        SKILL.write_text(s, encoding="utf-8")
        print("✓ 路由表加了「核实来源」「有前置」两行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
