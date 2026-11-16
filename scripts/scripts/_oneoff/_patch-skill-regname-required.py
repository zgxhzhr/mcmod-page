#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「注册名与原名必填」写进 skill，并修掉原有的自相矛盾。"""
from pathlib import Path

SKILL = Path(r"E:\Mod\模板与工具\发布\mcmod-page\SKILL.md")

NEW = '''#### 注册名（regname）与原名（ename）都是必填项

**踩过的坑（两次）**：

1. BUFF/DEBUFF 那批 22 条全部被退回，理由「没有注册名」——当时以为效果没有物品 id，
   其实效果同样有注册表 id。
2. 自然生成那批 8 条被退回，理由「需要补充注册名/原名」——结构同样有注册表 id，
   当时整批 `regname` 与 `ename` 都留空了。

#### regname 填什么

| 资料类型 | 注册名填什么 | 例 |
|---|---|---|
| 物品 / 方块 | 物品注册表 id | `lastsongofelysian:core_of_fire` |
| BUFF / DEBUFF | 效果注册表 id | `lastsongofelysian:red_ink` |
| 生物 / 实体 | 实体类型 id | `lastsongofelysian:elysian_hero_npc` |
| 世界 / 维度 | 维度 id | `lastsongofelysian:elysian_realm` |
| **自然生成 / 结构** | **结构 id**（`data/<ns>/worldgen/structure/*.json` 的文件名）| `minecraft:village_plains` |
| 绑定热键 | **留空**（本地化 key 不是注册名）| — |

**自然生成页的注册名从哪找**：

```
data/<namespace>/worldgen/structure/<结构名>.json   → regname = namespace:结构名
```

只有结构定义文件才算。以下两类不是结构，别硬填成结构 id：

- 模组只替换了模板（如掠夺者前哨站的 25 个 nbt），结构本身还是原版的 → 填原版 id
- 模板池（`data/<ns>/worldgen/template_pool/...`）→ 填模板池路径，如 `minecraft:village/common`

#### ename 填什么

| name 是什么语言 | ename |
|---|---|
| **中文**（模组有 zh_cn） | **必填英文名** |
| **英文**（模组无中文，name 本身就是英文） | 可留空 |

**关键**：`name` 是中文时 `ename` 不能空——这正是 15261 被退回的直接原因：
八条页面的 name 都是「平原村庄」这类中文，ename 全空，审核要的就是那一列英文原名。

原版结构没有自定义英文名时，用结构 id 转标题格式并在括号里注明变体：

```
minecraft:village_plains   → Village (Plains)
minecraft:village_desert   → Village (Desert)
minecraft:pillager_outpost → Pillager Outpost
```

#### 唯一例外：抽象资料与通用文本

这两类是**虚拟资料**，游戏里不存在，所以 `regname` 与图标都必须留空（见 §6.1.11）。
除此之外的每一条真实资料，两个字段都要有值。

#### 自检

```python
# regname 为空 → 必退
[r["name"] for r in data if not r.get("regname")]
```

**要求**：

- 一律用 **ASCII**（别把中文写进 regname，如 `signet_空梦` 是错的，应 `signet_reverie`）；
- 生成数据后跑一次自检，`regname` 为空的条目必须清零；
- 忘了填 → 整批退回重来，比补一次自检贵得多。

'''


def main():
    t = SKILL.read_text(encoding="utf-8")
    if "注册名（regname）与原名（ename）都是必填项" in t:
        print("已存在，跳过")
        return

    # 替换旧的那一节（从标题到「忘了填 → 整批退回重来」那句结尾）
    start = t.find("#### 注册名（regname）任何资料类型都不能空")
    if start < 0:
        print("找不到旧节")
        return
    end_marker = "- 忘了填 → 整批退回重来，比补一次自检贵得多。"
    end = t.find(end_marker, start)
    if end < 0:
        print("找不到旧节结尾")
        return
    end += len(end_marker)
    t = t[:start] + NEW.rstrip() + t[end:]
    SKILL.write_text(t, encoding="utf-8")
    print("✓ 已替换为「注册名与原名都是必填项」")


if __name__ == "__main__":
    main()
