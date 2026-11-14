# world-mod-1.12.2

1.12.2 的「进世界 + 触发 IRR 导出」mod。1.16.5 版在 `../world-mod/`。

## 为什么 1.12.2 必须走 mod

1.12.2 运行时类名**完全混淆**（`Minecraft` 叫 `bib`），javaagent 按名反射拿不到
`Minecraft` / `Level` / `Player` 中的任何一个，也就不可能程序化进世界。
mod 是编译期依赖 MC 的（ForgeGradle 负责 reobf），代码里可以直接写：

```java
mc.launchIntegratedServer(world, world, null);   // 进本地存档
ExportUtils.INSTANCE.exportMods();               // 调 IRR 导出
```

## 构建

```powershell
# 需要 JDK 8 + Gradle 4.10.3（ForgeGradle 2.3 不支持新 Gradle）
$env:JAVA_HOME="C:\Users\MKIII\jdks\jdk8"
gradle build
```

## 两个坑（都已踩过）

1. **Forge 版本**：`1.12.2-14.23.5.2860` 在 maven 上**没有 userdev 包**，
   编译要用同线的 `1.12.2-14.23.5.2847`（同 14.23.5，API 一致），
   产物在 2860 上正常加载。
2. **mcmod.info 必须是数组**。写成单个 object 时 FML 会报
   `Zip file ... failed to read properly, it will be ignored`，
   然后当成「non-mod file」注入 classpath，mod 根本不加载。

## 实测

```
1.12.2 Forge 14.23.5.2860 + IRR_V1.1.0_MC1.12.2
tutescnsitems：213 个物品 / 467.3 KB / 17 秒（中文名 + 图标齐全）
```
