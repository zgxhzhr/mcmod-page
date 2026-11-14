#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资料页 JSON 的交付强自检（SKILL §5.8.3）。

不抽样：把每条资料的全部字段 dump 出来、逐项校验，跑完给 PASS / FAIL 汇总。
阻断项（BLOCK）非零即退出码 1，不允许"带病交付"。

用法：
    python audit-delivery.py 资料页.json
    python audit-delivery.py 资料页.json --intro 介绍页.html --dump
    python audit-delivery.py 资料页.json --json-only        # 只看机器结论

检查项：
    1. 字段：白名单（id/name/ename/regname/category/type/maxstack/damage/html/icon32/icon128/remark，remark 选填）
    2. 附言（**选填**；填了才检查）：结尾「辛苦…机了」、相邻条目不重复、无取证手段词、无括号注释
    3. 正文：非空、<p> 闭合、汉字句长 ≤ 40、无「§」占位符残留
    4. 图标：icon32/icon128 必须是 PNG base64（裸 base64 或带 data: 前缀都接受——rules/04:193 要求裸的）
    5. 断言黑名单（历史上被证伪的说法，只增不减）
    6. 重复度：跨条重复句、8-gram 最高重合，超 30% 提示合并/综合/通用文本
    7. 介绍页（可选）：与资料页同名数值是否一致、残留黑名单
"""
import argparse
import json
import re
import sys
from collections import Counter
from itertools import combinations

# ── 交付规范 ────────────────────────────────────────────────────────
# 与 rules/04 §6.5、rules/05 §6.6 和历史交付（857 条）一致：
#   · 没有 kind 字段
#   · remark 选填（用户可能要求不填）
#   · 图标裸 base64（不加 data: 前缀）
FIELD_ORDER = ["id", "name", "ename", "regname", "category", "type",
               "maxstack", "damage", "html", "icon32", "icon128", "remark"]

# 历史翻车词表，只增不减（每发现一次就加一条，并注明出事的模组 id）
BLACKLIST = [
    ("没有提供任何配方", "27991：实际 data/onatm/recipes 有 9 个配方"),
    ("没有提供合成配方", "27991：TNT Pick 有 tntpickr.json"),
    ("没有任何配方使用它", "27991：Living Metal 是 Experiment 45 的原料"),
    ("只能从创造模式", "27991：可合成，别写只能创造模式拿"),
    ("无限使用", "27991：durability(1) 是一次性"),
    ("不会提示", "25147：checkBlockArray 失败会生成 BLOCK_MARKER 粒子"),
    ("点燃周围方块", "20947：原版 PrimedTnt 的 explode 是 fire=false"),
    ("名称取自 lang", "25147：lang 里没有该键时这句话就是编"),
]

# 附言里不许出现的取证手段词（只写数据来源，不写怎么查到的）
FORBIDDEN_REMARK = ["反编译", "反混淆", "脚本导出", "抓包", "由我"]

END_RE = re.compile(r"辛苦([喵呜娘]+)机了。?$")  # rules/02 §6.2.3 含「喵娘」特例
SENT_SPLIT = re.compile(r"(?<=[。；])")
CJK = re.compile(r"[\u4e00-\u9fa5]")


def plain(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def grams(text: str, n: int = 8):
    t = re.sub(r"[^\u4e00-\u9fa5]", "", text)
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def audit_items(path):
    blocks, warns, infos = [], [], []
    data = json.load(open(path, encoding="utf-8"))
    infos.append(f"条目数 {len(data)}")

    if not isinstance(data, list) or not data:
        blocks.append("JSON 不是非空数组")

    prev_end = None
    sections = []          # (name, html, remark) 供重复度计算
    for idx, it in enumerate(data, 1):
        name = it.get("name", f"#{idx}")

        # 1) 字段顺序
        keys = list(it.keys())
        # 顺序只在「同时出现了白名单里靠前和靠后的字段」时提示，不阻断
        expect = [k for k in FIELD_ORDER if k in keys]
        if keys[:len(expect)] != expect:
            warns.append(f"[{name}] 字段顺序与惯例不同：{keys}")
        extra = [k for k in keys if k not in FIELD_ORDER]
        if extra:
            blocks.append(f"[{name}] 出现多余字段：{extra}")
        # 抽象资料（综合功能的父资料）：rules/05 §6.1.11 ——
        # 注册名与图标必须留空，正文写整套说明，是合法形态
        is_abstract = (not it.get("regname")) and (not it.get("icon32")) and bool(it.get("html"))
        if is_abstract:
            warns.append(f"[{name}] 按抽象资料处理（无注册名/无图标），确认这是综合用的父资料")
        for k in ("name", "regname", "category", "type", "remark"):
            if not it.get(k) and not is_abstract:
                blocks.append(f"[{name}] 字段 {k} 为空")
        if not it.get("icon32") and it.get("icon128"):
            warns.append(f"[{name}] 只给了大图标（icon32 为空）——批量脚本会勾「删除小图标」，确认是有意的")
        # 抽象资料/通用文本本来就没有图标（rules/04 §唯一例外），不按此判
        if (not it.get("icon32") and not it.get("icon128")
                and it.get("regname") and not is_abstract):
            blocks.append(f"[{name}] 大小图标都为空（真实物品/方块应至少给大图标）")

        if "ename" not in keys:
            warns.append(f"[{name}] 缺 ename 键（无中文时规则要求保留该键并留空）")

        # 2) 附言
        remark = it.get("remark", "")
        m = END_RE.search(remark) if remark else None
        if not remark:
            blocks.append(f"[{name}] 字段 remark 为空（附言必填，结尾写「辛苦…机了」）")
        elif not m:
            blocks.append(f"[{name}] 附言结尾不是「辛苦…机了」")
        elif m:
            if m.group(1) == prev_end:
                warns.append(f"[{name}] 附言结尾与上一条重复（{m.group(1)}）")
            prev_end = m.group(1)
        for w in FORBIDDEN_REMARK:
            if w in remark:
                blocks.append(f"[{name}] 附言出现取证手段词「{w}」")
        if remark.count("（") or remark.count("("):
            warns.append(f"[{name}] 附言含括号注释")

        # 3) 正文
        html = it.get("html", "")
        txt = plain(re.sub(r"<table[\s\S]*?</table>", "", html))
        if "§" in txt:
            blocks.append(f"[{name}] 正文残留 § 占位符")
        if not html:
            warns.append(f"[{name}] 正文为空（综合/合并的子资料属正常，见 rules/05 §6.1.10）")
        if html.count("<p>") != html.count("</p>"):
            blocks.append(f"[{name}] <p> 未闭合（{html.count('<p>')} 开 / {html.count('</p>')} 闭）")
        for s in SENT_SPLIT.split(txt):
            n = len(CJK.findall(s))
            if n > 40:
                blocks.append(f"[{name}] 句长 {n} 汉字超 40：{s.strip()[:30]}…")
        if txt.strip() and len(CJK.findall(txt)) < 60:
            warns.append(f"[{name}] 正文仅 {len(CJK.findall(txt))} 汉字，可能过薄")

        # 4) 图标
        for k in ("icon32", "icon128"):
            v = it.get(k, "")
            if not v:
                continue
            raw = v.split("base64,", 1)[1] if v.startswith("data:") else v
            try:
                import base64 as _b64
                head = _b64.b64decode(raw[:64] + "=" * (-len(raw[:64]) % 4))[:8]
                if head != b"\x89PNG\r\n\x1a\n":
                    blocks.append(f"[{name}] {k} 不是 PNG 数据")
            except Exception:
                blocks.append(f"[{name}] {k} base64 解码失败")

        # 5) 黑名单
        for word, why in BLACKLIST:
            if word in txt or word in remark:
                blocks.append(f"[{name}] 命中黑名单「{word}」——{why}")

        sections.append((name, txt, remark))

    # 5.5) 附言结尾变体：同批不能整批用同一个「辛苦 XXX 机了」（rules/02 §6.2.3）
    _tails = []
    for _it in data:
        _m = END_RE.search((_it.get("remark") or "").strip())
        if _m:
            _tails.append(_m.group(0).rstrip("。"))
    if len(_tails) >= 3 and len(set(_tails)) == 1:
        warns.append(f"本批 {len(_tails)} 条附言结尾完全相同（{_tails[0]}）——"
                     "rules/02 §6.2.3 要求同批轮换变体，整批一致像脚本生成")

    # 6) 重复度 → 合并 / 综合 / 通用文本 判定
    sents, per = [], {}
    for name, txt, _ in sections:
        ss = [s.strip() for s in SENT_SPLIT.split(txt) if len(s.strip()) >= 8]
        sents += [(name, s) for s in ss]
        per[name] = grams(txt)
    cnt = Counter(s for _, s in sents)
    dup = {s: k for s, k in cnt.items() if k > 1}
    total = sum(len(s) for _, s in sents) or 1
    dup_len = sum(len(s) * k for s, k in dup.items())
    ratio = dup_len / total * 100

    top, pair = 0.0, None
    for a, b in combinations(per, 2):
        if per[a] and per[b]:
            r = len(per[a] & per[b]) / min(len(per[a]), len(per[b]))
            if r > top:
                top, pair = r, (a, b)

    if ratio >= 30 or top >= 30:
        verdict = "超门槛：考虑 合并 / 综合 / 引用通用文本（见 §6.1.10）"
        warns.append(f"重复度 {ratio:.1f}% / 8-gram {top*100:.1f}% → {verdict}")
    else:
        verdict = "无需合并 / 综合 / 通用文本"
    infos.append(f"跨条重复句 {len(dup)} 句，可消除重复 {ratio:.1f}%")
    infos.append(f"8-gram 最高重合 {top*100:.1f}%" + (f"（{pair[0]} × {pair[1]}）" if pair else ""))
    infos.append(f"三类功能判定：{verdict}")

    return data, blocks, warns, infos, dup


def audit_intro(path, data):
    blocks, warns, infos = [], [], []
    html = open(path, encoding="utf-8").read()
    txt = plain(html)

    for word, why in BLACKLIST:
        if word in txt:
            blocks.append(f"[介绍页] 命中黑名单「{word}」——{why}")

    h1 = len(re.findall(r"\[h1=", html))
    heads = len(re.findall(r"\[h[12]=", html))
    infos.append(f"介绍页 {len(CJK.findall(txt))} 汉字，标题 {heads} 个（h1 {h1} 个）")
    if h1 != 1:
        warns.append(f"[介绍页] h1 数量为 {h1}，按 §6.2.2.35 只应有 1 个")

    # 数值一致性：资料页里出现的关键数值（威力/耐久/生命），看介绍页是否也提
    nums = set(re.findall(r"\d+\.\d+|\b\d{2,}\b", txt))
    watch = ("10000", "650")
    seen, missing = set(), []
    for it in data:
        for tok in re.findall(r"\d+\.\d+|\b\d{2,}\b", plain(it["html"])):
            if tok in watch and (it["name"], tok) not in seen:
                seen.add((it["name"], tok))
                missing.append((it["name"], tok, tok in nums))
    if missing:
        infos.append("关键数值在介绍页的呈现：" + "；".join(
            f"{n} {t}{'✓' if ok else '（未提，属正常取舍）'}" for n, t, ok in missing))

    return blocks, warns, infos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json", help="资料页 JSON")
    ap.add_argument("--intro", help="介绍页 HTML，一并检查")
    ap.add_argument("--dump", action="store_true", help="全字段 dump（逐条人工复核用）")
    ap.add_argument("--json-only", action="store_true", help="只输出结论，不 dump")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    data, blocks, warns, infos, dup = audit_items(a.json)
    if a.intro:
        b2, w2, i2 = audit_intro(a.intro, data)
        blocks += b2
        warns += w2
        infos += i2

    if a.dump and not a.json_only:
        print("=" * 70)
        print("全字段 dump（逐条核对 regname / category / type / maxstack / damage / 附言来源）")
        for it in data:
            meta = {k: v for k, v in it.items() if k not in ("html", "icon32", "icon128", "remark")}
            print("-" * 70)
            print(meta)
            print(plain(it["html"]).replace("。", "。\n"))
            print("附言:", it["remark"])

    print("\n" + "=" * 70)
    print("强自检结果")
    print("=" * 70)
    for i in infos:
        print("  ·", i)
    if dup:
        print("\n  跨条重复句（可作为通用文本候选）：")
        for s, k in list(dup.items())[:10]:
            print(f"    ×{k} {s}")
    if warns:
        print(f"\n  提醒 {len(warns)} 条：")
        for w in warns:
            print("    !", w)
    if blocks:
        print(f"\n  阻断 {len(blocks)} 条（必须改完再交付）：")
        for x in blocks:
            print("    X", x)
        print("\n结论：FAIL")
        return 1
    print("\n结论：PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
