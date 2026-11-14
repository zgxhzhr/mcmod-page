# BOOTSTRAP · 在另一台机器上从零长出这套能力

面向对象：**另一台机器上的 AI（或人）**。按 §0 → §6 顺序做，每节末尾有验收命令，
过了再进下一节。跳步会在低版本上撞一脸错，因为那些坑只有踩过才知道。

> 这里没有「一键脚本」。原因很实在：能力依赖**你机器上已有的东西**（PCL 装了哪些版本、
> 哪个 JDK 在哪、代理端口多少），这些东西没法猜。所以给的是**缺口自检 + 逐层装配**。

---

## §0 先自检：这台机器现在能做什么

```powershell
cd scripts\mcauto
python doctor.py
```

它会按 环境 / 启动器 / 工具 jar / 网络 四类逐项报 `✓` `!` `✗`，并在末尾给出
**L1~L6 能力分层**。缺什么、去哪装，每项后面都有 `→` 提示。

给 AI 用的话加 `--json`，输出机器可读结果。

**验收**：`doctor.py` 退出码 0（或你能解释剩下每个 `✗` 为什么可以先不管）。

---

## §1 配路径（唯一需要手改的地方）

```powershell
notepad scripts\mcauto\config.json
```

```json
{
  "cache":   "…\\mcauto-cache",            // 前置/原版/服务端 jar 缓存
  "worlds":  "…\\mcauto-worlds",           // 预生成的超平坦存档
  "mc_dirs": ["I:\\PCL\\.minecraft"],      // PCL 的 .minecraft（可多个）
  "java":    {"8": "…", "17": "…", "21": "…"},
  "gradle":  {"8": "…", "7": "…", "4": "…", "2": "…"},
  "proxy":   "http://127.0.0.1:10808",
  "tool_dirs": ["…下载目录", "…放工具 jar 的目录"],
  "tool_jars": {}
}
```

也可以不改文件，用环境变量指向别的 json：`$env:MCAUTO_CONFIG="D:\my-mcauto.json"`。

**两个硬约束**

1. **`java["8"]` 必须在工作区之外。** DSH 会把工作区标成 Low 完整性级别，
   从工作区里启动的 exe 继承 Low IL，连 `%TEMP%` 都写不了 —— Minecraft 的
   jar 重映射、LWJGL2 解压、ImageIO 全部会失败，报错还完全不指向真因。
2. `mc_dirs` 里**装了版本的那个**要放前面（`doctor.py` 会告诉你哪个有 versions）。

**验收**：

```powershell
python config.py     # 打印解析后的路径，javaw 路径都应该是实存文件
```

---

## §2 L1：让客户端能起、停在标题界面

需要的就 JDK + 一个版本目录。1.16.5 及以下用 JDK 8，1.17~1.20 用 17，1.21 用 21。

```powershell
python run.py --version "1.19.2-forge-43.5.2" --mode iconr --target-modid <modid> `
  --mods <工具jar> <目标模组jar> --work <工作目录> --timeout 60 --hidden --console
```

**验收**：`<work>\agent.log` 里出现 `Setting user:` 且没有 `Unable to launch`。

### 常见失败

| 现象 | 原因 |
|---|---|
| `UnsupportedClassVersionError: 61.0` | 用了 JDK 17 跑 1.16.5，要 JDK 8 |
| `no lwjgl64 in java.library.path` | 原生库没解压 —— `extract_natives` 应该已处理 |
| `Modules _1._18._2 and minecraft export package` | `-p` 模块路径时不能再加原版 jar |
| 报 `NoSuchMethodError: ThrowablePatternConverter.<init>` | 继承链里 log4j 重复，按 `group:artifact` 去重 |

---

## §3 L2：让客户端进世界（每个世代方式不同）

| 世代 | 方式 | 参数 |
|---|---|---|
| 1.20+ | 原生 quickPlay | `--quickPlaySingleplayer mcauto` |
| 1.19.2 / 1.18.2 / 1.16.5 Fabric | 本地专用服务端 + `--server` | 脚本自动挑空闲端口 |
| 1.16.5 Forge | **mod 打开 `ConnectingScreen`** | `world-mod/` 产物 |
| 1.12.2 Forge | **mod 调 `launchIntegratedServer`** | `world-mod-1.12.2/` 产物 |
| 1.7.10 Forge | **mod 调 `launchIntegratedServer`** | `world-mod-1.7.10/` 产物 |

为什么低版本必须走 mod：1.12.2 / 1.7.10 运行时**类名完全混淆**（`Minecraft` 叫 `bib`），
javaagent 按名反射什么都拿不到；1.16.5 没有 quickPlay，`--server` 也不自动连，
而 `ConnectScreen` 在 Forge ModLauncher 的类加载器下按名加载不到。

**验收**：日志里出现 `Client attempting to join` 或 `已进世界`。

> 1.7.10 需要先手工拼一个版本目录，见 §4。

---

## §4 1.7.10 专项：手工拼 Forge 客户端

1.7.10 的 Forge installer **只支持 `--installServer`**（客户端要 GUI），所以自己拼：

```
versions/1.7.10-Forge-mcauto/1.7.10-Forge-mcauto.json
  inheritsFrom: "1.7.10"
  mainClass:    "net.minecraft.launchwrapper.Launch"
  libraries:
    net.minecraft:launchwrapper:1.11
    org.ow2.asm:asm-all:5.0.3
    net.minecraftforge:forge:1.7.10-10.13.4.1614-1.7.10:universal
    lzma:lzma:0.0.1
    com.google.guava:guava:17.0
  minecraftArguments: "… --tweakClass cpw.mods.fml.common.launcher.FMLTweaker"
```

三个坐标坑（都踩过）：

| 坑 | 真相 |
|---|---|
| `com.github.jponge:lzma:0.0.1` | maven / forge / central **全 404**。真实坐标是 **`lzma:lzma:0.0.1`** |
| guava 版本 | Forge 1.7.10 要 **17**，原版 1.7.10 带 15。把 17 作为**子版本库**加进去，继承链合并按 `group:artifact` 覆盖才生效 |
| Forge 版本号 | userdev 只在 `1.7.10-10.13.4.1614-1.7.10` 这种**带 -1.7.10 后缀**的坐标下存在 |

**验收**：客户端起来后日志出现 `constructed (1.7.10, javac build)`。

---

## §5 L3：触发导出

每种工具调用的入口不一样，`run.py` 的 `--mode` 管这个：

判断用哪种 mode，看三件事：**工具是谁**、**能不能发命令**、**谁负责触发**。

| 版本 | 工具 | 正确用法 |
|---|---|---|
| 1.21.1 NeoForge | LMS fork | `--mode lms --self-trigger` |
| 1.20.1 Fabric | IconRenderer fork | `--mode iconr2 --self-trigger` |
| 1.19.2 Fabric | IconRenderer fork | `--mode iconr2 --self-trigger` |
| 1.18.2 Fabric | IconRenderer fork | `--mode iconr2 --self-trigger` |
| 1.16.5 Fabric | IconRenderer fork | `--mode iconr2 --self-trigger` |
| 1.20.1 Forge | IconRenderer-Forge | `--mode iconr`（靠命令） |
| 1.19.2 Forge | IconRenderer-Forge | `--mode iconr`（靠命令） |
| 1.18.2 Forge | IconRenderer-Forge | `--mode iconrd`（直接 `new FileHelper(modid)`） |
| 1.16.5 Forge | IRR + world mod | `--mode irr --self-trigger` |
| 1.12.2 Forge | IRR + world mod | `--mode irr --self-trigger` |
| 1.7.10 Forge | IRR + world mod | `--mode irr --self-trigger` |

**为什么 Fabric 一律 `--self-trigger`**：agent 发命令依赖「找 connection 上名字含 command
的单 String 方法」，而 Fabric 的 intermediary 名（`method_45730` 之类）不含 command，
fallback 直接失效（报 `找不到可用的命令发送方法`）。我们 fork 的 `McAutoEntry`
读 `-Dmcauto.*` 自己触发导出，绕开这个问题。

**Fabric 模组几乎都要 `fabric-api`**，不带上会看到 Fabric Loader 弹
`Incompatible mod set!`（提示 requires any version of fabric-api）。
`autodeps.py` 能自动补；手工跑时记得一起 `--mods` 进去。

**产物目录名各工具不同**（`IconRendererOutput` / `IconRenderer/Json` / `export`），
`run.py` 已经会在目录对不上时自动在 `game` 下找刚生成的 json。

**验收**：`<work>\game\export\` 下有 `*_item.json`，且条目数 > 0。

---

## §6 L4~L6：图标正确性 / 依赖 / 批量

- **L4** 脚本只能出图，判断不了像不像 —— 必须人看。已知画不对的：射线类被拉成平面、
  坐骑类需要乘客、部分渲染依赖运行时状态。这些会标 `noVisual` / `suspect`。
  人工补图走 `_icons` 覆盖目录。
- **L5** `autodeps.py` 按崩溃日志反推前置（`NoClassDefFoundError` + `requires <modid>`），
  从 Modrinth 搜下载。**必须能访问 Modrinth**；直连约 0.06 MB/s，代理 1.7 MB/s。
- **L6** `batch.py` 按 jobs.json 批量跑，输出 `<out>/<modid>/manifest.json` + 原生格式。

---

## §7 我们重编 / 新增的 jar（重要）

这套能力**不是全靠上游**。下面这些 jar 是我们自己构建或改造的，
来源、构建方式、为什么改，都记在这里 —— 换机器时要么用 release 里的产物，
要么按命令自己编。

### 7.1 three world mods（我们原创，负责「进世界」）

| jar | 版本 | 源码 | 构建 |
|---|---|---|---|
| `mcauto-world-1.16.5.jar` | 1.16.5 Forge | `scripts/mcauto/world-mod/` | ForgeGradle **5.1** + Gradle **7.6.4** + official 1.16.5 映射 |
| `mcauto-world-1.12.2.jar` | 1.12.2 Forge | `scripts/mcauto/world-mod-1.12.2/` | ForgeGradle **2.3** + Gradle **4.10.3** + JDK 8 + mappings `snapshot_20171003` |
| `mcauto-world-1.7.10.jar` | 1.7.10 Forge | `scripts/mcauto/world-mod-1.7.10/` | **不用 ForgeGradle**，`javac -cp forge-1.7.10-universal.jar` |

构建命令：

```powershell
# 1.16.5
cd scripts\mcauto\world-mod
$env:JAVA_HOME="C:\Program Files\Java\jdk-17"
gradle-7.6.4\bin\gradle.bat build --no-daemon

# 1.12.2
cd scripts\mcauto\world-mod-1.12.2
$env:JAVA_HOME="C:\Users\MKIII\jdks\jdk8"
gradle-4.10.3\bin\gradle.bat build --no-daemon -g E:\gradle-fg12

# 1.7.10（纯 javac）
javac -encoding UTF-8 -cp forge-1.7.10-universal.jar -d classes src\mcauto\*.java
# 打包时 mcmod.info 必须是**数组**
```

三个都得注意的坑：

- **1.12.2**：`mcmod.info` 必须是**数组**；写成单个 object 时 FML 报
  `Zip file … failed to read properly, it will be ignored`，然后当 non-mod 注入，mod 根本不加载。
- **1.12.2**：不能手工从 `build/classes` 重打包 —— 那是 MCP 名字，运行时要 SRG 名字
  （`NoSuchMethodError: getMinecraft`）。必须用 `reobfJar` 产物。
- **1.12.2**：Forge `14.23.5.2860` 在 maven 上**没有 userdev**，编译要用同线的 `14.23.5.2847`。
- **1.7.10**：`TickEvent` 在 **FML 总线**（`FMLCommonHandler.instance().bus()`），
  不在 `MinecraftForge.EVENT_BUS`。只注册后者时 mod 能加载但 tick 永不触发。
- **1.16.5**：连接界面类名是 **`ConnectingScreen`**，不是 `ConnectScreen`；
  `TitleScreen` 在 1.16.5 叫 `MainMenuScreen`（父界面传 `null` 即可）。

### 7.1.1 agent jar（构建产物，可复现）

`mcauto-agent.jar`（class 61，1.17+）与 `mcauto-agent8.jar`（`--release 8`，≤1.16）
**不是手写产物**，由下面这条命令生成（源码在 `scripts/mcauto/agent/AgentMain.java`）：

```powershell
python scripts\mcauto\build_agent.py
```

中间产物 `agent-build/`（`.class` 与 `MANIFEST.MF`）已在 `.gitignore` 里，
不进版本库；两个 jar 保留在版本库里，方便直接用，也可以随时重建。

### 7.2 两个上游 fork（补构建配置 / 加自动化入口）

| fork | 分支 | 我们改了什么 |
|---|---|---|
| `zgxhzhr/LetMeSeeSee` | `1.21.1-neoforge` | 补 1.21.1 NeoForge 构建、自动化入口（读 `-Dmcauto.*`）、实体图标导出 |
| `zgxhzhr/IconRenderer` | `v2.0` | 新增 `Fabric-1.16.5` / `1.18.2` / `1.19.2` 构建配置 + `McAutoEntry` 自触发入口 |

构建产物**发在各自 fork 仓库的 release 里**，不放在本仓库：

- `zgxhzhr/LetMeSeeSee` → release `mcauto-1.0.8`（LGPL-3.0，含许可全文与源码说明）
- `zgxhzhr/IconRenderer` → release `fabric-all-mcauto`（GPL-3.0，同上）

原因：这两个上游分别是 LGPL-3.0 / GPL-3.0，二进制要和许可全文、源码声明一起发；
而本仓库是 MIT，混在一起会让 MIT 声明失效（聚合可以，合并不行）。
**fork 的 release 只放我们自己的构建**，上游 jar 不放、也不合并上游分支
（只 cherry-pick，见各仓库 `FORK.md`）。

### 7.3 自备的第三方 jar（**不在** release 里）

| jar | 从哪拿 | 用于 |
|---|---|---|
| `IRR_V1.1.0_MC1.7.10.jar` | CurseForge | 1.7.10 |
| `IRR_V1.1.0_MC1.12.2.jar` | CurseForge | 1.12.2 |
| `IRR-1.0-1.16.X.jar` | CurseForge | 1.16.5 |
| `IconRenderer-Forge-1.20.1-1.2.0.jar` | CurseForge 原发布页 | 1.20.1 Forge |
| `IconRenderer-Forge-1.0.2-1.19.2.jar` | CurseForge 原发布页 | 1.19.2 Forge |
| `IconRenderer-Forge-1.0.2-1.18.2forced.jar` | 第三方 forced 构建 | 1.18.2 Forge |

这些**没有公开源码仓库**（IconRenderer-Forge）或上游不是我们（IRR），
所以不能放进我们的 release，只能各自去取。

---

## §8 完整支持矩阵与实测数据

见仓库根 `README.md`。当前覆盖 **12 条链路**（1.7.10 → 1.21.1）。

---

## §9 到新机器上第一次跑，建议这么做

```
1. doctor.py            → 看清缺什么
2. config.json          → 填路径
3. doctor.py            → 复检
4. 挑一个 ≥1.20 的版本跑通 L1+L2+L3（最快验证整条链）
5. 再跑 1.19.2（服务端模式）
6. 最后跑低版本（1.16.5 → 1.12.2 → 1.7.10），一个版本一个坑
7. 用同一个模组跨版本跑一遍，比对物品数是否一致（一致性抽查）
```

**第 7 步是唯一能证明「真的可移植」的动作。** 没在第二台机器上跑过之前，
任何「可移植」的说法都只是设计意图。

---

## §10 边界（这些我做不到，别指望）

- **图标像不像**：只能人看，脚本只能出图 + 标可疑
- **实体渲染**：离屏渲染注定有一批画不对（射线、坐骑、依赖运行时状态的）
- **macOS / Linux**：光标看门狗用了 Win32 API，路径分隔符也是 Windows 的；
  没做平台分支，理论上要改 3 处（看门狗、路径、启动器假设）
- **没有在第二台机器实测过**：本文件按本机经验写，真实差异要靠跑一遍补回来
