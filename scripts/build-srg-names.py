#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 Forge 的 joined.tsrg（obf→SRG）与 Mojang 官方 client.txt（obf→官方名）
用 obf 名桥接，生成离线可查的 SRG→官方名对照表。

为什么要这一步：Forge 1.17+ 用 Mojang 官方映射，`javap` 反编译 jar 看到的是
SRG 名（`f_19612_`、`m_41486_`），mcp_config 里的 joined.tsrg 只给 obf→SRG，
两张表都不含人类可读名，必须 join 一次才能回答「这个 SRG 到底是饥饿还是反胃」。

用法：
    python scripts/build-srg-names.py \
        --tsrg refs/joined-1.20.1.tsrg \
        --client refs/client-1.20.1.txt \
        --out refs/srg-names-1.20.1.tsv

输出 TSV 三列：srg \\t official \\t owner（官方类名）
字段与方法分开输出；同一 obf 名在字段/方法间撞车时各出一行，查询时按需筛。

之后查名字：
    grep -P "^f_19612_\\t" refs/srg-names-1.20.1.tsv
"""
import argparse
import sys


def parse_tsrg(path):
    """返回 {(class_obf, member_obf): srg} 与 {class_obf: class_srg}。

    tsrg2 格式：类行 'obf srg id'，成员行以单个 tab 开头，
    更深缩进的参数行忽略。
    """
    members = []
    classes = {}
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if not line.startswith("\t"):
                parts = line.split()
                if len(parts) >= 2:
                    cur = parts[0]
                    classes[cur] = parts[1]
            elif line.startswith("\t\t"):
                # 参数行，跳过
                continue
            else:
                parts = line.strip().split()
                if not cur:
                    continue
                # 字段行：obf srg id（3 段）
                # 方法行：obf 描述符 srg id（4 段，描述符在第 2 列）
                if len(parts) == 3:
                    members.append((cur, parts[0], parts[1], "field", None))
                elif len(parts) >= 4:
                    members.append((cur, parts[0], parts[2], "method", parts[1]))
    return classes, members


def parse_proguard(path):
    """返回 {class_obf: (class_official, {member_obf: [(official_name, kind)]})}。"""
    out = {}
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            if line.startswith("    "):
                if cur is None:
                    continue
                body = line.strip()
                if "->" not in body:
                    continue
                left, obf = body.rsplit("->", 1)
                obf = obf.strip()
                left = left.strip()
                is_method = "(" in left
                # 去掉方法前的 "行号:行号:" 前缀
                if is_method and left[:1].isdigit():
                    left = left.split(":", 2)[-1].strip()
                name = left.split("(")[0].rsplit(" ", 1)[-1].strip()
                out[cur][1].setdefault(obf, []).append(
                    (name, "method" if is_method else "field", left)
                )
            else:
                if "->" not in line:
                    continue
                left, obf = line.rstrip(":").rsplit("->", 1)
                obf = obf.strip().rstrip(":")
                official = left.strip()
                cur = obf
                out[cur] = (official, {})
    return out


def desc_param_kinds(desc):
    """从 JVM 描述符 '(' 后解析参数，返回 ('prim'|'obj', ...) 元组。

    javap 里同名重载全靠这个区分：stacksTo(int) 与 food(FoodProperties)
    在官方映射里混淆名都是 'a'，只有参数类型能把它们分开。
    """
    if not desc.startswith("("):
        return None
    body = desc[1:].split(")")[0]
    kinds = []
    i = 0
    while i < len(body):
        c = body[i]
        if c == "[":
            i += 1
            continue
        if c == "L":
            j = body.find(";", i)
            if j < 0:
                break
            kinds.append("obj")
            i = j + 1
            continue
        kinds.append("prim")
        i += 1
    return tuple(kinds)


def sig_param_kinds(sig):
    """从官方签名 'ret name(int, Foo)' 取参数类型粗分类。"""
    if "(" not in sig:
        return None
    if sig[:1].isdigit():
        sig = sig.split(":", 2)[-1]
    inner = sig.split("(", 1)[1].rsplit(")", 1)[0].strip()
    if not inner:
        return ()
    prims = {"int", "long", "float", "double", "boolean", "byte", "char", "short"}
    kinds = []
    for part in inner.split(","):
        part = part.strip()
        kinds.append("prim" if part in prims else "obj")
    return tuple(kinds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsrg", required=True)
    ap.add_argument("--client", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    classes, members = parse_tsrg(args.tsrg)
    official = parse_proguard(args.client)

    # 类映射：SRG 类名 → 官方类名
    cls_rows = []
    for obf, srg in classes.items():
        if obf in official:
            cls_rows.append((srg, official[obf][0]))

    # 成员映射
    mem_rows = []
    miss = 0
    for cls_obf, mem_obf, srg, kind, desc in members:
        info = official.get(cls_obf)
        if not info:
            miss += 1
            continue
        cls_official, mems = info
        cands = mems.get(mem_obf)
        if not cands:
            miss += 1
            continue
        want = desc_param_kinds(desc) if desc else None
        hits = []
        for name, cand_kind, sig in cands:
            if cand_kind != kind:
                continue
            if want is not None:
                got = sig_param_kinds(sig)
                if got is not None and got != want:
                    continue
            hits.append(name)
        if not hits:
            miss += 1
            continue
        for name in hits:
            mem_rows.append((srg, name, cls_official))

    seen = set()
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("# srg\tofficial\towner\n")
        for srg, name in cls_rows:
            owner = name.rsplit(".", 1)[0] if "." in name else "-"
            key = (srg, name, owner)
            if key in seen:
                continue
            seen.add(key)
            f.write(f"{srg}\t{name}\t{owner}\n")
        for srg, name, owner in mem_rows:
            key = (srg, name, owner)
            if key in seen:
                continue
            seen.add(key)
            f.write(f"{srg}\t{name}\t{owner}\n")

    print(f"类 {len(cls_rows)} 条，成员 {len(mem_rows)} 条，未匹配 {miss} 条 → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
