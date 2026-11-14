# 导出工具索引（从 Downloads 收录）

本目录存放**游戏内导出器** jar，供 `scripts/mcauto/run.py --mods` 使用。
`index.json` 是机器可读清单（file / kind / mc / modid / ver / self_trigger）。

## 选哪个（见 rules/07 §5.8 / §5.9）

| MC 版本 | 加载器 | 工具 | mode |
|---|---|---|---|
| 1.21.1 | NeoForge | `LetMeSeeSee-NeoForge-Minecraft1.21.1-*.jar` | `--mode lms`（物品+实体） |
| 1.20.1 | Fabric | `IconRenderer-Fabric-*-mc1.20.1*.jar` | `--mode iconr2`（需自触发构建） |
| 1.19.2 | Fabric | `IconRenderer-Fabric-*-mc1.19.2*.jar` | `--mode iconr2` |
| 1.20.1 | **NeoForge 20.1.x** | `IconRenderer-Forge-1.20.1-1.2.0.jar` | ⚠️ 名为 Forge，实为 **mojmap 构建**：在 Forge 47.4.23（SRG）上会崩（`Error computing listener list for LevelEvent$Unload`）。要 NeoForge 1.20.1 运行时 |
| 1.19.2 | Forge | `IconRenderer-Forge-1.0.2-1.19.2.jar` | stock，需手点界面（agent 在 SRG 上不可用） |
| 1.16.x | Forge | `IRR-1.0-1.16.*.jar` | `--mode irr` |
| 1.12.2 / 1.7.10 | Forge | `IRR_V1.1.0_MC*.jar` | `--mode irr` |

## 启动前自检（省时间）

1. 目标模组的前置是否齐全（mods.toml 依赖 + 反编译 grep，mandatory=false 也可能是硬依赖）；
2. 加载器运行时名：NeoForge 1.21 / Fabric 自触发 / **Forge 1.20.1 是 SRG，agent 不可用**；
3. 起客户端 30 秒内查 `agent.log`：出现 `Setting user` / `joined` 才说明前置对了。
