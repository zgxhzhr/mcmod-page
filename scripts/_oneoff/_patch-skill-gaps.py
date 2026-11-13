#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""补齐「会话记忆 → skill 文件」的 5 处缺口。

比对方法：把本次会话确立的 22 条规则逐条 grep rules/ 与 SKILL.md，
命中 17 条、缺 4 条、另有 1 条（画廊后置）只写在路由页里没进规则块。

缺口：
  A. 画廊必须在文末              → 只出现在 SKILL.md 必答三问，无规则细节
  B. 通用文本的 30% 阈值          → 05 里只说「重复率较高」，无数值线
  C. 批量面板支持的 5 个页面       → 只有零散提及，没有 page 清单
  D. /class/edit 上的模组介绍面板  → 完全没写
  E. targetUrl + 连续执行          → 完全没写（且 targetUrl 猜不出来，是关键坑）
"""
from pathlib import Path

ROOT = Path(r"E:\Mod\模板与工具\发布\mcmod-page")
R02 = ROOT / "rules" / "02-模组页.md"
R05 = ROOT / "rules" / "05-批量与合并综合.md"
R07 = ROOT / "rules" / "07-工具与交付.md"

GALLERY = '''

## 6.2.2.36 画廊必须在页面最后

审核点名：「2. 画廊后置」。这条独立于标题层级——就算 h1/h2 全对，画廊夹在中间照样退。

### 规则

```
[h1=概述]
…正文…
[h2=分节] …
[h1=画廊]        ← 必须在最末，前面不能再有任何正文
```

`[h1=画廊]` 之后只能是图片表格或图片段落，**不能再出现正文或其它标题**。

### 反例（实测被退）

```
[h1=概述]
[h1=画廊]        ← 夹在第二位
[h1=改动范围]
[h1=六种村庄]
```

审核附言原文：「1.适当添加 h2 标题；2.画廊后置」。两条分开判，改好 h2 不代表画廊自动合规。

### 自检

```powershell
# 标题序列里 画廊 必须是最后一个
Select-String -Path 草稿.html -Pattern "\\[h[12]=" | Select-Object -Last 1
```

最后一行的标题不是「画廊」而页面里又确实有画廊 → 顺序错了。
'''

THRESHOLD = '''

### 6.1.9.1 什么时候该拆：30% 是线，不是感觉

§6.1.9 说「重复率较高」时用通用文本，但「较高」要落成数字才可判。实测取的线是 **30%**：

| 重复率 | 判断 | 实例 |
|---|---|---|
| **≥30%** | 拆通用文本 | Malstone 26143：19 条饰品，重复 30% → 拆 |
| **<30%** | 不拆，逐条交 | Canned Food 14363：31 条，重复 14% → 不拆 |
| 极高（>80%）且条目 >100 | 走 §6.2.0 拆包交 IRR | — |

**怎么算**：把同族各条正文按段落去重，统计「出现次数 ≥ 族内半数」的段落字数占比。

```python
# 段落重复率（按 80% 条数出现即算重复）
from collections import Counter
seg = Counter()
for r in rows:
    for m in re.finditer(r"<p>(.*?)</p>", r["html"]):
        seg[re.sub(r"<[^>]+>", "", m.group(1))] += 1
total = sum(len(r["html"]) for r in rows)
dup = sum(len(k) * v for k, v in seg.items() if v >= len(rows) * 0.8)
print(f"重复率 {dup/total:.0%}")
```

### 拆了之后别把页面拆空

CANS 那批拆完，果汁页只剩 50 字符（一句「不恢复饥饿值」）。此时要判断：
**这一句是不是「功能」？** 是功能就留（§6.4 要求正文写功能），不是就删。
「不恢复饥饿值、也没有额外状态效果」是功能描述，留着不算冗余。
'''

BATCH = '''

### 5.7 批量面板（`mcmod-batch.user.js`）支持的页面与队列

同一个脚本管五种页面，靠 `location.pathname` 分流：

| 页面 | 用途 | 面板 |
|---|---|---|
| `/item/add/<classId>/` | 批量新增资料 | 蓝色「批量新增」 |
| `/item/list/<classId>-<type>.html` | 读取列表与编辑链接 | 列表面板 |
| `/item/edit/<id>/` | 批量编辑已有资料 | 蓝色「批量编辑」 |
| **`/class/edit/<classId>-<subId>/`** | **模组介绍再编辑** | 绿色「模组介绍 · 批量编辑」 |
| `/verify*` | 审核列表读取 | 验证面板 |

#### 三个必须知道的机制

**① `@match` 漏一个页面，脚本就不会加载**

扩展版还要同步 `manifest.json` 的 `content_scripts.matches`。
`/class/edit/*` 是 v2.40 才补上的 —— 之前模组编辑页「面板消失」的根因就是这个，
不是面板被清掉，是脚本压根没注入。

**② 队列存在 sessionStorage 的全局键里，不要按 classId 分开存**

```
mcmod-class-edit-plan = { items: [...], autoRun, paused }
```

早期按 `mcmod-class-edit-<classId>` 分开存，翻页后对不上就「丢 JSON」。
现在整份存一处，每页按 `classId` 取自己那条。

**③ 自动跳转必须有 `targetUrl`，而且猜不出来**

再编辑页 URL 是 `/class/edit/<classId>-<verifyId>/`，**第二段是随机 id**，
同一个模组每次退回都不一样。只能从审核列表的 `againHref` 取：

```
{"classId": 2674, "name": "Bunny Boots",
 "targetUrl": "/class/edit/2674-818373/", ...}
```

没有 `targetUrl` 就只能手动翻页，「连续执行」走不下去。

#### 连续执行流程

```
填入正文 + 附言 + 说明 → 提交 → 等 2.6s → 点确认 → 等 2.8s
   → 按下一条的 targetUrl 跳转 → 新页面加载 2s 后自动重复
   → 队列跑完提示「队列完成」
```

找不到提交按钮或等不到确认框 → 自动 `paused`，不会盲点。
「停止」保留队列，可再点「连续执行」续跑。

#### 改了脚本之后

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1      # 同步到技能目录
python scripts\\install-extension.py                          # 重建扩展（MV3）
# 再去 edge://extensions 点「重新加载」
```
'''


def append(path: Path, text: str, marker: str) -> bool:
    t = path.read_text(encoding="utf-8")
    if marker in t:
        print(f"  跳过 {path.name}（已存在）")
        return False
    path.write_text(t.rstrip() + "\n" + text, encoding="utf-8")
    print(f"  ✓ {path.name}  +{len(text.splitlines())} 行")
    return True


def main() -> int:
    print("补缺口：")
    append(R02, GALLERY, "6.2.2.36 画廊必须在页面最后")
    append(R05, THRESHOLD, "6.1.9.1 什么时候该拆")
    append(R07, BATCH, "5.7 批量面板")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
