# mcmod-page —— MC百科页面编写技能包

给 AI agent 用的技能：把 Markdown 稿子转成 **MC百科（mcmod.cn）能直接粘贴的 HTML**，
按官方编辑规范检查内容，并把长清单排成能读的表格结构。

> 本仓库即技能目录：`SKILL.md` 在根目录，`scripts/` 在根目录下。

## 从 GitHub 装（推荐）

```bash
git clone https://github.com/zgxhzhr/mcmod-page
cd mcmod-page

# Windows
powershell -ExecutionPolicy Bypass -File .\install.ps1
# macOS / Linux
bash install.sh
```

不想用 git 就下 [Releases](https://github.com/zgxhzhr/mcmod-page/releases) 里的 zip 解压，跑同样的安装脚本。

## 包里有什么

```
mcmod-page/
├── SKILL.md              # 技能正文（agent 读这个）
├── README.md             # 本文件，给人看
└── scripts/
    ├── md2mcmod.py       # Markdown -> 百科 HTML（零依赖，只用标准库）
    ├── rowspan.py        # 表格首列合并成 rowspan
    └── 示例-源.md        # 可跑的最小示例
```

## 安装（用脚本，或手动三步）

**懒人版**：解压后在文件夹里跑 install.ps1（Windows）或 install.sh（macOS/Linux），它会自己复制到技能目录并打印自检命令。

**手动版**：


1. **放到位。** 把整个 `mcmod-page` 文件夹（不是只放 SKILL.md）复制到技能目录：

   | 平台 | 路径 |
   |---|---|
   | Windows | `%USERPROFILE%\.dsh\skills\mcmod-page\` |
   | macOS / Linux | `~/.dsh/skills/mcmod-page/` |

   用其它客户端（Claude Code、Cursor…）就放进它的 skills 目录，格式通用。

2. **重启会话。** 新开一个对话，说「帮我优化这个百科页」，或显式 `skill mcmod-page`。

3. **跑一遍示例确认脚本可用：**

   ```bash
   cd <技能目录>/scripts
   python md2mcmod.py 示例-源.md -o 示例.mcmod.html
   python rowspan.py 示例.mcmod.html
   ```

   第二行应输出：`表格 1 张 / 数据行 7 行 / 合并出 2 个 rowspan 组`。

> 需要 Python 3.8+。两个脚本只用标准库，不需要 `pip install` 任何东西。

## 可选但强烈建议：Windows MCP

装了它，agent 能直接操作你的浏览器，于是**「装篡改猴 → 装 MC百科脚本 → 把稿子粘进编辑器」这三步它自己做**，你只在开头同意一次、结尾看一眼。不装也能用，只是这三步得你自己来。

它会做的事：

1. 打开扩展商店装**篡改猴**，并到扩展详情页把「允许用户脚本」打开（这步不开，脚本装了也不执行）。
2. 打开 [Mcmodder 直链](https://github.com/Charcoal-Black/Mcmodder/releases/latest/download/mcmodder.user.js)，在篡改猴安装页点「安装」，然后回「已安装脚本」核对版本号。
3. 打开百科编辑页 → 「源代码编辑器」→ 粘贴生成的 HTML → 预览 → 保存 → 截图给你确认。

验证脚本已生效：打开 mcmod.cn，个人中心应多出「设置 → 脚本设置」。

```powershell
# 1) 装（Windows，需 Python 3.10+）
pip install uv          # 若还没装 uv
uvx windows-mcp serve   # 不常驻方式；或 pip install windows-mcp 后 windows-mcp serve
```

```yaml
# 2) 在客户端 MCP 配置里注册（以 DSH 为例：<profile>/cordis.patch.yml）
- insert:
    - id: mcp-windows
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: windows
        transport: stdio
        command: 'windows-mcp'
        args: [ 'serve' ]
        failOnStartupError: false
```

3. 重启客户端，工具列表里应出现 `mcp__windows__*`。

项目：<https://github.com/CursorTouch/Windows-MCP>（PyPI `windows-mcp`）

> ⚠️ **安全**：这个 MCP 等于把桌面控制权交给 agent（能截屏、点击、输入）。
> 建议在专用账号或虚拟机里用，操作前关掉敏感窗口（网银、密码管理器），用完就停。

## 常见问题

**Q：它生成的 HTML 粘进百科后表格没边框/列宽怪？**
A：粘完点一次「正文预览」。`style="width"`、`word-break` 这类属性由编辑器自己补，不影响结果。

**Q：合并单元格（rowspan）没生效？**
A：先确认 `rowspan.py` 跑过了；再看源稿里首列是否**重复写**了同一名称（不是留空）。若预览里仍被拆开，说明你的编辑器版本会剥 `rowspan`，退回"按类型分组 + 每组一张小表"的排法（SKILL.md §4 的 L3）。

**Q：需要改内容而不是排版怎么办？**
A：SKILL.md 里写了边界——**作者的措辞不要改**，只做标点/空格/`注：`前缀/反引号这类整理；专有名词和 mod 自造术语原样保留。

**Q：能不能把 Markdown 直接交给浏览器里的油猴脚本转？**
A：不建议。Mcmodder 的 Markdown→HTML 只告警不修正，会在 `<code>`/`<blockquote>` 上打红框，而那些内联样式会被一起保存进正文。用 `scripts/md2mcmod.py`。
