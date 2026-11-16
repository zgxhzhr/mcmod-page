#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MC百科文风训练：Qwen2.5 + LoRA + ORPO（或 SFT 兜底）。

数据格式（build-dataset.py 产出）
--------------------------------
    train.jsonl: {"prompt": ..., "chosen": 真实百科正文, "rejected": AI味版本}

训练目标
--------
1. 提高 chosen 的生成概率，压低 rejected（ORPO 的对比学习）
2. prompt 里带 MC 主站编辑规范 10 条，让模型学会"按规则写"
3. 最终效果：输入一段 AI 味介绍，输出规范、平实、信息完整的百科正文

显存策略（8GB RTX 4060 Laptop）
-------------------------------
- 默认 Qwen2.5-0.5B：权重约 1GB，LoRA 训练约 3-4GB → 稳
- 0.5B 效果不够时可换 1.5B，但需关掉占显存的程序
- gradient_checkpointing + batch 1 + grad_accum 8

用法
----
    # 先跑 200 条验证流程
    python train-orpo.py --max-samples 200 --epochs 1

    # 全量
    python train-orpo.py --epochs 3

    # 退回 SFT（只用 chosen）
    python train-orpo.py --mode sft

    # 换模型
    python train-orpo.py --model Qwen/Qwen2.5-1.5B-Instruct
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# 国内加速：HF 走镜像（必须在 import transformers 之前设）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

# 路径默认按本地配置；云端用 --data / --out 覆盖即可
_ENV_DATA = os.environ.get("MC_DATA_DIR")
_ENV_OUT = os.environ.get("MC_OUT_DIR")
DEFAULT_DATA = Path(_ENV_DATA) if _ENV_DATA else Path(r"E:\Mod\百科-语料\dataset")
OUT_DIR = Path(_ENV_OUT) if _ENV_OUT else Path(r"E:\Mod\百科-语料\train")
# 模型缓存：有 HF_HOME 就用，否则放 out 目录下（云端不必设）
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = str(OUT_DIR / "hf-cache")


def build_prompt(rec: dict) -> str:
    return rec["prompt"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--out", default=str(OUT_DIR / "run"))
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--mode", choices=["orpo", "sft"], default="orpo",
                    help="orpo=对比学习(推荐，不需要 reference model)；sft=只用 chosen")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--max-samples", type=int, default=0, help="0=全量，用于快速验证")
    ap.add_argument("--beta", type=float, default=0.1, help="ORPO 的 beta")
    ap.add_argument("--save-steps", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true", help="只检查数据和显存，不训练")
    args = ap.parse_args()

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig, TrainingArguments)
    from trl import ORPOConfig, ORPOTrainer, SFTConfig, SFTTrainer

    print(f"torch {torch.__version__}  CUDA {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        print(f"显存：空闲 {free/1024**3:.1f} / 共 {total/1024**3:.1f} GB")
    else:
        print("!! CUDA 不可用，训练会极慢（建议先修好 torch+CUDA）")

    # 数据
    data_dir = Path(args.data)
    train_file = data_dir / ("train.jsonl" if args.mode == "orpo" else "train-sft.jsonl")
    val_file = data_dir / "val.jsonl"
    rows = [json.loads(l) for l in train_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.max_samples:
        rows = rows[: args.max_samples]
    print(f"训练样本 {len(rows)} 条（{train_file.name}），模式 {args.mode}")

    if args.mode == "orpo":
        ds = Dataset.from_dict({
            "prompt": [build_prompt(r) for r in rows],
            "chosen": [r["chosen"] for r in rows],
            "rejected": [r["rejected"] for r in rows],
        })
    else:
        msgs = []
        for r in rows:
            m = r.get("messages")
            if m:
                msgs.append(m)
            else:
                msgs.append([{"role": "user", "content": r["prompt"]},
                             {"role": "assistant", "content": r["chosen"]}])
        ds = Dataset.from_dict({"messages": msgs})

    if args.dry_run:
        print("\n=== dry-run ===")
        print("样本 0 的 prompt 长度:", len(ds[0]["prompt"]) if args.mode == "orpo" else "-")
        if args.mode == "orpo":
            print("chosen 长度:", len(ds[0]["chosen"]), " rejected 长度:", len(ds[0]["rejected"]))
        print("数据检查通过，去掉 --dry-run 开始训练")
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # 显存策略：4bit 量化（有 bitsandbytes 时用），否则 fp16
    quant_cfg = None
    try:
        import bitsandbytes  # noqa: F401
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4")
        print("使用 4bit 量化加载")
    except ImportError:
        print("未装 bitsandbytes，用 fp16 加载")

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=quant_cfg,
        torch_dtype=torch.float16 if quant_cfg is None else None,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False
    if quant_cfg is not None:
        model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()

    lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    common = dict(
        output_dir=str(out), num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr, fp16=torch.cuda.is_available(),
        logging_steps=5, save_steps=args.save_steps, save_total_limit=2,
        warmup_ratio=0.05, lr_scheduler_type="cosine",
        gradient_checkpointing=True, report_to=[],
        dataloader_pin_memory=False,
    )

    if args.mode == "orpo":
        cfg = ORPOConfig(**common, beta=args.beta, max_length=args.max_len,
                         max_prompt_length=args.max_len // 2,
                         remove_unused_columns=False)
        trainer = ORPOTrainer(model=model, args=cfg, train_dataset=ds, tokenizer=tok)
    else:
        # SFT 用 messages 格式，让 trainer 自己 apply_chat_template
        cfg = SFTConfig(**common, max_seq_length=args.max_len,
                        remove_unused_columns=True)
        trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds,
                             tokenizer=tok)

    print("\n开始训练…")
    trainer.train()
    trainer.save_model(str(out / "final"))
    tok.save_pretrained(str(out / "final"))
    print(f"\n完成，模型保存在 {out/'final'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
