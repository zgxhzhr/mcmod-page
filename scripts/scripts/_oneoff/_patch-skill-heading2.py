#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 skill 里的标题层级规则：不只资料页，模组页没有原文 h1 时也不能用 h2。"""
from pathlib import Path

SKILL = Path(r"E:\Mod\模板与工具\发布\mcmod-page\SKILL.md")


def main():
    t = SKILL.read_text(encoding="utf-8")
    anchor = "判断口诀：**看这个页面本身有没有原文的 `[h1=]`**。"
    if anchor not in t:
        print("找不到锚点")
        return

    add = '''判断口诀：**看这个页面本身有没有原文的 `[h1=]`**。

⚠️ **这条对模组页也适用**。有些模组的原介绍只给了图片和一段文字，**一个标题都没有**
（例：Exline's Awnings 28508 的原文就是 `<p><img>文字</p>` + 一个图片表格）。
这时候加 `[h2=内容]` 一样会跨级——必须用 `[h1=内容]`，或者干脆不加标题。

三种情况的实际处理：

| 原文标题情况 | 自己补充时用 | 例子 |
|---|---|---|
| 有 `[h1=概述]` / `[h1=画廊]` | `[h2=]` | Simple Wooden Pipes 15375、Factory Blocks 20843 |
| **没有任何标题** | `[h1=]`，或者不加标题 | Exline's Awnings 28508 |
| 资料页（天生无 h1） | `[h1=]` | Crafting Dead 战利品表 |

**提交前跑检查器**：

```powershell
python E:\\Mod\\模板与工具\\发布\\mcmod-page\\scripts\\check-page-structure.py 草稿.html
```

它检查五项：跨级标题、HTML `<h2>` 误用、百科不支持的标签、标签闭合平衡、
`[ban:title_menu]` 与标题的搭配。

'''
    t = t.replace(anchor, add, 1)
    SKILL.write_text(t, encoding="utf-8")
    print("✓ skill 已修正标题规则 + 指向检查器")


if __name__ == "__main__":
    main()
