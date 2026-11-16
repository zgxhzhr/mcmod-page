#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地改写工具：用训练好的 LoRA 模型把 AI 味草稿改成规范百科文。

本机 8GB 显存跑 7B 要用 4bit 量化（约 5GB），脚本已内置。

用法
----
    # 1) 改写一个文件
    python rewrite.py 草稿.md

    # 2) 从标准输入
    echo "值得注意的是，这个模组…" | python rewrite.py -

    # 3) 交互模式（适合反复试）
    python rewrite.py --interactive

    # 4) 指定模型/LoRA
    python rewrite.py 草稿.md --model 模型路径 --lora LoRA路径

    # 5) 只检查不改写（看 AI 味评分）
    python rewrite.py 草稿.md --check-only

输出
----
改写结果写到 <文件名>.rewritten.md，同时打印 AI 味检测对比。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

DATA = Path(r"E:\Mod\百科-语料")
DEFAULT_MODEL = DATA / "train/models/Qwen2.5-7B-Instruct"
DEFAULT_LORA = DATA / "train/run-7b/final"

# 主站规范 prompt（与训练时一致，保证分布匹配）
INSTRUCTION = (
    "你是 MC百科（mcmod.cn）的编辑。请按主站编辑规范改写下面这段模组介绍。\n"
    "\n"
    "【主站规范（审核会按条退回）】\n"
    "1. 不写主观词句、第一人称（我觉得/小编/个人认为）——规范 1\n"
    "2. 不写不确定语句（据说/貌似/应该）——规范 2\n"
    "3. 不用不规范用语、颜文字、无帮助的 emoji——规范 3\n"
    "4. 不写冗余句（欢迎补充/介绍就到这里）——规范 29\n"
    "5. 不堆叠标点（连续感叹号、连续句号、连续问号）——规范 19\n"
    "6. 标点完整：句末有句号，全半角统一——规范 12\n"
    "7. 不用 PS./注：等前后缀，注解融入正文——规范 24\n"
    "8. 提到版本特性要写具体版本号，禁用新版/旧版——规范 23\n"
    "9. 不凑字数、不空泛：要讲清做什么、怎么用、怎么获得——规范 18\n"
    "10. 保留原文全部数值、名称、机制与获取方式，不得改动\n"
    "\n"
    "只输出改写后的正文，不要解释、不要加标题。\n"
    "\n"
    "待改写：\n{txt}"
)


def load_checker():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "chk", Path(__file__).parent / "ai-tell-check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_model(model_path: str, lora_path: str, quant: bool = True):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"加载裸模型：{model_path}", file=sys.stderr)
    tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    kwargs = {"device_map": "cuda:0", "trust_remote_code": True}
    use_quant = False
    if quant:
        try:
            import bitsandbytes  # noqa: F401
            from transformers import BitsAndBytesConfig
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4")
            use_quant = True
            print("使用 4bit 量化（约 5GB 显存）", file=sys.stderr)
        except ImportError:
            print("未装 bitsandbytes，降级为 fp16", file=sys.stderr)
    if not use_quant:
        kwargs["torch_dtype"] = torch.float16
        # 估算显存需求
        try:
            import torch as _t
            total = _t.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"使用 fp16（本机显存 {total:.1f}GB）", file=sys.stderr)
            if total < 14:
                print(f"  ⚠ 显存不足 14GB，7B 模型可能 OOM。建议：pip install bitsandbytes",
                      file=sys.stderr)
        except Exception:
            pass

    model = AutoModelForCausalLM.from_pretrained(model_path, **kwargs)

    if lora_path and Path(lora_path).exists():
        from peft import PeftModel
        print(f"加载 LoRA：{lora_path}", file=sys.stderr)
        model = PeftModel.from_pretrained(model, lora_path)
    elif lora_path:
        print(f"⚠ 找不到 LoRA 目录（{lora_path}），用 base 模型", file=sys.stderr)

    model.eval()
    return model, tok


def rewrite(model, tok, text: str, max_new: int = 1200) -> str:
    import torch
    prompt = INSTRUCTION.format(txt=text)
    ids = tok.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False, add_generation_prompt=True)
    inp = tok(ids, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inp, max_new_tokens=max_new, do_sample=False,
            pad_token_id=tok.pad_token_id, repetition_penalty=1.05)
    return tok.decode(out[0][inp["input_ids"].shape[1]:],
                      skip_special_tokens=True).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="本地 AI 味改写工具")
    ap.add_argument("path", nargs="?", help="输入文件；'-' 表示 stdin")
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--lora", default=str(DEFAULT_LORA))
    ap.add_argument("--max-new", type=int, default=1200)
    ap.add_argument("--no-quant", action="store_true", help="不用 4bit（需要大显存）")
    ap.add_argument("--check-only", action="store_true", help="只检查不改写")
    ap.add_argument("--interactive", action="store_true", help="交互模式")
    args = ap.parse_args()

    chk = load_checker()

    if args.interactive:
        print("交互模式：粘贴文本，空行结束。输入 q 退出。\n")
        while True:
            try:
                lines = []
                while True:
                    line = input()
                    if not line.strip():
                        break
                    lines.append(line)
            except EOFError:
                break
            text = "\n".join(lines).strip()
            if not text or text.lower() == "q":
                break
            before = chk.check(text)
            print(f"\n[改写前] {before['score']} 分  {before['level']}")
            for it in before["issues"][:3]:
                print(f"  · {it['kind']}：{it['detail'][:60]}")
            model, tok = load_model(args.model, args.lora, not args.no_quant)
            out = rewrite(model, tok, text, args.max_new)
            after = chk.check(out)
            print(f"\n[改写后] {after['score']} 分  {after['level']}")
            print(f"\n{out}\n" + "─" * 60)
        return 0

    if args.path == "-":
        text = sys.stdin.read()
        src_name = "stdin"
    elif args.path:
        text = Path(args.path).read_text(encoding="utf-8-sig")
        src_name = args.path
    else:
        ap.print_help()
        return 2

    text = text.strip()
    if not text:
        print("输入为空", file=sys.stderr)
        return 1

    before = chk.check(text)
    print(f"=== 改写前 ===")
    print(f"  AI 味评分 {before['score']} / {before['level']}  （{len(text)} 字）")
    for it in before["issues"]:
        print(f"  · {it['kind']}：{it['detail'][:70]}")

    if args.check_only:
        return 0

    print(f"\n=== 加载模型 ===")
    model, tok = load_model(args.model, args.lora, not args.no_quant)

    print(f"\n=== 改写中 ===")
    out = rewrite(model, tok, text, args.max_new)

    after = chk.check(out)
    print(f"\n=== 改写后 ===")
    print(f"  AI 味评分 {after['score']} / {after['level']}  （{len(out)} 字）")
    for it in after["issues"]:
        print(f"  · {it['kind']}：{it['detail'][:70]}")

    # 信息保真检查
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ev", Path(__file__).parent / "eval-hard.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    keep = ev.score_output(out, text)
    print(f"\n  信息保留率 {keep['info_keep']:.1%}  "
          f"（原文数字/术语在改写后保留的比例）")
    if keep["info_keep"] < 0.9:
        print(f"  ⚠ 有 {1-keep['info_keep']:.0%} 的数值或术语丢失，请人工核对")

    # 保存
    out_path = Path(src_name).with_suffix(".rewritten.md") if src_name != "stdin" else Path("rewritten.md")
    out_path.write_text(out, encoding="utf-8")
    print(f"\n已保存：{out_path}")
    print(f"\n=== 输出内容 ===\n{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
