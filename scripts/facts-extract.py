#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""facts-extract.py — 写页之前先把 jar 的事实抽成表（开卷写作的第 1 层）

产出 facts.json，包含：
  · lang      全部语言条目（json 与 .lang 两种格式）
  · classes   每个类的父类 + 全部 static final 常量（名字与值）
  · entities  注册名 → 中英名（从 lang 的 entity.<ns>.<id> 反推）
  · pools     分组/池类（类名含 Roster/Pool/Group/Faction/Horde）里的 List.of 成员
  · numbers   源码中出现的全部数值字面量（给 claim-check 交叉引用）

用法：
  python facts-extract.py --jar <mod.jar> --src <反编译目录> --out facts.json
"""
import argparse
import json
import re
from pathlib import Path

CONST_RE = re.compile(r"(?:static final|private static final|public static final)\s+[\w<>\[\], ?]+\s+(\w+)\s*=\s*([^;]{1,80});")
CLASS_RE = re.compile(r"class\s+(\w+)(?:<[^>]*>)?\s+extends\s+([\w.<>]+)")
LIST_RE = re.compile(r"List\.of\(([^)]{1,900})\)")
NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def read_lang(jar_path: Path):
    import zipfile
    out = {}
    z = zipfile.ZipFile(jar_path)
    for n in z.namelist():
        if "/lang/" not in n:
            continue
        try:
            body = z.read(n).decode("utf-8", errors="replace")
        except Exception:
            continue
        if n.endswith(".lang"):
            for line in body.splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    out.setdefault(k.strip(), v.strip())
        elif n.endswith(".json"):
            try:
                d = json.loads(body)
            except Exception:
                continue
            for k, v in d.items():
                if isinstance(v, str):
                    out.setdefault(k, v)
    return out


def read_sources(src: Path):
    classes, pools, numbers = {}, {}, set()
    for p in src.rglob("*.java"):
        t = p.read_text(encoding="utf-8", errors="replace")
        numbers.update(NUM_RE.findall(t))
        name = p.stem
        cm = CLASS_RE.search(t)
        consts = {}
        for m in CONST_RE.finditer(t):
            consts[m.group(1)] = m.group(2).strip()[:60]
        if consts or cm:
            classes[name] = {"extends": (cm.group(2) if cm else ""), "constants": consts}
        # 池：按「常量名 = List.of(...)」逐条拆开，避免一个类的多个池混在一起
        for m in re.finditer(r"(\w+)\s*=\s*List\.of\(([^)]{1,900})\)", t):
            cname, body = m.group(1), m.group(2)
            members = []
            for tok in re.findall(r"[A-Z][A-Z0-9_]{2,}", body):
                if tok not in members:
                    members.append(tok)
            if members and re.search(r"Roster|Pool|Group|Faction|Horde|Troop", name):
                pools[f"{name}.{cname}"] = members
    return classes, pools, numbers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default="facts.json")
    a = ap.parse_args()

    lang = read_lang(Path(a.jar))
    classes, pools, numbers = read_sources(Path(a.src))

    ents = {}
    for k, v in lang.items():
        m = re.fullmatch(r"entity\.([\w]+)\.([\w]+)", k)
        if m:
            ns, eid = m.group(1), m.group(2)
            e = ents.setdefault(eid, {"ns": ns, "names": []})
            if v not in e["names"]:
                e["names"].append(v)

    facts = {
        "jar": Path(a.jar).name,
        "lang_entries": len(lang),
        "entities": dict(sorted(ents.items())),
        "pools": pools,
        "classes": classes,
        "numbers": sorted(numbers),
    }
    Path(a.out).write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {a.out}")
    print(f"  语言条目 {len(lang)} · 实体 {len(ents)} · 池/分组类 {len(pools)} · 类 {len(classes)} · 数字 {len(numbers)}")
    for name, members in list(pools.items())[:5]:
        print(f"    {name}: {', '.join(members[:8])}{' …' if len(members) > 8 else ''}")


if __name__ == "__main__":
    main()
