# mcmod-page

MC百科（mcmod.cn）的两套配套工具：

1. **页面编写技能** —— 路由页 + 规则块，把模组 jar 变成能直接粘进百科「源代码编辑器」的正文，并按站方审核口径自检
2. **导出流水线** —— 一条命令把模组 jar 跑进游戏、自动导出站方格式的物品/实体数据（JSON + 图标），可直接交给站方

两块共用一套脚本目录，但互相独立：只写页面不需要游戏，只导数据不需要读规则块。

---

## 一、页面编写技能

```
SKILL.md                    路由页（133 行）：任务 → 必读规则块 → 工具速查
rules/                      8 个规则块，按任务分文件；§编号与 SKILL.md 一致
  01-语法与规范.md            正文语法、编辑规范、排版决策链
  02-模组页.md               模组页结构、标题层级、分节、附言、版本信息禁令
  03-语体与去AI味.md          文风标尺、口语对照、对比句式清单、实测案例
  04-资料页与图标.md          资料页正文与字段、排版细则、图标全流程
  05-批量与合并综合.md        通用文本 / 合并 / 综合 / 抽象资料 / 批量新增 / 注入脚本
  06-分类与判定.md            专有名词、命名、食物属性、模组分类、短页面判定
  07-工具与交付.md            渲染转换工具、常见坏表、提交前校验、交付话术
  08-环境与本地模型.md        安装、本机路径、7B 改写模型
```

**为什么拆成路由**：单体曾到 178 KB / 3599 行，模型一次读不完只能跳读，
而规则是「漏一条退一次」的性质 —— 跳读等于没读。
拆成路由后，写模组页只读 02 + 03，写资料页只读 04 + 03。

### 安装

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

装完重启会话，或显式 `skill mcmod-page`。

自检（跑不通就是没装好）：

```powershell
cd "$env:USERPROFILE\.dsh\skills\mcmod-page"
python scripts\check-page-structure.py --help
```

### 交付前必答三问

```
1. 这一页的 h1/h2 各几个？          §6.2.2.34 / §6.2.2.35
2. 画廊在末尾吗？要不要 ban？        §6.2.2.31.1
3. 正文里有没有一句话只讲某一个物品/实体？   红线：模组页只写摘要
```

---

## 二、导出流水线

把模组 jar 变成站方能直接吃的 `json + png`。全程无人值守：隔离环境、自动进世界、
自动触发导出、自动补前置、自动收产物。

### 支持矩阵

| MC / 加载器 | 导出工具 | 触发方式 | 状态 |
|---|---|---|---|
| **1.21.1 NeoForge** | LetMeSeeSee（LMS） | agent 反射调静态入口 | ✅ 物品 + 实体 |
| **1.20.1 Forge** | IconRenderer-Forge | agent 派发客户端命令 | ✅ 物品 + 实体 |
| **1.20.1 Fabric** | IconRenderer（fork） | 模组自己 tick 检测 | ✅ 物品 + 实体 |
| 1.16.5 及更早 | — | — | ⬜ 未打通 |

工具都是 mcmod 站方提供的；我们只做自动化和两个 fork（见下）。

### 一条命令

```powershell
# 单个模组（缺前置会自动补）
python scripts\mcauto\autodeps.py `
    --version "1.20.1-Forge_47.4.26" --mode iconr `
    --target-modid malstone `
    --mods tool.jar target.jar `
    --work D:\tmp\run --mc 1.20.1 --loader forge

# 批量
python scripts\mcauto\batch.py --jobs jobs.json --out D:\handover
```

`jobs.json`：

```json
[
  {
    "jar": "路径\\模组.jar",
    "tools": ["路径\\IconRenderer-Forge-1.20.1-1.2.0.jar"],
    "mc": "1.20.1", "loader": "forge",
    "version": "1.20.1-Forge_47.4.26",
    "mode": ["iconr"]
  }
]
```

### 交付目录结构

```
<out>/
├ <modid>/
│   ├ manifest.json                          这个模组用了什么、几条、多大、耗时
│   └ native/
│       ├ lms/let_me_see_see/
│       │   ├ <modid>.json                   物品（站方格式）
│       │   └ _icons/<modid>/*.png           手工覆盖图标（可选）
│       └ lmsent/let_me_see_see/
│           └ <modid>_entity.json            实体
└ manifest.jsonl                            全部模组的汇总
```

**不做任何格式转换** —— 工具输出什么就交什么，站方直接吃。

### 流水线五个脚本

| 脚本 | 做什么 |
|---|---|
| `launcher.py` | 读 PCL 的 version json 生成 java 命令行（不启动 PCL） |
| `agent/AgentMain.java` | Java agent：判断进世界 → 把导出任务投到渲染线程 |
| `make_world.py` | 用官方服务端生成超平坦存档（客户端造世界要走 GUI） |
| `fetch_deps.py` | 读 mods.toml 下**声明式**前置（Modrinth 直查优先） |
| `autodeps.py` | 崩溃报告驱动：缺类 → 找模组 → 下载 → 重跑 |
| `run.py` | 单模组编排（准备环境 / 启动 / 等产物 / 收尾） |
| `batch.py` | 批量编排（读 jobs.json，产出交付目录） |

### 踩过的坑（都写在代码注释里了）

- **Fabric 运行时是 intermediary 名字**，按 mojmap 名字反射全部失效 → Fabric 改成让模组自己处理自动化
- **Forge 1.20.1 是 SRG 名字** → agent 改成按**类型/签名**找成员，不看名字
- **任务投递不能盲试**：`BlockableEventLoop` 有 8 个单 Runnable 参数的方法，其中 submit 系在**当前线程同步执行**；把渲染任务投进去 = agent 线程调 OpenGL → `FATAL ERROR: No context is current`，JVM 当场死。现在按名字白名单（`execute`/`m_18707_`/`method_18856`）
- **过早反射会让 Forge 卡死**：模组加载期碰 `Minecraft` 类会触发事件总线类转换 → 两阶段（先只看类是否加载）
- **客户端命令不在 connection 的调度器里**（那是服务端同步下来的）→ Forge 用 `ClientCommandHandler.runCommand`
- **命令是异步的**：发完要等产物落盘，否则 run.py 立刻杀进程
- **autodeps 会误判**：模组自己抛的 `ClassNotFoundException`（如 LMS 的 `LMSAgent`）不是缺依赖 → 加三道防线（已安装包过滤 / 无意义词过滤 / 下载后校验 jar 里真有那个包）
- **光标会消失**：GLFW 用 `ShowCursor(FALSE)` 把内部计数器压成负数，固定调几次没用 → 循环到返回值 ≥ 0，并在退出路径强制恢复

### 两个 fork（改过才能自动化）

| fork | 改了什么 | 许可 |
|---|---|---|
| [LetMeSeeSee](https://github.com/zgxhzhr/LetMeSeeSee) | 新增实体图标导出 + 给自动化用的静态入口 | LGPLv3 |
| [IconRenderer](https://github.com/zgxhzhr/IconRenderer) | 补了缺失的构建配置 + 自触发入口（Fabric） | GPL-3.0 |

两者都是 copyleft，分发时必须连源码一起给。

### 手工覆盖图标

有些实体的渲染器依赖运行时状态（射线类被拉成平面、坐骑类需要乘客），离屏渲染注定画不对。
导出时会标 `noVisual` / `suspect`，需要人工补图的放到：

```
<缓存>\mcauto-overrides\<modid>\<路径>.png       128×128
<缓存>\mcauto-overrides\<modid>\<路径>_32.png    32×32（可选）
```

`run.py` 每次运行会把它拷进 game 目录，导出结果里带 `"iconSource": "override"`。

---

## 三、脚本总表

### 页面相关

| 脚本 | 用途 |
|---|---|
| `check-page-structure.py` | 结构自检：跨级标题、`<h2>` 误用、不支持的标签、标签闭合 |
| `ai-tell-check.py` | AI 味评分（词表 + 句长分布） |
| `render-mc-model.py` / `batch-render-models.py` | 按 `models/block/*.json` 还原方块外观（带 UV） |
| `render-block-iso.py` | 简单立方块等轴测 |
| `render-item-3d.py` | 物品 3D 预览 |
| `render-spawn-egg.py` | 刷怪蛋图标 |
| `md2mcmod.py` / `md2mcmod-html.py` | Markdown → 百科 HTML |
| `rowspan.py` | 表格首列合并 |
| `gen-items.py` | 批量新增资料 JSON |
| `mcmod-batch.user.js` | 页面内批量面板：新增 / 编辑资料 / 模组介绍再编辑 / 连续执行 |
| `install-extension.py` | 把油猴脚本装成浏览器扩展（MV3，含 `/class/edit/*`） |

`scripts/_oneoff/` 是历史一次性补丁脚本，不用装也能跑主流程，留着备查。

### 批量面板支持页面

```
/item/add/*     批量新增资料
/item/list/*    读取列表与编辑链接
/item/edit/*    批量编辑已有资料
/class/edit/*   模组介绍再编辑（v2.40 起）
/verify*        审核列表读取
```

两种装法：油猴直接粘 `scripts/mcmod-batch.user.js`；或跑 `python scripts/install-extension.py`
→ `edge://extensions` → 加载解压缩的扩展 → 选 `%LOCALAPPDATA%\McmodBatchExt`。

---

## 四、环境要求

| 依赖 | 用途 | 说明 |
|---|---|---|
| PCL + 已安装的 MC 版本 | 导出流水线 | 只读它的 `versions/` 和 `libraries/`，不启动 PCL 本体 |
| JDK 17 / 21 | 跑客户端、编 agent | 1.20.1 用 17，1.21.1 用 21 |
| Python + Pillow | 全部脚本 | 图标处理要用 |
| 代理（可选） | 下前置 | 直连 Modrinth 约 0.06 MB/s，走代理 1.7 MB/s |

**不可分发的部分**：

- 原版材质（`vanilla-1.20.1` / `1.21.4` 客户端 jar 里的贴图）
- 模组 jar 与解包源码、渲染产物、脱敏前的审核列表快照
- 各脚本里的本机路径（`E:\Mod\...`）换机器要改

---

## 五、维护

### 改完推上去

```powershell
git add -A
git commit -m "..."
git push origin main
```

**如果 push 报 `Failed to connect to github.com:443 over proxy 127.0.0.1`**：
本机 git 配了代理，代理没开时连不上但直连是通的。一次性绕过：

```powershell
git -c http.proxy= -c https.proxy= push origin main
```

### 改完之后

| 改了什么 | 要做什么 |
|---|---|
| `rules/` 或 `SKILL.md` | 跑 `install.ps1` 同步到技能目录 |
| `scripts/mcmod-batch.user.js` | 跑 `install-extension.py`，再去 `edge://extensions` 重新加载 |
| `scripts/mcauto/agent/*.java` | 跑 `python scripts/mcauto/build_agent.py` 重新编 jar |
| 两个 fork 的源码 | 各自 `gradlew build`，产物替换到缓存目录 |

## License

见 `LICENSE`。两个 fork 各自沿用上游许可（LGPLv3 / GPL-3.0）。
