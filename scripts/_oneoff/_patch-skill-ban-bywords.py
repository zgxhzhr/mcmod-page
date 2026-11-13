#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""修正 ban 判据：以字数为准，标题数只是辅助。

原写法（§6.2.2.31.1 + §6.2.2.35 两处）：
    「字数 < 600 且 标题总数 ≤ 3 → 加 ban」
把标题数当成了必要条件，于是 373 字、4 个标题的页面被判成「不该 ban」。
实测反馈：**373 字的页面，4 个标题的目录照样没有导航价值** —— 目录的意义是「跳着查」，
几百字没有跳着查的需求，4 行目录纯占位。

新判据：
    字数 < 600                    → 加 ban（唯一条件，不看标题数）
    600 ≤ 字数 < 900 且 标题 ≤ 3   → 也可加（目录两三行同样没价值）
    其余                          → 不加，让目录显示
"""
from pathlib import Path

R02 = Path(r"E:\Mod\模板与工具\发布\mcmod-page\rules\02-模组页.md")
R03 = Path(r"E:\Mod\模板与工具\发布\mcmod-page\rules\03-语体与去AI味.md")

NEW_311 = '''#### 判据：以字数为准，标题数只是辅助

```
字数 < 600                    → 加 [ban:title_menu]（唯一条件，不看标题数）
600 ≤ 字数 < 900 且 标题 ≤ 3   → 也可以加（目录两三行同样没导航价值）
其余                          → 不加，让目录显示
```

**为什么字数优先**：目录的作用是「跳着查」。几百字的页面读者一屏就能扫完，
4 个标题的目录也就是 4 行，占地方不帮忙。

⚠️ **不要把「标题数」当必要条件**。曾经的写法是「字数 < 600 **且** 标题 ≤ 3」，
结果 373 字、4 个 h2 的页面被判成不该 ban —— 字数才是主因。

**怎么加**：

```html
<p>[ban:title_menu]</p>      ← 独占一个 <p>，放正文最前
<p>[h1=概述]</p>
```

**不是删标题**——标题还留着分节，只是关掉右侧目录。
'''

def replace_block(path: Path, start_marker: str, end_marker: str, new: str) -> bool:
    t = path.read_text(encoding="utf-8")
    i = t.find(start_marker)
    if i < 0:
        print(f"  ✗ {path.name}: 找不到起点 {start_marker[:30]}")
        return False
    j = t.find(end_marker, i)
    if j < 0:
        print(f"  ✗ {path.name}: 找不到终点")
        return False
    t = t[:i] + new + t[j + len(end_marker):]
    path.write_text(t, encoding="utf-8")
    print(f"  ✓ {path.name}")
    return True


def main() -> int:
    print("修正 ban 判据：")

    # ① 02 里的 §6.2.2.31.1 判据段
    replace_block(
        R02,
        "#### 判据\n\n```\n字数 < 600  且  h1 ≤ 3",
        "**怎么加**：\n\n```html\n<p>[ban:title_menu]</p>      ← 独占一个 <p>，放正文最前\n<p>[h1=概述]</p>\n```",
        NEW_311.rstrip("\n").replace("#### 判据：以字数为准，标题数只是辅助", "#### 判据：以字数为准，标题数只是辅助"),
    )

    # ② 02 里 §6.2.2.35 末尾的重述
    t = R02.read_text(encoding="utf-8")
    old = """```
字数 < 600 且 标题总数 ≤ 3   → 加 ban
否则                        → 不加，让目录显示
```"""
    new = """```
字数 < 600                    → 加 ban（不看标题数）
600 ≤ 字数 < 900 且 标题 ≤ 3   → 也可加
其余                          → 不加
```"""
    if old in t:
        t = t.replace(old, new, 1)
        R02.write_text(t, encoding="utf-8")
        print("  ✓ 02 §6.2.2.35 的重述已同步")

    # ③ 03 里如果也抄了旧判据
    t3 = R03.read_text(encoding="utf-8")
    if "字数 < 600 且 标题总数 ≤ 3" in t3:
        t3 = t3.replace("字数 < 600 且 标题总数 ≤ 3", "字数 < 600（不看标题数）")
        R03.write_text(t3, encoding="utf-8")
        print("  ✓ 03 同步")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
