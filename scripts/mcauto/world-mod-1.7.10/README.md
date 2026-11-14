# world-mod-1.7.10

1.7.10 的「进世界 + 触发 IRR 导出」mod。

## 这个版本为什么不用 ForgeGradle

1.7.10 的 ForgeGradle 1.2 在 `:downloadClient` 阶段会去
`http://s3.amazonaws.com/Minecraft.Download/versions/1.7.10/1.7.10.jar` 下客户端，
**这个地址早就下线了**，构建链根本起不来（FG 的缓存目录里预放 jar 也绕不过，它会重新下）。

但 1.7.10 的 **Forge 类名不混淆**（`cpw.mods.fml.*` / `net.minecraftforge.*`），
只有 MC 内部类混淆。所以：

* 编译期只依赖 `forge-1.7.10-10.13.4.1614-1.7.10-universal.jar`
* MC 内部一律反射 + **SRG 名**（`field_71441_e` 世界、`field_71439_g` 玩家）
* 不需要 reobf，因为没引用 MC 类

```powershell
javac -encoding UTF-8 -cp forge-1.7.10-...-universal.jar -d classes src/mcauto/*.java
# 打包时带上 mcmod.info（**数组**格式）
```

## 两个 1.7.10 特有的坑

1. **TickEvent 在 FML 总线，不在 Forge 总线**

   ```java
   MinecraftForge.EVENT_BUS.register(this);                 // Forge 事件
   FMLCommonHandler.instance().bus().register(this);        // FML 事件 ← TickEvent 在这
   ```

   只注册前者，`ClientTickEvent` 永远不触发（mod 加载了但毫无反应）。

2. **客户端要用手工拼的版本**

   Forge 1.7.10 的 installer 只支持 `--installServer`（客户端要 GUI）。
   手工拼一个版本目录即可（已在 `mcauto-cache` 里备好）：

   ```
   versions/1.7.10-Forge-mcauto/1.7.10-Forge-mcauto.json
     inheritsFrom: 1.7.10
     mainClass:    net.minecraft.launchwrapper.Launch
     libraries:    launchwrapper 1.11 / asm-all 5.0.3 / forge universal / lzma / guava 17
     minecraftArguments: ... --tweakClass cpw.mods.fml.common.launcher.FMLTweaker
   ```

   依赖坑（都踩过）：
   * `lzma` 的坐标是 **`lzma:lzma:0.0.1`**（不是 `com.github.jponge:lzma`，
     后者在 maven 上全 404）
   * Forge 1.7.10 要 **guava 17**，而原版 1.7.10 带的是 15
     —— 把 guava 17 作为「子版本库」加进去，继承链合并时会按 group:artifact 覆盖

## 实测

```
1.7.10 Forge 10.13.4.1614 + IRR_V1.1.0_MC1.7.10
Arda's Uncrafting Table：1 个物品 / 7.9 KB / 6 秒
```
