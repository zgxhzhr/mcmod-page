#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refresh-sha.py —— 规则块改动后，刷新历史交付 README 里的指纹声明。

用法：
    python refresh-sha.py [交付根目录]

默认交付根 = E:\\Mod\\百科-语料\\交付（可用环境变量 MCMOD_DELIVERY_ROOT 覆盖）。
只改 `rules/xx.md §N [xxxxxxxx]` 里方括号中的 8 位指纹，不动条款号与其它内容。
"""
import hashlib
import os
import re
import sys
from pathlib import Path

RULES = Path(__file__).resolve().parent.parent / "rules"
ROOT = Path(sys.argv[1] if len(sys.argv) > 1
            else os.environ.get("MCMOD_DELIVERY_ROOT", r"E:\Mod\百科-语料\交付"))

PAT = re.compile(r"rules/([\w\-]+\.md) (§[\d.]+)\s*\[([0-9a-f]{8})\]")


def main() -> int:
    shas = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:8]
            for p in RULES.glob("*.md")}
    if not RULES.exists():
        print(f"✗ 规则目录不存在：{RULES}")
        return 1
    changed = total = 0
    for readme in sorted(ROOT.glob("*/README.md")):
        total += 1
        text = readme.read_text(encoding="utf-8")
        stale = [(m.group(1), m.group(3), shas.get(m.group(1), m.group(3)))
                 for m in PAT.finditer(text) if shas.get(m.group(1)) not in (None, m.group(3))]
        if not stale:
            continue
        new = PAT.sub(lambda m: f"rules/{m.group(1)} {m.group(2)} "
                                f"[{shas.get(m.group(1), m.group(3))}]", text)
        readme.write_text(new, encoding="utf-8")
        changed += 1
        pairs = "、".join(f"{n} {o}→{v}" for n, o, v in stale)
        print(f"  刷新 {readme.parent.name}: {pairs}")
    print(f"✓ 扫描 {total} 份 README，刷新 {changed} 份")
    return 0


if __name__ == "__main__":
    sys.exit(main())
