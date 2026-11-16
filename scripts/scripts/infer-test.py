#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训练效果测试：用 AI 味文本喂给 base 模型和训练后模型，对比输出。

用法
----
    python infer-test.py                    # 用测试集前 3 条
    python infer-test.py --n 5              # 前 5 条
    python infer-test.py --id 25177         # 指定语料 id
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

DATA = Path(r"E:\Mod\百科-语料")
MODEL_BASE = DATA / "train" / "models" / "Qwen2.5-0.5B-Instruct"
LORA = DATA / "train" / "run-sft" / "final"


def gen(model, tok, prompt: str, max_new: int = 512) -> str:
    import torch
    msgs = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=max_new, do_sample=False,
                             temperature=None, top_p=None, pad_token_id=tok.pad_token_id)
    return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--id", type=int, default=0)
    ap.add_argument("--max-new", type=int, default=512)
    ap.add_argument("--lora", default=str(LORA))
    args = ap.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"CUDA {torch.cuda.is_available()}")
    tok = AutoTokenizer.from_pretrained(str(MODEL_BASE), trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        str(MODEL_BASE), torch_dtype=torch.float16, device_map="cuda:0")
    base.eval()

    samples = []
    if args.id:
        import sqlite3
        con = sqlite3.connect(f"file:{DATA/'mcmod.db'}?mode=ro", uri=True)
        r = con.execute("SELECT id,name,intro_text FROM classes WHERE id=?", (args.id,)).fetchone()
        con.close()
        if r:
            # 用注入器造 AI 味版本
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "inj", Path(__file__).parent / "ai-tell-inject.py")
            inj = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(inj)
            samples.append({"prompt": f"你是 MC百科（mcmod.cn）的编辑。请按主站编辑规范改写下面这段模组介绍。\n\n只输出改写后的正文。\n\n待改写：\n{inj.inject(r[2] or '', 0.85, seed=r[0])}",
                            "real": r[2], "name": r[1], "id": r[0]})
    else:
        f = DATA / "dataset" / "val.jsonl"
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        for r in rows[: args.n]:
            samples.append({"prompt": r["prompt"], "real": r["chosen"],
                            "rejected": r["rejected"], "name": "val"})

    print(f"加载 LoRA：{args.lora}")
    trained = PeftModel.from_pretrained(base, args.lora)
    trained.eval()

    for i, s in enumerate(samples, 1):
        print(f"\n{'='*70}\n样本 {i}")
        poison = s["prompt"].split("待改写：\n")[-1]
        print(f"--- 输入（AI 味版，{len(poison)} 字）---")
        print(poison[:300])
        print(f"\n--- 参考答案（真实百科，{len(s['real'])} 字）---")
        print(s["real"][:250].replace("\n", " "))
        print("\n--- base 模型输出 ---")
        print(gen(base, tok, s["prompt"], args.max_new)[:350].replace("\n", " "))
        print("\n--- 训练后模型输出 ---")
        print(gen(trained, tok, s["prompt"], args.max_new)[:350].replace("\n", " "))

        # 简单指标：AI 味套话计数
        for label, txt in [("答案", s["real"]),
                           ("base", gen(base, tok, s["prompt"], args.max_new)),
                           ("训练后", gen(trained, tok, s["prompt"], args.max_new))]:
            cues = ["值得注意的是", "值得一提的是", "从某种角度", "总的来说", "可以说",
                    "不难发现", "与此同时", "无疑", "彰显", "体现了"]
            n = sum(txt.count(c) for c in cues)
            print(f"  {label}：套话 {n} 处  长度 {len(txt)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
