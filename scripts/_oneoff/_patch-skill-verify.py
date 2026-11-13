#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""补 §6.10.1「一次反编译的结论不算结论」+ 修路由页对 §6.10 的错误映射。

背景：skill 里只有 §6.10「手册会过时，代码才算数」，
讲的是「代码 vs 手册」的优先级，没有讲「代码读一遍就信」这件事。
本次会话至少三次踩在这上面：
  - 苹果箱先判「纯装饰无存储」，查 loot_table 才发现破坏掉 8 个苹果，定位全错
  - 动物谷那页表格「宠物商人」列缺行，第一遍交付的数据不完整
  - SRG 名（f_196xx_）靠单份映射会错位，必须两份映射交叉

另修：路由页把 §6.10 指到 06/04，实际在 02-模组页.md，导致「去核对」的人找不到规则。
"""
from pathlib import Path

ROOT = Path(r"E:\Mod\模板与工具\发布\mcmod-page")
R02 = ROOT / "rules" / "02-模组页.md"
SKILL = ROOT / "SKILL.md"

SECTION = '''

### 6.10.1 一次反编译的结论不算结论

§6.10 讲的是「代码比手册可靠」，但**代码读一遍就信，同样会错**。
本节是核实纪律，适用于所有要写进正文的事实。

#### ① 必须全量反编译，不要只看一个类

模组的行为经常不在你以为的那个类里：

| 你以为在 | 实际常在 |
|---|---|
| `XxxItem` | `XxxEatProcedure` / 事件监听器 / mixin |
| `XxxBlock` | `XxxBlockEntity` / `loot_tables/blocks/*.json` |
| 代码 | `assets/*/lang`、`models/`、`recipes/`、`blockstates/` |

所以流程固定是：**整个 jar 全量反编译 → 全仓库 grep → 再细读命中的类**。

```powershell
java -jar cfr.jar 模组.jar --outputdir 输出目录 --silent true
# 然后全仓库搜，不是搜单个文件
Get-ChildItem 输出目录 -Recurse -Filter *.java | Select-String -Pattern '"item_id"'
```

#### ② 一个结论要两条独立证据链

单一来源不下结论。可用的组合：

```
代码参数  +  资源文件（lang / 模型 / 战利品表）
全量 grep +  单个类细读
mojang 映射 + forge 映射（两份交叉对 SRG 名）
```

**失败案例**：SRG 名 `f_196xx_` 如果只查一份映射表就下结论，
一旦偏移一位，「夜视」会被写成「隐身」。必须 client.txt 与 joined.tsrg 两边对上。

#### ③ 第一遍产物不可信，包括自己上一轮写的

交付前回头核一遍。真实案例：

| 案例 | 第一遍结论 | 复核后 |
|---|---|---|
| 苹果箱 | 「纯装饰，不具备存储功能」 | 查 `loot_tables/blocks/apple_crate.json`：破坏掉 8 个苹果，箱体不返还 —— **定位整个错了** |
| 动物谷猫狗表格 | 品种表第二列只有部分行有值 | 逐行核对后补齐（20 行「宠物商人」+ 3 行「自然生成」） |
| Golden Carrot Juice | 饥饿值 1 | 用户质疑 → 回查 `super(1, 0.0f)` 确认是 1 —— 结论对，但**必须能翻出证据** |

#### ④ 每个数字都要能指到来源

| 写进正文的内容 | 必须来自 |
|---|---|
| 饥饿值 / 饱和度 | `FoodProperties` 构造参数（注意实际饱和度 = nutrition × modifier × 2）|
| 药水效果的等级与时长 | `MobEffectInstance(effect, ticks, amplifier)` |
| 掉落物与数量 | `loot_tables/**/*.json` |
| 生命值 / 护甲 | 属性注册（`Attributes.MAX_HEALTH` 等）|
| 注册名 / 名称 | `item.x` / `block.x` 的 lang 键 |
| 配方 | `data/*/recipes/*.json` 的 pattern / key |

**说不出来源的数字不要写**。宁可留空标「待确认」。

#### ⑤ 交付前五问

```
□ 整个 jar 都反编译了吗（不是只反了几个类）？
□ 这个结论有几条独立证据？
□ 每个数字能指到具体哪一行代码 / 哪个 json？
□ 上一轮的结论复核过吗？
□ 有没有「查了一处就下全局结论」的地方？
```

'''

def main() -> int:
    t = R02.read_text(encoding="utf-8")
    if "6.10.1 一次反编译的结论不算结论" in t:
        print("已存在，跳过 §6.10.1")
    else:
        t = t.rstrip() + "\n" + SECTION
        R02.write_text(t, encoding="utf-8")
        print(f"✓ 已写入 §6.10.1，02 共 {len(t.split(chr(10)))} 行")

    # 修路由页映射
    s = SKILL.read_text(encoding="utf-8")
    old = "| §6 的 6.2 / 6.2.1 / 6.2.2 / 6.3 / 6.10 | 命名、核实 | `rules/06-分类与判定.md`、`rules/04-资料页与图标.md` |"
    new = "| §6 的 6.2 / 6.2.1 / 6.2.2 | 命名 | `rules/06-分类与判定.md` |\n| §6 的 6.3 / 6.10 / 6.10.1 | 找手册、内容核实、一次结论不算结论 | `rules/02-模组页.md` |"
    if old in s:
        s = s.replace(old, new, 1)
        SKILL.write_text(s, encoding="utf-8")
        print("✓ 路由页 §6.10 映射已修正（原来指到 06/04，实际在 02）")
    else:
        print("⚠ 路由页那行没匹配到，需人工确认")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
