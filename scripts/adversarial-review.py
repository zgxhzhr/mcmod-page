#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""adversarial-review.py — 第 4 层：另一个模型逐句判「有没有源码依据」

它不看我们的写作意图，只拿「正文句子 + 事实摘要」判断 supported / unsupported / uncertain。
默认只审 游戏设定（概念页）与含数字的条目，控制成本。

用法：
  python adversarial-review.py --json 交付.json --facts facts.json --out review.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import importlib.util


def load_oc():
    spec = importlib.util.spec_from_file_location("oc", SKILL / "scripts" / "oc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TAG = re.compile(r"<[^>]+>")


def sentences(html):
    # 表格内容（含「语言文件原文」的表）由 claim-check 做字符串比对，不交给模型判
    stripped = re.sub(r"<table[\s\S]*?</table>", " ", html)
    txt = TAG.sub(" ", re.sub(r"\[icon:[^\]]*\]", " ", stripped))
    return [s.strip() for s in re.split(r"(?<=[。；！？])", txt) if len(s.strip()) >= 6]


def facts_digest(facts):
    pools = "\n".join(f"- {k}: {', '.join(v)}" for k, v in list(facts.get("pools", {}).items())[:12])
    keep = re.compile(r"Roster|Battle|Truce|EventHandler|Warlord|Troop|Config", re.I)
    consts = []
    for cls, info in list(facts.get("classes", {}).items()):
        if not keep.search(cls):
            continue
        for k, v in list((info or {}).get("constants", {}).items())[:40]:
            consts.append(f"- {cls}.{k} = {v}")
    ents = ", ".join(list(facts.get("entities", {}).keys()))
    nums = " ".join(str(x) for x in facts.get("numbers", [])[:600])
    body = "\n".join(consts[:400])
    return (f"## 分组/池\n{pools}\n\n## 常量\n{body}\n\n## 实体注册名\n{ents}\n"
            f"\n## 源码中的数值字面量（内联常量也算有据）\n{nums}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--facts", required=True)
    ap.add_argument("--out", default="review.json")
    ap.add_argument("--model", default="")
    ap.add_argument("--max-sentences", type=int, default=60)
    a = ap.parse_args()

    rows = json.loads(Path(a.json).read_text(encoding="utf-8"))
    facts = json.loads(Path(a.facts).read_text(encoding="utf-8"))

    picked = []
    for r in rows:
        if not r.get("html"):
            continue
        if r.get("type") != "游戏设定" and not re.search(r"\d", TAG.sub("", r["html"])):
            continue
        for s in sentences(r["html"]):
            picked.append({"page": r.get("name"), "sentence": s})
    picked = picked[: a.max_sentences]

    body = "\n".join(f"{i+1}. [{p['page']}] {p['sentence']}" for i, p in enumerate(picked))
    prompt = f"""你是一名严格的事实核查员。下面是一份 Minecraft 模组百科页面的句子，
以及该模组反编译源码里的事实摘要（分组/池、常量、实体注册名）。

请逐句判断：这句话能不能被给定的事实摘要或常识层面的原版机制支撑。
- supported：摘要里能找到直接依据（给出常量名或池名）
- unsupported：摘要里找不到依据（很可能是编造的）
- uncertain：无法判断（需要更多源码）

**不要评价文风，不要改写句子，不要补充事实。** 只做判定。

注意两条「有据」规则，避免误报：
1. 数值只要是「源码中的数值字面量」里出现过的，就算有据（可能是内联常量，没有 static final 名字）；
2. 移动速度、体型宽高、生命值、攻击伤害等属性来自游戏内导出，属有据；除非与摘要明显冲突。

输出 JSON 数组，每项 {{"id": 编号, "verdict": "supported|unsupported|uncertain", "evidence": "依据或原因"}}，不要任何其它文字。

## 待判句子
{body}

## 事实摘要
{facts_digest(facts)}
"""
    pf = Path(a.out).with_suffix(".prompt.md")
    pf.write_text(prompt, encoding="utf-8")

    oc = load_oc()
    kwargs = {"prompt_file": pf, "cwd": Path(a.out).parent, "timeout": 900}
    kwargs["model"] = a.model or getattr(oc, "DEFAULT_MODEL", "opencode/deepseek-v4.1-flash-free")
    res = oc.run(**kwargs)
    answer = res.get("answer", "") if isinstance(res, dict) else str(res)
    verdicts = []
    i = answer.find("[")
    while i >= 0 and not verdicts:
        try:
            verdicts, _ = json.JSONDecoder().raw_decode(answer[i:])
        except Exception:
            i = answer.find("[", i + 1)
    if isinstance(verdicts, dict):
        verdicts = verdicts.get("verdicts", [])
    if not verdicts:
        print("模型未返回可解析的 JSON，原文：\n", answer[:800])
        return 2

    bad = [v for v in verdicts if str(v.get("verdict")) == "unsupported"]
    unc = [v for v in verdicts if str(v.get("verdict")) == "uncertain"]
    print(f"复核 {len(verdicts)} 句：supported {len(verdicts)-len(bad)-len(unc)} · unsupported {len(bad)} · uncertain {len(unc)}")
    for v in bad:
        i = int(v.get("id", 0)) - 1
        src = picked[i] if 0 <= i < len(picked) else {}
        print(f"  ✗ [{src.get('page')}] {src.get('sentence','')[:60]} —— {v.get('evidence','')[:60]}")
    Path(a.out).write_text(json.dumps({"verdicts": verdicts}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
