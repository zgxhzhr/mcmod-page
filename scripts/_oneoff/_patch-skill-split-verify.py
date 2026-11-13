#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""把 §6.10 / §6.10.1 搬到独立的 rules/09-核实纪律.md，并新增 §6.10.2（连前置一起反编译）。

理由：这两节是**通用核实纪律**，跟「模组页」没关系，塞在 02 里路由也不顺。
搬到 09 后，路由表可以写「写任何页面都要读 09」。

新增 §6.10.2 来自实测：模组的核心机制常在依赖里。
怪物娘扩展的驯养/好感度体系全在 NFF: Girls 本体，只反扩展会得出
「本模组没写这套逻辑」的错误结论。
"""
from pathlib import Path

ROOT = Path(r"E:\Mod\模板与工具\发布\mcmod-page")
R02 = ROOT / "rules" / "02-模组页.md"
R09 = ROOT / "rules" / "09-核实纪律.md"
SKILL = ROOT / "SKILL.md"

HEADER = '''# 核实纪律：代码、前置与二次核验

> 规则块 `09-核实纪律.md`，属于 `mcmod-page` 技能。
> **写任何页面之前都要读本文件**——只要正文里出现数字、机制、获取方式，就适用。
> §编号与 SKILL.md 一致，可按编号交叉引用。

---

'''

NEW_6102 = '''

### 6.10.2 有前置就一起反编译

#### 为什么

模组的核心机制**经常不在它自己的 jar 里**。

| 情况 | 机制实际在哪 |
|---|---|
| 附属模组 | 前置本体（好感度/驯养/属性系统都在主模组）|
| 生物/方块扩展 | 前置本体定义了实体与注册表 |
| 兼容联动 | 被联动的那个模组提供接口 |

**只反扩展，会得出「本模组没有实现这套逻辑」的错误结论**，
或者把前置提供的能力写成「本模组提供」。

#### 步骤

**① 读依赖声明，拿到 modId 与版本范围**

```
Forge / NeoForge : META-INF/mods.toml
                   [[dependencies.<modid>]] 里的 modId / versionRange / mandatory
Fabric           : fabric.mod.json
                   depends / recommends
```

**② 按 modId 找下载（Modrinth 优先）**

```powershell
# Modrinth：开放 API，直链无防盗链
Invoke-RestMethod "https://api.modrinth.com/v2/project/<slug>/version"
# 取 [0].files[0].url
```

```
CurseForge：有防盗链，需要代理
  页面  https://www.curseforge.com/minecraft/mc-mods/<slug>/files
  直链  https://mediafilez.forgecdn.net/files/<id//1000>/<id%1000>/<filename>
  或查  https://api.cfwidget.com/minecraft/mc-mods/<slug>
```

**③ 版本必须对得上**

前置的 MC 版本与 loader 要和模组本身一致（看 `mods.toml` 的 `versionRange`）。
不匹配的前置反出来是另一套代码，结论照样错。

**④ 一起解包，同级目录，跨目录检索**

```
jar-analyze/<模组>/
jar-analyze/<模组>-前置1/
jar-analyze/<模组>-前置2/

# 检索时两个目录一起搜
Get-ChildItem <模组>*,<前置>* -Recurse -Filter *.java | Select-String -Pattern '"item_id"'
```

#### 坑

| 坑 | 说明 |
|---|---|
| **传递依赖** | 前置的前置也算（如某 API 又依赖另一个库）|
| **纯 API 前置** | Curios / Patchouli 这类只需看接口签名，收益低但要确认 |
| **版本漂移** | 不同前置版本行为不同，**必须记下确切的版本号**，写进交付说明 |
| **CF 直链防盗链** | 直接 `Invoke-WebRequest` 可能 403，需要 Referer 或走代理；Modrinth 没这问题 |

#### 判定：什么时候必须写「沿用」

如果正文要写某个机制，而这个机制的方法调用落在前置 jar 里：

```
✗ 本模组提供好感度系统，可以培养亲密度
✓ 好感度与驯养沿用 NFF: Girls 本体的体系，本模组只做生物扩展
```

**写错方向比写少更严重**——会把前置的功劳算在扩展头上。

'''

def main() -> int:
    t2 = R02.read_text(encoding="utf-8")
    marker = "### 6.10 内容核实：手册会过时，代码才算数"
    i = t2.find(marker)
    if i < 0:
        print("✗ 02 里找不到 §6.10")
        return 1
    moved = t2[i:].rstrip()
    t2 = t2[:i].rstrip() + "\n"
    R02.write_text(t2, encoding="utf-8")
    print(f"✓ 从 02 切出 §6.10 + §6.10.1（{len(moved.splitlines())} 行），02 剩 {len(t2.splitlines())} 行")

    content = HEADER + moved + NEW_6102
    R09.write_text(content, encoding="utf-8")
    print(f"✓ 写入 rules/09-核实纪律.md（{len(content.splitlines())} 行）")

    # 路由页：加 09，改 §6.10 那一行，并把 09 列进「几乎每次都要读」
    s = SKILL.read_text(encoding="utf-8")

    old_idx = "| §6 的 6.3 / 6.10 / 6.10.1 | 找手册、内容核实、一次结论不算结论 | `rules/02-模组页.md` |"
    new_idx = "| §6 的 6.3 | 先找模组自带手册（Patchouli） | `rules/02-模组页.md` |\n| §6 的 6.10 / 6.10.1 / 6.10.2 | 内容核实、一次结论不算结论、连前置一起反编译 | `rules/09-核实纪律.md` |"
    if old_idx in s:
        s = s.replace(old_idx, new_idx, 1)
        print("  ✓ §号索引已更新")
    else:
        print("  ⚠ §号索引那行没匹配到")

    old_read = """**几乎每次都要读的两块**：`rules/03-语体与去AI味.md`（不读必被退「AI 味」）、
`rules/07-工具与交付.md`（不读不知道跑哪几个检查脚本）。"""
    new_read = """**几乎每次都要读的三块**：

- `rules/03-语体与去AI味.md` —— 不读必被退「AI 味」
- `rules/07-工具与交付.md` —— 不读不知道跑哪几个检查脚本
- `rules/09-核实纪律.md` —— 只要正文出现数字、机制、获取方式就适用；
  有前置的模组必须连前置一起反编译"""
    if old_read in s:
        s = s.replace(old_read, new_read, 1)
        print("  ✓ 「几乎每次都要读」已加 09")

    SKILL.write_text(s, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
