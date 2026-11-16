#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""难样本评测：用 base 模型容易失败的输入，测训练是否真的带来改进。

测什么
------
1. **信息保真**：原文里的数值/专有名词，输出是否全部保留（最硬指标）
2. **去 AI 味**：套话词数（值得注意的是/无疑/体现了…）
3. **主站规范**：emoji、堆叠标点、PS/注 前后缀
4. **长度守恒**：输出不该比原文缩水太多（缩水=丢信息）

为什么要难样本
--------------
普通 AI 味文本 base 模型就能改好（上一轮验证过），看不出训练价值。
这里用**注入强度 1.0 的极端 AI 味 + 长文本**，逼出模型能力边界。

用法
----
    python eval-hard.py --lora 训练产物目录 [--n 8] [--model 模型路径]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

DATA = Path(r"E:\Mod\百科-语料")
SCRIPT_DIR = Path(__file__).parent

CUES = ["值得注意的是", "值得一提的是", "从某种角度", "从某种意义上", "总的来说",
        "可以说", "不难发现", "与此同时", "在此基础上", "更进一步", "无疑",
        "彰显", "体现了", "不可多得", "一大亮点", "更加流畅自然", "值得玩家慢慢体会",
        "的整体表现", "完善的", "强大的", "丰富的"]
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
STACKED = re.compile(r"[！？。]{2,}")


def load_injector():
    spec = importlib.util.spec_from_file_location("inj", SCRIPT_DIR / "ai-tell-inject.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def numbers_and_terms(text: str) -> set[str]:
    """提取需要保真的信息：数字、带单位数值、英文专名。"""
    nums = set(re.findall(r"\d+(?:\.\d+)?", text))
    terms = set(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text))
    return {x for x in nums | terms if len(x) >= 1}


def score_output(out: str, ref: str) -> dict:
    """三条硬指标 + 两条软指标。"""
    out_nums = numbers_and_terms(out)
    ref_nums = numbers_and_terms(ref)
    keep = len(out_nums & ref_nums) / max(len(ref_nums), 1)

    cues = sum(out.count(c) for c in CUES)
    emoji = len(EMOJI.findall(out))
    stacked = len(STACKED.findall(out))
    ratio = len(out) / max(len(ref), 1)

    return {
        "info_keep": round(keep, 3),      # 信息保留率（越高越好，1.0=全保留）
        "cues": cues,                      # 套话数（0 最好）
        "emoji": emoji,                    # emoji（0 最好）
        "stacked": stacked,                # 堆叠标点（0 最好）
        "len_ratio": round(ratio, 3),      # 长度比（0.7-1.3 合理，太低=丢信息）
        "chars": len(out),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(DATA / "train/models/Qwen2.5-0.5B-Instruct"))
    ap.add_argument("--lora", default="", help="训练产物目录；空=只测 base")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--max-new", type=int, default=700)
    ap.add_argument("--strength", type=float, default=1.0)
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    inj = load_injector()
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # 大模型自动 4bit，小模型 fp16
    import re as _re
    is_big = any(k in str(args.model).lower() for k in ["1b", "3b", "7b", "8b", "13b", "14b", "32b"])
    kwargs = {"device_map": "cuda:0", "trust_remote_code": True}
    if is_big:
        try:
            import bitsandbytes  # noqa
            from transformers import BitsAndBytesConfig
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4")
            print("  大模型 → 4bit 量化加载")
        except ImportError:
            kwargs["torch_dtype"] = torch.float16
            print("  ⚠ 未装 bitsandbytes，用 fp16（可能 OOM）")
    else:
        kwargs["torch_dtype"] = torch.float16
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    model.eval()
    tag = "base"
    if args.lora:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.lora)
        model.eval()
        tag = "trained"

    # 挑长文本（800-2000 字），这类最能暴露改写能力
    import sqlite3
    con = sqlite3.connect(f"file:{DATA/'mcmod.db'}?mode=ro", uri=True)
    # 固定样本清单：保证不同模型测同一批（避免随机波动）
    fixed = DATA / "train" / "eval-ids.json"
    if fixed.exists():
        ids = json.loads(fixed.read_text(encoding="utf-8"))
        ph = ",".join("?" * len(ids))
        got = {r[0]: r for r in con.execute(
            f"SELECT id,name,intro_text FROM classes WHERE id IN ({ph})", (*ids,))}
        rows = [got[i] for i in ids if i in got]
    else:
        rows = list(con.execute(
            "SELECT id,name,intro_text FROM classes WHERE chars BETWEEN 800 AND 2000 "
            "ORDER BY id DESC LIMIT 400"))[: args.n]
        fixed.write_text(json.dumps([r[0] for r in rows]), encoding="utf-8")
        print(f"已固化 {len(rows)} 条评测样本 → {fixed}")
    con.close()

    INSTR = ("你是 MC百科（mcmod.cn）的编辑。请按主站编辑规范改写下面这段模组介绍。\n"
             "保留全部数值、名称、机制与获取方式，去掉套话与营销腔，只输出正文。\n\n待改写：\n")

    results = []
    print(f"模型：{tag}  样本数：{len(rows)}  注入强度：{args.strength}\n")
    for cid, name, body in rows:
        if not body or len(body) < 400:
            continue
        poisoned = inj.inject(body, args.strength, seed=cid)
        prompt = INSTR + poisoned
        text = tok.apply_chat_template([{"role": "user", "content": prompt}],
                                       tokenize=False, add_generation_prompt=True)
        ids = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=args.max_new,
                                 do_sample=False, pad_token_id=tok.pad_token_id)
        gen = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()

        # 基准：用真实正文作为参考（它才是"应该还原成什么"）
        sc = score_output(gen, body)
        sc["id"] = cid
        sc["name"] = name
        results.append(sc)
        print(f"  id={cid} {str(name)[:16]:<18} 保留率 {sc['info_keep']:.2f}  "
              f"套话 {sc['cues']:>2}  emoji {sc['emoji']}  堆叠 {sc['stacked']}  "
              f"长度比 {sc['len_ratio']:.2f}")

    if results:
        avg = lambda k: sum(r[k] for r in results) / len(results)
        print(f"\n=== {tag} 汇总 ===")
        print(f"  信息保留率 {avg('info_keep'):.3f}")
        print(f"  套话均数 {avg('cues'):.2f}")
        print(f"  emoji 均数 {avg('emoji'):.2f}")
        print(f"  堆叠标点 {avg('stacked'):.2f}")
        print(f"  长度比 {avg('len_ratio'):.2f}")
        out_file = DATA / "train" / f"eval-{tag}.json"
        out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  明细：{out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
