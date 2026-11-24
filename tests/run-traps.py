#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run-traps.py — 防幻觉闸门的回归用例

每个 trap 都是「曾经真实犯过的错」或「必须放行的正确写法」：
  · fabricated_numbers  编造概率（12.5%）
  · invented_faction    自造建制词（舰队）
  · ledge_mismatch      台账数字与实际常量不符
  · 对照组             正确写法必须 PASS，避免闸门过严

用法： python tests/run-traps.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
CHECK = SKILL / "scripts" / "claim-check.py"
SRC = HERE / "fixtures" / "src"


def run(args):
    p = subprocess.run([sys.executable, str(CHECK)] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout


def main():
    traps = json.loads((HERE / "traps.json").read_text(encoding="utf-8"))
    ok = 0
    for t in traps:
        name, expect = t["name"], t["expect"]
        base = ["--src", str(SRC)]
        if t.get("html"):
            f = HERE / f"{name}.html"
            f.write_text(t["html"], encoding="utf-8")
            base += ["--html", str(f)]
        else:
            f = HERE / f"{name}.json"
            f.write_text(json.dumps(t["rows"], ensure_ascii=False), encoding="utf-8")
            base += ["--json", str(f)]
        if t.get("claims"):
            cf = HERE / f"{name}-claims.json"
            cf.write_text(json.dumps(t["claims"], ensure_ascii=False), encoding="utf-8")
            base += ["--claims", str(cf)]
        if t.get("facts"):
            base += ["--facts", t["facts"]]
        code, out = run(base)
        got = "PASS" if code == 0 else "FAIL"
        good = got == expect
        ok += 1 if good else 0
        print(f"{'✓' if good else '✗'} {name:<24} 期望 {expect} 实得 {got}")
        if not good:
            for line in out.splitlines()[:6]:
                print("     ", line)
    print(f"\n{ok}/{len(traps)} 通过")
    return 0 if ok == len(traps) else 1


if __name__ == "__main__":
    sys.exit(main())
