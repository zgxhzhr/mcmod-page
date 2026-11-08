#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语料抓取进度条（终端版 + 网页版）。

用法
----
    python corpus-progress.py                 # 打印一次
    python corpus-progress.py --watch         # 终端里持续刷新（Ctrl+C 退出）
    python corpus-progress.py --serve 8899    # 起本地网页，浏览器看实时进度条

进度口径
--------
- 已处理 = 数据库里的行数（成功、空页、失败都算已处理，不会重复抓）
- 有内容 = 正文 ≥100 字的条数
- 目标   = --target（默认 5000，与 crawl --limit 对齐）
- 速率 / ETA 用最近 30 条的时间戳估算
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEFAULT_DATA = Path(r"E:\Mod\百科-语料")

PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>MC百科语料抓取进度</title>
<style>
 body{font-family:'Microsoft YaHei',system-ui,sans-serif;background:#14161a;color:#e8eaed;
      display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;margin:0}
 h1{font-size:20px;font-weight:600;color:#9fb4d0;margin:0 0 28px}
 .wrap{width:min(88vw,900px)}
 .bar{height:34px;border-radius:17px;background:#232830;overflow:hidden;box-shadow:inset 0 0 0 1px #2f3a48}
 .fill{height:100%;width:0;border-radius:17px;
       background:linear-gradient(90deg,#3b82f6,#22d3ee);transition:width .6s ease}
 .pct{font-size:52px;font-variant-numeric:tabular-nums;font-weight:700;margin:22px 0 6px}
 .sub{color:#8b96a5;font-size:14px}
 .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:30px}
 .card{background:#1b1f26;border:1px solid #262d38;border-radius:12px;padding:14px}
 .k{color:#7d8794;font-size:12px;margin-bottom:6px}
 .v{font-size:22px;font-variant-numeric:tabular-nums;font-weight:600}
 .err{color:#f87171}.ok{color:#34d399}
 .foot{margin-top:24px;color:#5f6a78;font-size:12px}
</style></head>
<body><div class="wrap">
 <h1>MC百科模组介绍语料 · 抓取进度</h1>
 <div class="bar"><div class="fill" id="fill"></div></div>
 <div class="pct" id="pct">—</div>
 <div class="sub" id="sub">正在读取…</div>
 <div class="grid">
   <div class="card"><div class="k">已处理</div><div class="v" id="done">—</div></div>
   <div class="card"><div class="k">长文 ≥100字</div><div class="v ok" id="ok">—</div></div>
   <div class="card"><div class="k">短页 20-99字</div><div class="v" id="short">—</div></div>
   <div class="card"><div class="k">空/失败</div><div class="v err" id="bad">—</div></div>
   <div class="card"><div class="k">速度</div><div class="v" id="rate">—</div></div>
 </div>
 <div class="foot" id="foot"></div>
</div>
<script>
async function tick(){
  try{
    const r=await fetch('/api',{cache:'no-store'});
    const d=await r.json();
    document.getElementById('fill').style.width=Math.min(100,d.pct)+'%';
    document.getElementById('pct').textContent=d.pct.toFixed(1)+'%';
    document.getElementById('sub').textContent=
      d.done+' / '+d.target+' 条　剩余约 '+(d.eta_min>=0?d.eta_min+' 分钟':'—');
    document.getElementById('done').textContent=d.done;
    document.getElementById('ok').textContent=d.ok;
    document.getElementById('short').textContent=d.short;
    document.getElementById('bad').textContent=d.bad;
    document.getElementById('rate').textContent=d.rate.toFixed(2)+' 条/秒';
    document.getElementById('foot').textContent='最后更新 '+d.now+'　数据目录 '+d.data;
  }catch(e){ document.getElementById('sub').textContent='读取失败：'+e; }
}
tick(); setInterval(tick, 2000);
</script></body></html>"""


def stats(data: Path, target: int) -> dict:
    db = data / "mcmod.db"
    out = {"done": 0, "ok": 0, "bad": 0, "pct": 0.0, "rate": 0.0,
           "eta_min": -1, "target": target, "now": datetime.now().strftime("%H:%M:%S"),
           "data": str(data)}
    if not db.exists():
        return out
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=1.0)
    except Exception:
        return out
    try:
        row = con.execute(
            "SELECT COUNT(*), "
            "SUM(CASE WHEN chars>=100 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN chars>=20 AND chars<100 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN chars<20 OR chars IS NULL THEN 1 ELSE 0 END) FROM classes").fetchone()
        done = row[0] or 0
        out["done"] = done
        out["ok"] = row[1] or 0        # 长文（≥100 字，语料主力）
        out["short"] = row[2] or 0     # 短页（20-99 字）
        out["bad"] = row[3] or 0       # 空/失败

        # 实时速率：只看最近 180 秒内写入的条数（避免历史数据把速率拉低）
        times = [r[0] for r in con.execute(
            "SELECT fetched_at FROM classes ORDER BY rowid DESC LIMIT 300")]
        if times and times[0]:
            now_ts = datetime.strptime(times[0], "%Y-%m-%dT%H:%M:%S")
            window = 180.0
            recent = 0
            for ts in times:
                if not ts:
                    continue
                try:
                    dt = (now_ts - datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")).total_seconds()
                except Exception:
                    continue
                if dt <= window:
                    recent += 1
                else:
                    break
            if recent >= 2:
                out["rate"] = recent / window
            elif len(times) >= 5 and times[-1]:
                t0 = datetime.strptime(times[-1], "%Y-%m-%dT%H:%M:%S")
                span = (now_ts - t0).total_seconds()
                if span > 0:
                    out["rate"] = (len(times) - 1) / span
    except Exception:
        pass
    finally:
        con.close()

    t = target or max(out["done"], 1)
    out["pct"] = 100.0 * out["done"] / t
    if out["rate"] > 0 and out["done"] < t:
        out["eta_min"] = int((t - out["done"]) / out["rate"] / 60)
    return out


def bar(pct: float, width: int = 40) -> str:
    n = int(width * max(0.0, min(100.0, pct)) / 100.0)
    return "█" * n + "░" * (width - n)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--target", type=int, default=5000)
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--serve", type=int, default=0)
    args = ap.parse_args()
    data = Path(args.data)

    if args.serve:
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/api"):
                    body = json.dumps(stats(data, args.target), ensure_ascii=False).encode()
                    ct = "application/json; charset=utf-8"
                else:
                    body = PAGE.encode()
                    ct = "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        srv = ThreadingHTTPServer(("127.0.0.1", args.serve), H)
        print(f"进度页已启动：http://127.0.0.1:{args.serve}/  （Ctrl+C 停止）")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    def render() -> str:
        s = stats(data, args.target)
        eta = f"剩 {s['eta_min']} 分" if s["eta_min"] >= 0 else "—"
        line1 = (f"  [{bar(s['pct'])}] {s['pct']:5.1f}%  "
                 f"{s['done']}/{s['target']}  {eta}")
        line2 = (f"  长文 {s['ok']}   短页 {s.get('short', 0)}   空/失败 {s['bad']}   "
                 f"{s['rate']:.2f} 条/秒   {s['now']}")
        return line1 + "\n" + line2

    if not args.watch:
        print(render())
        return 0

    print("Ctrl+C 退出监控（不影响后台抓取）")
    try:
        while True:
            print("\r" + render(), end="", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已退出")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
