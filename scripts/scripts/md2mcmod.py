#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2mcmod.py —— 把 Markdown 转成 MC 百科（mcmod.cn）正文可直接粘贴的 HTML 片段。

转换规则对齐 Mcmodder v2.3 的「Markdown → HTML」按钮
（源码：src/ueditor/AdvancedUEditor.ts#performMarkdownIt）：

  * h1 ~ h6        -> <p>[hN=标题]</p>      百科用这种标记生成目录（标题内必须是纯文本）
  * ul / ol        -> 加 class="list-paddingleft-2"
                      且 li 内的裸文本必须包成 <p>（百科只接受 li > p 结构）
  * code           -> 百科不支持 <code>，默认降级为普通文字（见下方“合规”说明）
  * blockquote     -> 百科不支持，降级为普通段落（每行一个 <p>）
  * pre            -> 保留，并补上百科的代码块语言类 brush:<lang>;toolbar:false
  * hr             -> 丢弃（编辑规范第 22 条禁止字符型分割线）

合规说明（对应 MC 百科《主站编辑规范》）：
  * 第 26 条禁止“过于鲜艳/明亮刺眼/五颜六色的文字颜色”，所以行内代码**默认不染色**；
    确实需要彩色标识符时加 --color-code，输出的颜色写法取自 UEditor 的 forecolor（rgb 形式）。
  * 第 35 条要求“代码长度超过 500 字节须用代码块工具处理”，所以真正的代码请写成
    围栏代码块（```java），脚本会转成 <pre class="brush:java;toolbar:false">。

用法：
    python md2mcmod.py input.md [-o output.html] [--color-code]
不指定 -o 时输出到同目录同名 .mcmod.html
"""

import argparse
import html
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 行内元素

_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITALIC = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
# 图片必须先于链接处理，否则 ![alt](url) 里的 [alt](url) 会先被当成链接
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def _placeholder(idx: int) -> str:
    return f"\x00{idx}\x00"


def _protect(text: str, pattern, build, store: list) -> str:
    """先把匹配到的片段换成占位符并入栈，避免后续规则二次处理它。"""
    def repl(m):
        store.append(build(m))
        return _placeholder(len(store) - 1)
    return pattern.sub(repl, text)


def _restore(text: str, store: list) -> str:
    for idx in range(len(store) - 1, -1, -1):
        text = text.replace(_placeholder(idx), store[idx])
    return text


def inline(text: str, color_code: bool = False) -> str:
    """行内 Markdown -> 百科可用的行内 HTML。

    顺序要点：先转义，再把「行内代码」和「链接」抽成占位符，
    最后才处理粗体/斜体 —— 否则代码里出现的 `*`（如 `org.apache.*`）会被当成斜体标记吃掉。

    行内代码默认不加颜色（合规优先）；color_code=True 时用 UEditor forecolor 的 rgb 写法上色。
    """
    text = html.escape(text, quote=False)
    store: list = []
    text = _protect(text, _IMAGE,
                    lambda m: f'<img src="{m.group(2)}" alt="{html.escape(m.group(1), quote=True)}">',
                    store)
    if color_code:
        text = _protect(text, _INLINE_CODE,
                        lambda m: f'<span style="color:rgb(199,37,78)">{m.group(1)}</span>', store)
    else:
        text = _protect(text, _INLINE_CODE, lambda m: m.group(1), store)
    text = _protect(text, _LINK,
                    lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', store)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    return _restore(text, store)


def plain(text: str) -> str:
    """标题专用：百科的 [hN=标题] 里只能放纯文本，必须把所有行内标记剥掉。"""
    text = _INLINE_CODE.sub(r"\1", text)
    text = _LINK.sub(r"\1", text)
    text = _BOLD.sub(r"\1", text)
    text = _ITALIC.sub(r"\1", text)
    return html.escape(text, quote=False)


def code_block(lang: str, body: str) -> str:
    """围栏代码块 -> 百科的 <pre class="brush:xxx;toolbar:false">。"""
    brush = (lang or "text").strip().lower() or "text"
    alias = {
        "js": "javascript",
        "ts": "javascript",
        "sh": "shell",
        "bash": "shell",
        "ps1": "powershell",
        "py": "python",
        "yml": "yaml",
        "plain": "text",
        "plaintext": "text",
        "": "text",
    }
    brush = alias.get(brush, brush)
    escaped = html.escape(body, quote=False)
    return f'<pre class="brush:{brush};toolbar:false">{escaped}</pre>'


# ---------------------------------------------------------------- 块级解析

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HR = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_FENCE = re.compile(r"^\s*```+\s*([\w+#-]*)\s*$")
_UL = re.compile(r"^\s*[-*+]\s+(.*)$")
_OL = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_QUOTE = re.compile(r"^\s*>\s?(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
# 百科块级指令，形如 [ban:title_menu]；整行独立出现时不包 <p>
_BLOCK_DIRECTIVE = re.compile(r"^\[(?:ban|hide|nocat):[^\[\]]*\]$")


def split_table_row(line: str):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def convert(md: str, color_code: bool = False, bold_first_col: bool = False) -> str:
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # 空行
        if not line.strip():
            i += 1
            continue

        # 围栏代码块
        m = _FENCE.match(line)
        if m:
            lang = m.group(1)
            i += 1
            buf = []
            while i < n and not _FENCE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1  # 跳过结束围栏
            out.append(code_block(lang, "\n".join(buf)))
            continue

        # 表格
        if "|" in line and i + 1 < n and _TABLE_SEP.match(lines[i + 1]):
            header = split_table_row(line)
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(split_table_row(lines[i]))
                i += 1
            t = ["<table><tbody>"]
            t.append("<tr>" + "".join(
                f'<th>{inline(c, color_code)}</th>'
                for c in header) + "</tr>")
            for r in rows:
                cells = [inline(c, color_code) for c in r]
                # 补齐/截断到表头列数，避免百科表格错位
                while len(cells) < len(header):
                    cells.append("")
                cells = cells[: len(header)]
                # --bold-first-col：把首列（名称列）加粗，方便在表格里扫读
                if bold_first_col and cells and cells[0]:
                    cells[0] = f"<strong>{cells[0]}</strong>"
                t.append("<tr>" + "".join(
                    f'<td valign="top"><p>{c}</p></td>' for c in cells) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue

        # 标题
        m = _HEADING.match(line)
        if m:
            level = len(m.group(1))
            title = plain(m.group(2))
            out.append(f"<p>[h{level}={title}]</p>")
            i += 1
            continue

        # 分隔线：丢弃
        if _HR.match(line):
            i += 1
            continue

        # 百科块级指令（例如 [ban:title_menu]）：必须作为裸文本输出。
        # 这类指令由百科的正文渲染器在文本层解析，套进 <p> 里可能失效，
        # 因此只在「整行独立、后面紧跟空行」时按指令处理，避免误伤正文里的同名文字。
        if _BLOCK_DIRECTIVE.match(line) and (i + 1 >= n or not lines[i + 1].strip()):
            out.append(line.strip())
            i += 1
            continue

        # 引用块：百科不支持，降级为普通段落，每行一段
        if _QUOTE.match(line):
            while i < n and _QUOTE.match(lines[i]):
                out.append(f"<p>{inline(_QUOTE.match(lines[i]).group(1), color_code)}</p>")
                i += 1
            continue

        # 无序列表
        if _UL.match(line):
            items = []
            while i < n and _UL.match(lines[i]):
                items.append(_UL.match(lines[i]).group(1))
                i += 1
            out.append('<ul class="list-paddingleft-2">' + "".join(
                f"<li><p>{inline(x, color_code)}</p></li>" for x in items) + "</ul>")
            continue

        # 有序列表
        if _OL.match(line):
            items = []
            while i < n and _OL.match(lines[i]):
                items.append(_OL.match(lines[i]).group(1))
                i += 1
            out.append('<ol class="list-paddingleft-2">' + "".join(
                f"<li><p>{inline(x, color_code)}</p></li>" for x in items) + "</ol>")
            continue

        # 普通段落：连续非空行合并为一段
        buf = [line.strip()]
        i += 1
        while i < n and lines[i].strip() and not (
            _HEADING.match(lines[i])
            or _FENCE.match(lines[i])
            or _UL.match(lines[i])
            or _OL.match(lines[i])
            or _QUOTE.match(lines[i])
            or _HR.match(lines[i])
            or ("|" in lines[i] and i + 1 < n and _TABLE_SEP.match(lines[i + 1]))
        ):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(buf), color_code)}</p>")

    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Markdown -> MC 百科正文 HTML")
    ap.add_argument("input", help="输入的 .md 文件")
    ap.add_argument("-o", "--output", help="输出文件（默认同名 .mcmod.html）")
    ap.add_argument("--color-code", action="store_true",
                    help="给行内代码上色（默认不上色，以符合编辑规范第 26 条）")
    ap.add_argument("--bold-first-col", action="store_true",
                    help="表格首列加粗（名称列扫读用）")
    args = ap.parse_args(argv)

    src = Path(args.input)
    if not src.is_file():
        print(f"找不到输入文件：{src}", file=sys.stderr)
        return 2

    md = src.read_text(encoding="utf-8")
    result = convert(md, color_code=args.color_code, bold_first_col=args.bold_first_col)

    dst = Path(args.output) if args.output else src.with_suffix(".mcmod.html")
    dst.write_text(result, encoding="utf-8")

    stats = {
        "[hN=] 标题": len(re.findall(r"\[h[1-6]=", result)),
        "<pre> 代码块": result.count("<pre"),
        "<table> 表格": result.count("<table>"),
        "<ul>/<ol> 列表": result.count("<ul") + result.count("<ol"),
        "彩色行内代码": result.count("rgb(199,37,78)"),
        "<blockquote> 残留": result.count("<blockquote"),
        "<code> 残留": result.count("<code"),
    }
    print(f"已写出：{dst}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
