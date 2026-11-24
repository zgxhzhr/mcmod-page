#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preflight.py —— 交付总闸：跑完自动检查，并**验证**「规则块阅读声明」不是抄来的。

为什么要有它
------------
两个反复出现的问题：

1. **没全读就开始写** —— 光在 README 里写一句「读了 rules/03 全文」是假声明，
   只要没成本，抄一段文字就能过。
2. **技术断言是猜的** —— 版本号、类名、数值没有出处，看起来合理就写进正文。

所以声明必须**可验证**，而且**带指纹**：

    ## 规则块阅读声明
    - rules/04-资料页与图标.md §6.4 [a1b2c3d4]
    - rules/03-语体与去AI味.md §10.2.5 [9f8e7d6c]
    - rules/09-核实纪律.md §6.10.3 [11223344]

    ## 证据
    | 断言 | 依据 | 状态 |
    | 支持 1.21.1 | neoforge.mods.toml versionRange="[1.21.1]" | 已验证 |
    | 护甲韧性 1.0 | ArmorMaterial 构造第 6 参数 | 已验证 |
    | 会掉落绿宝石 | 推测（未见 loot_table） | 推测 |

校验逻辑：

- `[sha8]` 必须等于该规则文件当前 SHA256 的前 8 位 → **文件改过、或抄的是旧版，直接暴露**
- `§x.y` 必须在该文件里真实存在（按标题 grep）→ **编条款号过不了**
- `## 证据` 里每条「已验证」的断言必须带依据（非空、且不是「大概/应该/我记得」）
- 正文中出现的版本号，必须在证据表里出现过

用法
----
    python preflight.py 交付目录
    python preflight.py 交付目录 --type 资料页
    python preflight.py 交付目录 --no-declaration      # 调试用：跳过声明核对
    python preflight.py 交付目录 --print-sha           # 打印当前规则文件指纹，写声明时直接抄

退出码：0 全过；1 有阻断项。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
RULES = SKILL / "rules"
PY = sys.executable

# 多余描述：几乎总是「补出来的」句子
REDUNDANT = [
    (r"挖掘等级(?:为|是)(?:木|石|铁|金)级", "挖掘等级默认档：只有与同类不同（如镐是钻石级）才写"),
    (r"(?:由|用|把).{0,12}(?:和|加|与).{0,12}(?:合成|做出来|压成)", "合成材料：配方表/合成节已列，正文不必逐条重复"),
    (r"是(?:本模组|模组)添加的(?:食物|物品|方块)", "「模组添加的」是自明信息"),
    (r"可以(?:随时|直接)(?:食用|使用|放置)", "「可以随时食用」这类补语，删掉不影响信息"),
    (r"与本模组.{0,8}一致|沿用原版", "对比句式，没给新信息"),
    (r"(?:生命值|血量|饥饿值|饱食度|护甲值|盔甲值|护甲韧性|饱和度)\s*[:：]?\s*\d", "裸数字：这些属性必须走 [icon:…]"),
    (r"https?://|github\.com|wiki|参考|出处|详见", "正文不写来源：链接/仓库/反编译路径只进 remark"),
]
LAZY_WORDS = ("大概", "应该", "我记得", "可能是吧", "通常", "一般来说", "应该能")

REQUIRED_READS = {
    "资料页": ["rules/04-资料页与图标.md", "rules/03-语体与去AI味.md", "rules/09-核实纪律.md", "rules/01-语法与规范.md"],
    "模组页": ["rules/02-模组页.md", "rules/03-语体与去AI味.md", "rules/09-核实纪律.md"],
    "批量": ["rules/05-批量与合并综合.md", "rules/07-工具与交付.md", "rules/03-语体与去AI味.md"],
}


def sha8(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8]


def rule_path(name: str) -> Path | None:
    """按文件名（可带路径）找到技能目录里的规则文件。"""
    cand = SKILL / name
    if cand.exists():
        return cand
    base = Path(name).name
    for p in RULES.glob("*.md"):
        if p.name == base:
            return p
    return None


def section_exists(p: Path, sec: str) -> bool:
    """§6.10.3 这种编号是否真实出现在文件标题里（也接受 6.10.3 无 §）。"""
    num = sec.lstrip("§").strip()
    txt = p.read_text(encoding="utf-8", errors="replace")
    return re.search(rf"^#{{2,6}}\s*(?:§)?{re.escape(num)}\b", txt, re.M) is not None


def run(script: str, *args: str) -> str:
    p = subprocess.run([PY, str(HERE / script), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def parse_declaration(txt: str):
    """从 README 取出声明行：- rules/xx.md §1.2 [abcd1234]"""
    lines = []
    in_sec = False
    for raw in txt.split("\n"):
        s = raw.strip()
        if s.startswith("##"):
            in_sec = "规则块阅读声明" in s
            continue
        if in_sec and s.startswith("-"):
            lines.append(s.lstrip("- ").strip())
    return lines


def parse_evidence(txt: str):
    """从 README 的 ## 证据 表取出 (断言, 依据, 状态)。"""
    rows = []
    in_sec = False
    for raw in txt.split("\n"):
        s = raw.strip()
        if s.startswith("##"):
            in_sec = "证据" in s
            continue
        if in_sec and s.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", s):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 3 and cells[0] not in ("断言",):
                rows.append((cells[0], cells[1], cells[2]))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--type", default="资料页", choices=list(REQUIRED_READS))
    ap.add_argument("--no-declaration", action="store_true")
    ap.add_argument("--print-sha", action="store_true")
    a = ap.parse_args()

    if a.print_sha:
        for p in sorted(RULES.glob("*.md")):
            heads = re.findall(r"^#{2,6}\s*(§?[\d.]+)", p.read_text(encoding="utf-8", errors="replace"), re.M)
            print(f"{p.name}  [{sha8(p)}]  条款: {', '.join('§' + h.lstrip('§') for h in heads[:8])}")
        return 0

    d = Path(a.dir)
    if not d.is_dir():
        print(f"目录不存在：{d}")
        return 1

    blocks: list[str] = []
    warns: list[str] = []
    infos: list[str] = []

    readme = next((d / n for n in ("README.md", "readme.md") if (d / n).exists()), None)
    readme_txt = readme.read_text(encoding="utf-8", errors="replace") if readme else ""

    # ① 规则块阅读声明：验证条款存在 + 指纹匹配
    if not a.no_declaration:
        if not readme:
            blocks.append("缺 README.md —— 无法核对声明")
        elif "规则块阅读声明" not in readme_txt:
            blocks.append("README 缺「## 规则块阅读声明」（写完规则再交付，见 SKILL.md 交付闸）")
        else:
            decl = parse_declaration(readme_txt)
            if not decl:
                blocks.append("声明小节是空的")
            need = REQUIRED_READS[a.type]
            covered = []
            for line in decl:
                m = re.match(r"(rules/[^\s\[]+\.md)\s*(?:§?([\d.]+))?\s*(?:\[([0-9a-f]{8})\])?", line)
                if not m:
                    blocks.append(f"声明行格式不对：{line}（要 `- rules/xx.md §1.2 [sha8]`）")
                    continue
                rel, sec, got = m.group(1), m.group(2), m.group(3)
                p = rule_path(rel)
                if not p:
                    blocks.append(f"声明引用了不存在的规则文件：{rel}")
                    continue
                covered.append(p.name)
                real = sha8(p)
                if not got:
                    blocks.append(f"{p.name} 缺指纹 —— 跑 `--print-sha` 拿当前 sha8 补上")
                elif got != real:
                    blocks.append(f"{p.name} 指纹不符：声明 {got} ≠ 实际 {real}（文件被改过，或抄的是旧版）")
                if sec and not section_exists(p, sec):
                    blocks.append(f"{p.name} 里没有 §{sec} —— 条款号是编的")
            miss = [Path(r).name for r in need if Path(r).name not in covered]
            if miss:
                blocks.append("声明漏了必读块：" + "、".join(miss))
            if not blocks:
                infos.append(f"规则块声明通过指纹与条款校验（{len(covered)} 个文件）")

    # ② 证据表：已验证的断言必须有依据，且不能是懒词
    ev = parse_evidence(readme_txt)
    if not a.no_declaration:
        if not ev:
            blocks.append("README 缺「## 证据」表（断言 / 依据 / 状态）—— 技术断言必须能指到来源")
        else:
            for claim, basis, state in ev:
                if state.startswith("已验证"):
                    if not basis or basis in ("-", "无", ""):
                        blocks.append(f"断言「{claim}」标了已验证却没有依据")
                    elif any(w in basis for w in LAZY_WORDS):
                        blocks.append(f"断言「{claim}」的依据是懒词（{basis}）")
            infos.append(f"证据表 {len(ev)} 条，其中已验证 {sum(1 for _, _, s in ev if s.startswith('已验证'))} 条")

    # ③ 自动检查
    # 只审计资料页批量包；断言台账(claims-*)、导出原始数据等辅助 JSON 不参与
    SKIP_PREFIX = ("claims-", "claims_", "export-", "_")
    files = sorted(p for p in d.glob("*.json")
                   if not p.name.startswith(".")
                   and not p.name.startswith(SKIP_PREFIX))
    if not files:
        blocks.append("目录里没有 JSON")
    for f in files:
        out = run("audit-delivery.py", str(f), "--json-only")
        v = re.search(r"结论：(PASS|FAIL)", out)
        b = re.search(r"阻断 (\d+) 条", out)
        w = re.search(r"提醒 (\d+) 条", out)
        infos.append(f"{f.name}: {v.group(1) if v else '?'} 阻断 {b.group(1) if b else 0} 提醒 {w.group(1) if w else 0}")
        if v and v.group(1) == "FAIL":
            for line in out.split("\n"):
                if line.strip().startswith("X ["):
                    blocks.append(f"{f.name} {line.strip()}")

    # ④ 多余描述
    versions_in_body = set()
    for f in files:
        try:
            rows = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        for r in rows:
            html = r.get("html") or ""
            if not html or str(r.get("category") or "").strip() == "{文本}" or r.get("type") == "游戏设定":
                continue
            # 版本号扫描先剥 [icon:…] 与标签：saturation-level=1.2 这类属性值不是版本
            _vp = re.sub(r"\[icon:[^\]]*\]", " ", re.sub(r"<[^>]+>", "", html))
            # 带单位的小数不是版本：1.5 秒 / 4.8 点 / 12.5% / 24 格 / 0.6 倍 等
            _vp = re.sub(r"\d+\.\d+(?=\s*(秒|分钟|刻|tick|点|格|%|倍|级|组|天|点伤害))", " ", _vp)
            for m in re.finditer(r"\b1\.\d{1,2}(?:\.\d{1,2})?\b", _vp):
                versions_in_body.add(m.group(0))
            plain = re.sub(r"<[^>]+>", "", html)
            plain = re.sub(r"[^。；<]*\[icon:[^\]]*\][^。；]*[。；]?", "", plain)
            plain = re.sub(r"\[icon:[^\]]*\]", "", plain)
            for pat, why in REDUNDANT:
                if re.search(pat, plain):
                    warns.append(f"[{r.get('name') or r.get('id')}] 多余描述：{why}")

    # ⑤ 正文里的版本号必须在证据表里出现过
    if versions_in_body and ev:
        claims = " ".join(c for c, _, _ in ev)
        for v in sorted(versions_in_body):
            if v not in claims:
                blocks.append(f"正文写了版本 {v}，但证据表里没有对应断言 —— 版本是猜的？")

    # 输出
    print("=" * 62)
    print(f"preflight · {d.name} · 类型 {a.type}")
    print("=" * 62)
    for s in infos:
        print(f"  · {s}")
    if warns:
        print("  ── 提醒 ──")
        for w in warns:
            print(f"  ! {w}")
    if blocks:
        print("  ── 阻断 ──")
        for b in blocks:
            print(f"  X {b}")
        print()
        print("  取当前指纹：python scripts/preflight.py . --print-sha")
    print()
    print(f"重跑：python scripts/preflight.py \"{d}\" --type {a.type}")
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
