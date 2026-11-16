#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""把单体 SKILL.md 拆成「路由 + 规则块」（v2）。

v1 的 bug：heading 正则取出的是去掉 # 的标题文本，但分组规则却按 `^## 6` 匹配，
于是只有一个块被命中。v2 改成两级判定：

  1) 二级标题（##）决定大桶
  2) 三级及以下标题按例外表覆盖（§6 内部要拆到 5 个文件）

§编号一律不改 —— 全文有大量「见 §6.2.2.34」交叉引用，改号等于全部失效。
"""
import re
from pathlib import Path

ROOT = Path(r"E:\Mod\模板与工具\发布\mcmod-page")
SRC = ROOT / "SKILL.md"
RULES = ROOT / "rules"

# 二级标题 → 文件（"ROUTER" = 留在 SKILL.md 路由里）
TOP = [
    (r"^0 安装", "08-环境与本地模型.md"),
    (r"^0\.5 索引", "ROUTER"),
    (r"^1 快速上手", "ROUTER"),
    (r"^2 百科正文能吃什么", "01-语法与规范.md"),
    (r"^3 编辑规范", "01-语法与规范.md"),
    (r"^4 排版决策链", "01-语法与规范.md"),
    (r"^5 工具", "07-工具与交付.md"),
    (r"^6 风格基线", "02-模组页.md"),
    (r"^7 常见坏表", "07-工具与交付.md"),
    (r"^8 提交前校验", "07-工具与交付.md"),
    (r"^9 交付话术", "07-工具与交付.md"),
    (r"^10 本地改写模型", "08-环境与本地模型.md"),
    (r"^11 模组分类", "06-分类与判定.md"),
    (r"^12 短页面批量判定", "06-分类与判定.md"),
]

# 三级及以下：例外覆盖（先命中先归）
OVERRIDE = [
    # §6 内部
    (r"^6\.4 ", "04-资料页与图标.md"),
    (r"^6\.5 ", "04-资料页与图标.md"),
    (r"^6\.7", "04-资料页与图标.md"),
    (r"^图标规范", "04-资料页与图标.md"),
    (r"^哪些类型天然没有图标", "04-资料页与图标.md"),
    (r"^6\.8 ", "04-资料页与图标.md"),
    (r"^6\.2\.2\.4", "04-资料页与图标.md"),
    (r"^6\.2\.2\.9", "04-资料页与图标.md"),

    (r"^6\.1\.9", "05-批量与合并综合.md"),
    (r"^6\.1\.10", "05-批量与合并综合.md"),
    (r"^6\.1\.11", "05-批量与合并综合.md"),
    (r"^6\.2\.0", "05-批量与合并综合.md"),
    (r"^6\.6 ", "05-批量与合并综合.md"),
    (r"^6\.9 ", "05-批量与合并综合.md"),
    (r"^写法$", "05-批量与合并综合.md"),
    (r"^附言里要明确请求管理员", "05-批量与合并综合.md"),
    (r"^什么时候不该合并", "05-批量与合并综合.md"),

    (r"^6\.2 ", "06-分类与判定.md"),
    (r"^6\.2\.1", "06-分类与判定.md"),
    (r"^6\.2\.2$", "06-分类与判定.md"),

    # 语体 / 去 AI 味 → 03
    (r"^文风标准", "03-语体与去AI味.md"),
    (r"^去 AI 味", "03-语体与去AI味.md"),
    (r"^6\.2\.2\.2", "03-语体与去AI味.md"),
    (r"^高频口语", "03-语体与去AI味.md"),
    (r"^该删", "03-语体与去AI味.md"),
    (r"^自查清单", "03-语体与去AI味.md"),
    (r"^10\.2\.1", "03-语体与去AI味.md"),
    (r"^10\.2\.2", "03-语体与去AI味.md"),
]

DESC = {
    "01-语法与规范.md": "正文语法、编辑规范、排版决策链",
    "02-模组页.md": "模组页结构、标题层级、分节、附言、版本信息禁令",
    "03-语体与去AI味.md": "文风标尺、口语对照、对比句式清单、实测案例",
    "04-资料页与图标.md": "资料页正文与字段、排版细则、图标全流程",
    "05-批量与合并综合.md": "通用文本 / 合并 / 综合 / 抽象资料 / 批量新增 / 注入脚本",
    "06-分类与判定.md": "专有名词、命名、食物属性、模组分类、短页面判定",
    "07-工具与交付.md": "渲染转换工具、常见坏表、提交前校验、交付话术",
    "08-环境与本地模型.md": "安装、本机路径、7B 改写模型",
}

HEAD = re.compile(r"^(#{2,4})\s+(.*)$")


def parse(lines):
    inside = False
    marks = []
    for i, ln in enumerate(lines):
        if ln.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            continue
        m = HEAD.match(ln)
        if m:
            marks.append((i, len(m.group(1)), m.group(2)))
    chunks = []
    for k, (i, lvl, title) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        chunks.append({"line": i, "lvl": lvl, "title": title,
                       "head": lines[i], "body": lines[i + 1:end]})
    return chunks


def main() -> int:
    lines = SRC.read_text(encoding="utf-8").split("\n")

    fm = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                fm = i + 1
                break

    chunks = parse(lines[fm:])
    for c in chunks:
        c["line"] += fm

    # 按标题层级继承：子块默认跟随父块，父块被 override 改了，子块跟着走。
    # v2 的 bug：#### 子块只按「上一个二级标题」分桶，于是 §6.1.9 下面的
    # 「怎么建这条通用文本」「IRR 导出格式」全漏进了模组页那个文件。
    cur = "ROUTER"
    stack = []  # [(level, bucket)]
    for c in chunks:
        while stack and stack[-1][0] >= c["lvl"]:
            stack.pop()
        parent = stack[-1][1] if stack else "ROUTER"

        if c["lvl"] == 2:
            cur = "ROUTER"
            for pat, bucket in TOP:
                if re.search(pat, c["title"]):
                    cur = bucket
                    break
            b = cur
        else:
            b = parent if parent != "ROUTER" else cur
            for pat, bucket in OVERRIDE:
                if re.search(pat, c["title"]):
                    b = bucket
                    break
        c["bucket"] = b
        stack.append((c["lvl"], b))

    RULES.mkdir(exist_ok=True)
    groups = {}
    for c in chunks:
        groups.setdefault(c["bucket"], []).append(c)

    total = 0
    for fname in DESC:
        cs = sorted(groups.get(fname, []), key=lambda x: x["line"])
        if not cs:
            print(f"⚠ {fname} 空")
            continue
        head = [
            f"# {DESC[fname]}",
            "",
            f"> 规则块 `{fname}`，属于 `mcmod-page` 技能。",
            "> **交付前必须整块读完本文件**，不要跳读，也不要只看 SKILL.md 的摘要。",
            "> §编号与 SKILL.md 一致，可按编号交叉引用。",
            "",
            "---",
            "",
        ]
        body = []
        for c in cs:
            body.append(c["head"])
            body.extend(c["body"])
        (RULES / fname).write_text("\n".join(head + body), encoding="utf-8")
        total += len(head) + len(body)
        print(f"  ✓ {fname:<26} {len(cs):>3} 块 {len(head)+len(body):>5} 行")

    router_chunks = sorted(groups.get("ROUTER", []), key=lambda x: x["line"])
    keep = []
    for c in router_chunks:
        keep.append(c["head"])
        keep.extend(c["body"])
    (ROOT / "_router_keep.tmp.md").write_text("\n".join(keep), encoding="utf-8")

    print(f"\n规则块合计 {total} 行；路由保留 {len(keep)} 行；原文 {len(lines)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
