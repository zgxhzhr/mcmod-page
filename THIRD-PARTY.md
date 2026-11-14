# 第三方组件与许可边界

本仓库（`mcmod-page`）是 **MIT**。但它依赖/配套的一些组件不是我们的，
也不在本仓库的收下。这份文件把边界写清楚，避免「MIT」被误解成覆盖了全部东西。

## 一、本仓库自己的东西（MIT）

| 内容 | 说明 |
|---|---|
| `scripts/` 下全部流水线脚本 | 路径配置、启动器封装、依赖解析、批量编排、页面写作脚本 |
| `scripts/mcauto/agent/` | javaagent 源码（跨加载器反射） |
| `scripts/mcauto/world-mod*/` | 三个「进世界 + 触发导出」mod 的源码（1.16.5 / 1.12.2 / 1.7.10） |
| `scripts/mcauto/irr-trigger/` | IRR 触发 mod 源码 |
| `rules/` `SKILL.md` `docs/` `README.md` | 写作规则、装配文档 |
| `examples/` 中的代码与文字 | 见下方「例外」 |

许可全文见 `LICENSE`。

## 二、不在本仓库、也不由 MIT 覆盖的组件

| 组件 | 许可 | 归属 | 获取位置 |
|---|---|---|---|
| **LetMeSeeSee**（含我们的 fork） | **LGPL-3.0** | 上游作者 + 我们的修改 | `zgxhzhr/LetMeSeeSee` 仓库；release `mcauto-1.0.8` |
| **IconRenderer**（含我们的 fork） | **GPL-3.0** | 上游作者 + 我们的修改 | `zgxhzhr/IconRenderer` 仓库；release `fabric-all-mcauto` |
| **IRR（Item Render Rebirth）** | 上游许可 | 上游作者 | CurseForge（**不随本仓库分发**） |
| **IconRenderer-Forge** | 上游许可 | 上游作者 | CurseForge 原发布页（**不随本仓库分发**） |
| **Minecraft / Forge / Fabric** | 各自上游 | Mojang / Forge / FabricMC | 自行安装（**不随本仓库分发**） |

两个 fork 的二进制**只发在各自仓库的 release 里**，随附许可全文与源码说明。
本仓库的 release 只放 MIT 产物（流水线包 + 三个 world mod），并通过链接指向 fork。

### 为什么这样分

MIT 与 GPL 可以在**同一个项目页面聚合**（aggregation），但不能**合并成一个作品**。
所以：fork 的源码留在 fork 仓库（继承 GPL/LGPL），本仓库只留 MIT 代码 + 链接。
把 GPL 代码搬进本仓库会让「MIT」这个声明失效。

## 三、我们重编/新增的 jar 在哪

| jar | 许可 | 发布位置 |
|---|---|---|
| `mcauto-pipeline.zip`（含全部脚本与 mod 源码） | MIT | 本仓库 release `mcauto-2026.11.15` |
| `mcauto-world-1.16.5.jar` / `-1.12.2.jar` / `-1.7.10.jar` | MIT（我们的原创 mod） | 同上 |
| `let_me_see_see-*.jar` | LGPL-3.0 | `zgxhzhr/LetMeSeeSee` release |
| `IconRenderer-Fabric-*-mcauto.jar` | GPL-3.0 | `zgxhzhr/IconRenderer` release |

我们的三个 world mod 只 `import` Forge 的 API 类，**jar 内不含 Forge 代码**，
因此可以作为独立作品以 MIT 发布。

## 四、例外：`examples/` 里的第三方内容

`examples/` 提供的是**写好的示例页面**。其中出现的：

- 模组名、物品名、生物名
- 模组图标、物品贴图

**版权归对应模组作者**，不在本仓库的 MIT 授权范围内。示例仅用于说明
页面结构与写法，复制使用时请替换为你自己的内容，或遵守原模组的授权条款。

## 五、给使用者的提醒

1. 你要**商用**：MIT 部分随便用；GPL/LGPL 部分（fork 的 jar）受 GPL 约束，
   分发时要一并提供源码与许可。
2. 你要**再发一份**：别把 GPL 的 jar 和 MIT 的脚本打成一个包声称 MIT。
   分开列、分别标许可。
3. 你只想要**流水线**：用 `mcauto-pipeline.zip` 就够了，第三方工具自己去 CurseForge 取。
