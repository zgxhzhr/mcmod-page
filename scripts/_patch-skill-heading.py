#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 skill 里「长介绍用 h2」这条规则——区分模组页与资料页。"""
from pathlib import Path

SKILL = Path(r"E:\Mod\模板与工具\发布\mcmod-page\SKILL.md")


def main():
    t = SKILL.read_text(encoding="utf-8")
    anchor = "实例（Simple Wooden Pipes 15375）："
    if anchor not in t:
        print("找不到锚点")
        return

    add = '''**⚠️ 这条只适用于「模组页」，资料页不适用。**

模组页上已经有原文的 `[h1=概述]` / `[h1=画廊]` 作父级，所以自己补充的用 `[h2=]` 是对的。
**资料页（物品/方块、生物/实体、游戏设定、自然生成……）没有原文 h1**，
标题必须从 `[h1=]` 起——用 `[h2=]` 会被判「文中有跨级标题」：

```
✗ 资料页直接用 h2
  <p>[h2=战利品方块与对应的表]</p>     ← 前面没有 h1，跨级

✓ 资料页从 h1 起
  <p>[h1=战利品方块与对应的表]</p>
```

判断口诀：**看这个页面本身有没有原文的 `[h1=]`**。
有（模组页、教程页）→ 用 h2；没有（资料页）→ 从 h1 起。

'''
    t = t.replace(anchor, add + anchor, 1)
    SKILL.write_text(t, encoding="utf-8")
    print("✓ skill 已补「资料页不能用 h2」")


if __name__ == "__main__":
    main()
