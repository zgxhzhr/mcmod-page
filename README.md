# mcmod-page

MC百科（mcmod.cn）页面编写技能 —— **路由页 + 规则块 + 工具脚本**。

写给装了 agent 的环境用：把模组 jar 变成能直接粘进百科「源代码编辑器」的正文，
并按站方审核口径自检。

## 结构

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
scripts/                    通用工具（另见下）
examples/                   真实交付示例：介绍 / 物品 / 通用文本 / 批量再编辑
```

**为什么拆**：单体曾到 178 KB / 3599 行，模型一次读不完只能跳读，
而规则是「漏一条退一次」的性质 —— 跳读等于没读。
拆成路由后，写模组页只读 02 + 03，写资料页只读 04 + 03。

## 安装

```powershell
# 装进技能目录（SKILL.md + rules + scripts + assets 一起）
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

装完重启会话，或显式 `skill mcmod-page`。

自检（跑不通就是没装好）：

```powershell
cd "$env:USERPROFILE\.dsh\skills\mcmod-page"
python scripts\check-page-structure.py --help
```

## 脚本

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

## 批量面板

两种装法，任选其一：

1. **油猴**（推荐）：把 `scripts/mcmod-batch.user.js` 粘进 Tampermonkey
2. **扩展**：跑 `python scripts/install-extension.py` → `edge://extensions` → 加载解压缩的扩展 → 选 `%LOCALAPPDATA%\McmodBatchExt`

支持页面：

```
/item/add/*     批量新增资料
/item/list/*    读取列表与编辑链接
/item/edit/*    批量编辑已有资料
/class/edit/*   模组介绍再编辑（v2.40 起）
/verify*        审核列表读取
```

## 不可分发的部分

- 技能本身依赖的**原版材质**（`vanilla-1.20.1`/`1.21.4` 客户端 jar 里的贴图）不含在本仓库
- **模组 jar 与解包后的源码**、**渲染产物**、**脱敏前的审核列表快照**同样不含
- 各脚本里的本机路径（`E:\Mod\...`、Python 路径）见 `rules/08-环境与本地模型.md`，换机器要改

拿到本仓库后，`rules/` 与 `scripts/` 可以直接用；
`SKILL.md` 里「本机专属依赖」那节列了必须自备的三样东西。

## 约定

- 交付主格式是 **HTML**，粘贴前要在编辑页顶部勾选「源代码编辑器」
- 方括号标记（`[hN=]`、`[ban:]`、`[icon:]`）是百科必需标签，不是格式垃圾
- 附言结尾统一「辛苦 XXX 机了」


## 维护

### 改完推上去

`powershell
git add -A
git commit -m "..."
git push origin main
`

**如果 push 报 Failed to connect to github.com:443 over proxy 127.0.0.1**：
本机 git 配了 http.proxy=127.0.0.1:10808，代理没开时就连不上，但直连是通的。
一次性绕过（不改配置）：

`powershell
git -c http.proxy= -c https.proxy= push origin main
`

### 改规则块之后

1. 跑 powershell -ExecutionPolicy Bypass -File .\install.ps1 同步到技能目录
2. 改过 scripts/mcmod-batch.user.js 还要跑 python scripts\install-extension.py，
   再去 dge://extensions 点重新加载

## License

见 `LICENSE`。
