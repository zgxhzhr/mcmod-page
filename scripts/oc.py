# -*- coding: utf-8 -*-
"""oc.py — opencode 外包封装（无头、JSON 事件流、免费模型）

用法：
  python oc.py --prompt-file task.md --cwd <工作目录> [--model opencode/...] [--out 结果.json]

行为：
  1. 调 `opencode run --format json`，把模型最后一段 text 拼起来
  2. 若 --out 给了且看起来是 JSON，落盘并校验可解析
  3. 打印耗时/token/退出码，失败退出码非 0
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

EXE = r"C:\Users\MKIII\AppData\Local\Programs\opencode\opencode.exe"
DEFAULT_MODEL = "opencode/deepseek-v4.1-flash-free"


def run(prompt_file: Path, cwd: Path, model: str, timeout: int = 900):
    t0 = time.time()
    proc = subprocess.run(
        [EXE, "run", "--model", model, "--format", "json", "--auto", "--archived",
         "-f", prompt_file.name, "按 " + prompt_file.name + " 的规则执行，只输出要求的内容。"],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout)
    texts, tin, tout, session = [], 0, 0, None
    for line in proc.stdout.splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        session = ev.get("sessionID") or session
        if ev.get("type") == "text":
            texts.append(ev["part"]["text"])
        elif ev.get("type") == "step_finish":
            tk = ev["part"].get("tokens") or {}
            tin += tk.get("input", 0)
            tout += tk.get("output", 0)
    return {
        "answer": "".join(texts).strip(),
        "elapsed": round(time.time() - t0, 1),
        "code": proc.returncode,
        "session": session,
        "tokens_in": tin,
        "tokens_out": tout,
        "stderr": proc.stderr[-1500:] if proc.returncode else "",
    }


def extract_json(text: str):
    """从回答里抓第一个 JSON 数组/对象。"""
    for m in re.finditer(r"[\[{]", text):
        frag = text[m.start():]
        dec = json.JSONDecoder()
        try:
            obj, _ = dec.raw_decode(frag)
            return obj
        except Exception:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", default="")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--expect", choices=["json", "text"], default="json")
    a = ap.parse_args()

    pf = Path(a.prompt_file)
    cwd = Path(a.cwd)
    assert pf.exists(), f"prompt 文件不存在: {pf}"
    r = run(pf, cwd, a.model, a.timeout)
    print(f"opencode: {r['elapsed']}s  exit={r['code']}  tokens in={r['tokens_in']} out={r['tokens_out']}  session={r['session']}")
    if r["code"] != 0:
        print(r["stderr"], file=sys.stderr)
        sys.exit(1)
    if a.expect == "json":
        obj = extract_json(r["answer"])
        if obj is None:
            print("✗ 回答里没有可解析的 JSON", file=sys.stderr)
            print(r["answer"][:800], file=sys.stderr)
            sys.exit(2)
        if a.out:
            Path(a.out).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✓ {a.out}（{len(obj) if isinstance(obj, list) else 1} 条）")
    else:
        if a.out:
            Path(a.out).write_text(r["answer"], encoding="utf-8")
            print(f"✓ {a.out}（{len(r['answer'])} 字符）")
        else:
            print(r["answer"])


if __name__ == "__main__":
    main()
