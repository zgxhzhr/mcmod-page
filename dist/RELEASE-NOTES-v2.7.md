# mcmod-page v2.7

> 相对 v2.6 的增量 = 2026-11-16 全天的审核口径终版 + 两轮事故回写（7663 观鸟 / 29737 兽人入侵 / 24115 冬瓜 三批实测）。

## 一、结构判定口径终版（rules/05 §6.1.9-6.1.11）

```
非实体族：独有数据能压成 1~2 张表 → 一律综合（子资料 html:""，数值进父表）
实体族：固定引用通用文本（各页自足属性行），通用文本压成 2~3 段主题式
通用文本页：资料类型 = 游戏设定，资料分类 = 实际概念名（如「基本概念」）
           —— 弃用 {文本} 自定义分类；「类型随条目族」的第一轮修正也已作废
           先例：起源 3111「基本概念/起源原生种族」、21637「起源附加种族」
抽象父资料 ename 必填（rules/06 §6.2.4）；装饰方块父页「XX 装饰方块（XX Block）」；
工具四件套父页「XX 套具（XX Kit）」，剑除外（§6.2.2/6.2.3）
```

7663 实测：羽毛 18 + 鸟肉 10 从通用文本改综合后，批内重复率 35% → 15%。

## 二、文本规范新增（rules/01/03）

- **`[icon:…]` 空格**：`生命值 [icon:health=20, 点]`——`[` 左侧、`,` 右侧各一个半角空格（审核附言「盘古之白」）；audit-delivery 双向阻断，历史 11 批 170 处已全量修正
- **回复→恢复**：康复语境写「恢复」（`huifu_hits()` 语境判定，答复语境的「回复消息」不误伤）
- **状态效果等级 ≤10 用罗马数字**（速度 II、力量 I），>10 保持阿拉伯（用户口径）
- **作者原文保护线画在「信息」不在「字句」**（rules/02 §6）：措辞可部分改写、模糊指代要写明、可补代码实证；**阻断性否定句（「而不是虚空刷新…」）必须改写**——属结构问题不是措辞偏好
- 实体族通用文本要压紧：2~3 段、按主题合并，一句一段不合格

## 三、字段与脚本（rules/04/07 + 工具）

- **耐久度进表单字段**：站上「最大耐久」的 data-multi-id 是 `damage`（2026-11-16 实测，不是元数据）；JSON 键用 `durability`，`damage` 留作别名；正文不再复述耐久数值
- **userscript v2.50**：无图标条目**显式清空 base64**（`clearOrSet`）+ 勾「删除大小图标」两件事都做——勾选框只是持久屏蔽开关，删不掉这次带进面板的图
- **重跑 build 脚本会静默覆盖交付后补丁**（7663 实测退回 46 阻断）→ rules/07 新增维护纪律
- **preflight 两个误报修复**：icon 属性值（saturation-level=1.2）与带单位小数（冷却 1.5 秒）不再被当版本号；真版本无证据照样阻断（正负例双测）

## 四、游戏内导出矩阵更新（rules/07 §5.8.1，全部实测）

| 链路 | 状态 |
|---|---|
| 1.21.1 NeoForge lms/lmsent | ✅ 29737 复跑：85 物品 + 120 实体全出 |
| **1.20.1 Forge iconr** | ✅ **已打通**（E 盘 47.4.26 目录 + agent ≥2026-11-16 构建；旧文档「不可用」结论作废）——agent 修了 ModLauncher 类加载器上下文与 needsWorld 门控 |
| 1.12.2 / 1.7.10 Forge IRR | ✅ self-trigger（mcauto-world + IRR_V1.1.0）；7663 实测 18 秒 48 图标 |
| 其余 12 条链路 | 与 v2.6 一致 |

## 五、核实纪律新增（rules/09 §6.10.1）

- **⑥ 补丁落盘必须回读**：脚本打印的 ✓ 不算数（agent 修复连骗三轮，锚点差一个 `private`/CRLF 就是零写入）；改完 `git diff --stat`，锚点打 repr
- **⑦ 交稿前拿上一批专名扫本批**：24115 曾把 23964 的合成描述整句串档写进正文；每个「A 由 B 合成」句式必须能在**本 jar** 指出文件

## 六、新增永久工具（main 包）

`make-preview.py`（卡片式 preview.html，每批默认交付物）、`refresh-sha.py`（规则修订后一键刷历史 README 指纹）、`probe-item-form.js`（站方表单字段探测）、`gen-items.py`/`gen-baby-items.py`、`judge-batch.py`、`category-crawl.py`

## 七、本批交付实例

- **7663 观鸟**：52 行；无 zh_cn 批 name 英文 ename 空；实体通用文本「鸟类」；血量曾被 SRG 直觉带偏（111267_a=MAX_HEALTH，stable_39 救回）
- **29737 兽人入侵**：171 行；92 注册实体→建 71 剔 21（投射物不建页，30083 先例）；作者 desc/lore 直接入正文
- **24115 冬瓜**：串档事故与修复记录见 rules/09 §6.10.1⑦

## 安装

```powershell
# skill 本体
powershell -ExecutionPolicy Bypass -File install.ps1
# 或手动：解压 mcmod-page-v2.7.zip 覆盖 ~/.dsh/skills/mcmod-page/
# 导出工具链（agent jar + 各版本 world-mod 源 + exporter jars）：mcmod-page-v2.7-toolchain.zip 覆盖到同目录
# 装完重跑一次 scripts/refresh-sha.py 刷新历史交付 README 的指纹
```

## 包

- `mcmod-page-v2.7.zip` — 技能本体（SKILL + rules ×9 + scripts ×28 + docs）
- `mcmod-page-v2.7-toolchain.zip` — mcauto 全量（agent jar 含 2026-11-16 修复）+ 12 链路导出器 + world-mod 工程源
