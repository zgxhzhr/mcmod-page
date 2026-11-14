# mcauto world-mod（ForgeGradle 工程）

各版本的「进世界 + 触发 IRR 导出」mod。低版本（1.12.2 / 1.7.10）类名混淆、
1.16.5 没有 quickPlay，这些都必须靠 mod 侧在**编译期**处理，javaagent 做不到。

## 为什么必须 mod 侧

| 需要的东西 | javaagent 为什么不行 |
|---|---|
| `loadWorld` 的 `Function` / `Function4` 参数 | 是函数式接口，agent 写不出合法实现 |
| `Minecraft.WorldSelectionType` | 是**私有嵌套枚举**，编译期才能引用 |
| `ConnectingScreen(Screen, Minecraft, String, int)` | Forge ModLauncher 类加载器下按名加载不到 |
| 1.12.2 / 1.7.10 的 MC 类 | 运行时类名完全混淆（`bib` 之类） |

## 1.16.5 已验证通过

```
gradle 7.6.4 + ForgeGradle 5.1 + official 1.16.5 映射
产物 mcauto-world118-1.0.0.jar
实测 fire_extinguisher 16 个物品 / 22.8 KB / 18 秒
```

用法：

```powershell
python scripts\mcauto\run.py --version "1.16.5-forge-36.2.39" --mode irr --self-trigger `
    --mods <本工程产物> <IRR jar> <目标模组> --work <目录>
```

mod 读 `-Dmcauto.modid` / `-Dmcauto.connect` / `-Dmcauto.delay`：
打开 `ConnectingScreen` 连本地服务端 → 进世界后调 IRR 的 `ExportMain#DoExport()` → 写 `_mcauto_done`。

## 其它版本

1.12.2 / 1.7.10 需要各自的老版本 ForgeGradle 工程（映射与 API 都不同），
复用思路：同样三个动作（拿 client、进世界、调 IRR 导出）。
