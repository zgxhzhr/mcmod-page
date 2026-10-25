# -*- coding: utf-8 -*-
"""把 HTML 表格里「连续的、首列内容相同」的行合并成一个 rowspan 单元格。

为什么需要它：Markdown 表格表达不了合并单元格，而百科里「一个名称对应多行」
（如 性格 -> 4 个事件）用合并格最好读。做法是**源稿里首列重复写**，转成 HTML 后
再跑一遍本脚本，把相邻同名行合成 rowspan。

用法：
    python rowspan.py 页面.mcmod.html              # 原地改写
    python rowspan.py 页面.mcmod.html -o 输出.html  # 另存

约定：
    * 含 <th> 的表头行不参与合并，原样保留；
    * 只比较**首列**，首列内容完全相同（含空）且相邻才合并；
    * 其它列原样保留，行的顺序不变。
"""
import argparse
import re
from pathlib import Path

_TABLE = re.compile(r"<table[^>]*>.*?</table>", re.S)
_TABLE_OPEN = re.compile(r"<table[^>]*>")
_ROW = re.compile(r"<tr[^>]*>.*?</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>.*?</td>", re.S)


def _inner(cell_html: str) -> str:
    """取出 <td ...> ... </td> 之间的内容，作为比较用的键。"""
    m = re.match(r"<td[^>]*>(.*)</td>", cell_html, re.S)
    return (m.group(1) if m else "").strip()


def _merge_table(table_html: str):
    rows = _ROW.findall(table_html)
    if not rows:
        return table_html, 0, 0

    open_tag = _TABLE_OPEN.match(table_html).group(0)
    out, groups, i = [], 0, 0

    # 表头（含 <th>）原样保留
    if "<th" in rows[0]:
        out.append(rows[0])
        i = 1

    while i < len(rows):
        cells = _CELL.findall(rows[i])
        if not cells:
            out.append(rows[i])
            i += 1
            continue
        key = _inner(cells[0])

        j = i + 1
        while j < len(rows):
            nxt = _CELL.findall(rows[j])
            if not nxt or _inner(nxt[0]) != key:
                break
            j += 1

        span = j - i
        if span == 1:
            out.append(rows[i])
        else:
            out.append(re.sub(r"<td", f'<td rowspan="{span}"', rows[i], count=1))
            for k in range(i + 1, j):
                out.append("<tr>" + "".join(_CELL.findall(rows[k])[1:]) + "</tr>")
            groups += 1
        i = j

    return open_tag + "<tbody>" + "".join(out) + "</tbody></table>", groups, len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="把 HTML 表格首列相邻同名行合并为 rowspan")
    ap.add_argument("input", help="输入 .mcmod.html")
    ap.add_argument("-o", "--output", help="输出路径；省略则原地改写")
    args = ap.parse_args()

    path = Path(args.input)
    html_text = path.read_text(encoding="utf-8")

    total_tables = total_groups = total_rows = 0

    def repl(m):
        nonlocal total_tables, total_groups, total_rows
        merged, groups, rows = _merge_table(m.group(0))
        total_tables += 1
        total_groups += groups
        total_rows += rows
        return merged

    result = _TABLE.sub(repl, html_text)
    Path(args.output or args.input).write_text(result, encoding="utf-8", newline="\n")

    print(f"表格 {total_tables} 张 / 数据行 {total_rows} 行 / 合并出 {total_groups} 个 rowspan 组")
    if total_groups == 0:
        print("提示：没有任何行被合并——检查源稿里首列是否「重复写」了同一名称。")


if __name__ == "__main__":
    main()
