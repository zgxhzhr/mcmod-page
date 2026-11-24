#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""claim-check.py — 断言溯源检查（防幻觉的机械化闸门）

思路：正文里的**数字**和**阵营/势力词**，必须能在反编译源码或语言文件里找到出处。
找不到 → 阻断。不判断「说得对不对」，只判断「有没有据」——把编造挡在提交之前。

用法：
  python claim-check.py --json 交付.json --src <反编译目录> [--lang-jar <jar>]
  python claim-check.py --html 页面.html --src ... [--lang-jar ...]     # 单文件

检查规则（可被 --allow 覆盖）：
  1. 数字：正文出现的每个数值，必须作为字面量出现在源码或语言文件里
     · 忽略 [icon:...] 标记内的数字
     · 允许 1/2/3/4/8/13 这类"计数用"小数字吗？——不默认放行，全查；
       确属修辞（"两条线"）的，加 --allow 12,3...
  2. 阵营词：亡灵|不死|大军|军团|教团|部族|舰队|阵营|势力|派系 等，
     必须出现在语言文件文本、类名或源码字符串里
"""
import argparse
import json
import re
import sys
from pathlib import Path

NUM_RE = re.compile(r"\d+(?:\.\d+)?")
ICON_RE = re.compile(r"\[icon:[^\]]*\]")
TAG_RE = re.compile(r"<[^>]+>")

_LIVE_SRC = {}
FACTION_WORDS = ["亡灵", "不死", "大军", "军团", "教团", "部族", "舰队", "阵营", "势力", "派系", "部落"]


def collect_sources(src_dir: Path):
    nums, texts = set(), []
    for p in src_dir.rglob("*.java"):
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in NUM_RE.finditer(t):
            nums.add(m.group(0))
        texts.append(t)
    return nums, "\n".join(texts)


def collect_lang(jar_path: Path):
    import zipfile
    nums, blob = set(), []
    try:
        z = zipfile.ZipFile(jar_path)
    except Exception:
        return nums, ""
    for n in z.namelist():
        if n.endswith(".lang") and "/lang/" in n:
            try:
                body = z.read(n).decode("utf-8", errors="replace")
            except Exception:
                continue
            for line in body.splitlines():
                if "=" in line:
                    v = line.split("=", 1)[1]
                    blob.append(v)
                    nums.update(NUM_RE.findall(v))
            continue
        if n.endswith(".json") and "/lang/" in n:
            try:
                d = json.loads(z.read(n).decode("utf-8", errors="replace"))
            except Exception:
                continue
            for k, v in d.items():
                if isinstance(v, str):
                    blob.append(v)
                    nums.update(NUM_RE.findall(v))
    return nums, "\n".join(blob)


def sentences(html: str):
    txt = TAG_RE.sub(" ", ICON_RE.sub(" ", html))
    return [s.strip() for s in re.split(r"(?<=[。；！？])", txt) if s.strip()]


def check(rows, src_nums, src_text, lang_nums, lang_text, allow_nums):
    problems = []
    for r in rows:
        html = r.get("html") or ""
        if not html:
            continue
        for s in sentences(html):
            # ① 数字
            for num in NUM_RE.findall(s):
                if num in allow_nums:
                    continue
                ok = num in src_nums or num in lang_nums or (float(num) if "." in num else int(num)) in {float(x) for x in src_nums if re.fullmatch(r"\d+(\.\d+)?", x)}
                if not ok:
                    problems.append({"page": r.get("name"), "kind": "数字无出处", "token": num, "sentence": s[:80]})
            # ② 阵营词
            for w in FACTION_WORDS:
                if w in s and w not in lang_text and w not in src_text:
                    problems.append({"page": r.get("name"), "kind": "阵营词无出处", "token": w, "sentence": s[:80]})

        # ③ 语言文件原文核验：页面声称「语言文件原文」时，表格单元格必须真能在 lang 里找到
        if "语言文件原文" in html and (lang_text or src_text):
            blob = re.sub(r"\s+", "", lang_text + src_text)
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", html, re.S):
                txt = re.sub(r"<[^>]+>", "", cell)
                txt = re.sub(r"\s+", "", txt)
                if len(txt) < 6 or txt in ("对应单位", "风味文本"):
                    continue
                if txt not in blob:
                    problems.append({"page": r.get("name"), "kind": "语言文件原文查无此句",
                                     "token": txt[:24], "sentence": txt[:80]})

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--html")
    ap.add_argument("--src", required=True)
    ap.add_argument("--lang-jar")
    ap.add_argument("--allow", default="", help="逗号分隔的放行数字，如 2,3")
    ap.add_argument("--facts", default="", help="逗号分隔的导出/测量数据 JSON（其中的数字视为有据）")
    ap.add_argument("--claims", default="", help="断言台账 JSON：[{match, class, constant, value}]，逐条核到类.常量=值")
    ap.add_argument("--liveness", default="", help="liveness.json（liveness.py 产出）：用于验证方法是否被活类调用")
    a = ap.parse_args()

    src_dir = Path(a.src)
    if not src_dir.exists():
        print(f"源码目录不存在: {src_dir}", file=sys.stderr)
        return 2
    src_nums, src_text = collect_sources(src_dir)
    global _LIVE_SRC
    _LIVE_SRC = {q.stem: q.read_text(encoding="utf-8", errors="replace") for q in src_dir.rglob("*.java")}
    lang_nums, lang_text = set(), ""
    if a.lang_jar:
        lang_nums, lang_text = collect_lang(Path(a.lang_jar))

    if a.json:
        rows = json.loads(Path(a.json).read_text(encoding="utf-8"))
        if isinstance(rows, dict):
            rows = rows.get("rows", [])
    else:
        html = Path(a.html).read_text(encoding="utf-8")
        rows = [{"name": Path(a.html).stem, "html": html}]

    allow = {x.strip() for x in a.allow.split(",") if x.strip()}
    if a.facts:
        for f in [x.strip() for x in a.facts.split(",") if x.strip()]:
            try:
                blob = Path(f).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if f.endswith(".jsonl"):
                allow.update(re.findall(r"\d+(?:\.\d+)?", blob))
            else:
                allow.update(NUM_RE.findall(blob))
    problems = check(rows, src_nums, src_text, lang_nums, lang_text, allow)

    # 断言台账：每条 claim 必须 (a) 正文出现该说法 (b) 源码里该类确实有该常量=该值
    live = set()
    if a.liveness:
        try:
            live = set(json.loads(Path(a.liveness).read_text(encoding="utf-8")).get("live", []))
        except Exception:
            live = set()

    ledger = []
    if a.claims:
        try:
            ledger = json.loads(Path(a.claims).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"台账读取失败: {e}", file=sys.stderr)
            ledger = []
        body_all = "\n".join((r.get("html") or "") for r in rows)
        for cl in ledger:
            m = cl.get("match", "")
            cls, const, val = cl.get("class"), cl.get("constant"), cl.get("value")
            if m and m not in body_all:
                problems.append({"page": "(台账)", "kind": "台账说法未出现在正文", "token": m, "sentence": ""})
                continue
            f = src_dir / (cls + ".java") if cls else None
            if not f or not f.exists():
                cand = list(src_dir.rglob(cls + ".java")) if cls else []
                f = cand[0] if cand else None
            if not f:
                problems.append({"page": "(台账)", "kind": "台账类找不到", "token": f"{cls}", "sentence": m})
                continue
            src = f.read_text(encoding="utf-8", errors="replace")
            pat = re.escape(str(const)) + r"\s*=\s*" + re.escape(str(val))
            if not re.search(pat, src):
                problems.append({"page": "(台账)", "kind": "台账常量值不符",
                                 "token": f"{cls}.{const} 应为 {val}", "sentence": m})
            # 方法级：字面量必须出现在该方法体里，且该方法被活类调用
            meth, lit = cl.get("method"), cl.get("literal", val)
            if meth:
                mm = re.search(r"(?:public|private|protected|static)[\w<>\[\], ?]*\s+"
                               + re.escape(meth) + r"\s*\([^)]*\)\s*\{", src)
                if not mm:
                    problems.append({"page": "(台账)", "kind": "台账方法不存在",
                                     "token": f"{cls}.{meth}", "sentence": m})
                else:
                    # 粗略取该方法体：从 {(位置) 到下一个同缩进 }
                    body = src[mm.end(): mm.end() + 4000]
                    depth, end = 1, 0
                    for i, ch in enumerate(body):
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                end = i
                                break
                    body = body[:end]
                    if re.escape(str(lit)) and not re.search(r"(?<![\d.])" + re.escape(str(lit)) + r"(?![\d.])", body):
                        problems.append({"page": "(台账)", "kind": "字面量不在该方法内",
                                         "token": f"{cls}.{meth} 未见 {lit}", "sentence": m})
                    if live and not any(re.search(r"\b" + re.escape(meth) + r"\s*\(", tx)
                                        for name, tx in _LIVE_SRC.items()
                                        if name == cls or name in live):
                        problems.append({"page": "(台账)", "kind": "该方法未被任何活类调用（疑似死代码）",
                                         "token": f"{cls}.{meth}", "sentence": m})

    print(f"源码数字字面量 {len(src_nums)} 个 · 语言文件数字 {len(lang_nums)} 个 · 检查 {len(rows)} 行")
    if not problems:
        print("✓ 全部断言可溯源")
        return 0
    for p in problems[:40]:
        print(f"  ✗ [{p['page']}] {p['kind']}: {p['token']} — {p['sentence']}")
    print(f"\n共 {len(problems)} 处无出处")
    return 1


if __name__ == "__main__":
    sys.exit(main())
