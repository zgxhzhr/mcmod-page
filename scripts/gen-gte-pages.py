#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GregTech Energistics（5175）—— 按审核意见改走「综合」。

审核原话：
  这一类一种设备的不同电压的版本，创建综合抽象资料用一个表列出区别就可以啦

8 个 AE2 库存覆盖板唯一的差异是「最大库存」，且严格按 4 倍递增：
  LV 1,280 → MV 5,120 → HV 20,480 → EV 81,920
  → IV 327,680 → LuV 1,310,720 → ZPM 5,242,880 → UV 20,971,520

产出：
  gte-抽象资料-5175.json   1 条（AE2 库存覆盖板），正文含 8 行表
  gte-子资料-5175.json     8 条，正文空
  gte-物品导入-5175.json   保留其余 4 条（机器状态覆盖板、流体编码器、库存终端、扩展样板终端）

图标：旧交付只有 icon32，没有 icon128。本次用现有 32×32 像素图按 NEAREST 放大补 128。
"""
import base64
import io
import json
import random
import re
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "gte-物品导入-5175.json"
OUT_ABSTRACT = BASE / "gte-抽象资料-5175.json"
OUT_CHILD = BASE / "gte-子资料-5175.json"
OUT_REST = BASE / "gte-物品导入-5175.json"
NS = "gregtechenergistics"

_PAW = ["呜喵", "喵呜", "喵喵"]

# 电压等级： (显示名, id 片段, 最大库存)
TIERS = [
    ("LV", "lv", 1_280),
    ("MV", "mv", 5_120),
    ("HV", "hv", 20_480),
    ("EV", "ev", 81_920),
    ("IV", "iv", 327_680),
    ("LuV", "luv", 1_310_720),
    ("ZPM", "zpm", 5_242_880),
    ("UV", "uv", 20_971_520),
]


def b64_from_bytes(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def upscale128(icon32_b64: str) -> str:
    """把 32×32 的图标放大到 128（像素图用 NEAREST，不糊）。"""
    if not icon32_b64:
        return ""
    im = Image.open(io.BytesIO(base64.b64decode(icon32_b64))).convert("RGBA")
    if im.size != (128, 128):
        im = im.resize((128, 128), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return b64_from_bytes(buf.getvalue())


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    by_name = {r["name"]: r for r in rows}

    # ── 抽象资料 ──
    table_rows = "".join(
        f"<tr><td>{tier}</td><td>{val:,}</td><td>{val // 1280}×</td></tr>"
        for tier, _, val in TIERS
    )

    abstract_html = (
        "<p>AE2 库存覆盖板是 GregTech Energistics 添加的机器覆盖板，"
        "把格雷机器接进 AE2 的 ME 网络，让它按合成样板自动取料与回料。</p>"

        "<p><strong>用法</strong>：贴在格雷机器的任意一面，接入 ME 网络后配置合成样板。"
        "覆盖板按样板的输入清单从网络抽取材料送入机器，再把产出送回网络。</p>"

        "<p><strong>库存机制</strong>：持续监测机器内的材料量，低于设定值即补充，达到上限停止。"
        "既避免机器因缺料停工，也避免一次性灌满导致网络内其他机器取不到料。</p>"

        "<p><strong>状态显示</strong>：界面显示运行中、缺少样板、网格连接异常、库存已满、"
        "缺少输入、多方块异常、输入或输出空间不足等状态。</p>"

        "<p><strong>开关</strong>：流体支持与输出功能可单独开关。另有合成卡槽位，"
        "安装后材料不足时可向网络发起合成请求。</p>"

        "<p><strong>八个电压等级</strong>：功能完全一致，唯一区别是能为所贴机器维持的材料总量上限。"
        "每升一级，上限变为四倍。</p>"

        "<table><thead><tr><th>等级</th><th>最大库存</th><th>相对 LV</th></tr></thead><tbody>"
        + table_rows +
        "</tbody></table>"
    )

    abstract = [{
        "id": "ae2_stocker_cover",
        "name": "AE2 库存覆盖板",
        "ename": "AE2 Stocker Cover",
        "regname": "",
        "category": "覆盖板",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "GregTech Energistics 抽象资料（图标与注册名留空）："
            "八级覆盖板的功能说明取自各条目正文的实测描述，"
            "最大库存取自 gregtechenergistics:ae2.stocker.* 各等级的注册参数，"
            "按 4 倍递增排列。图标与注册名按抽象资料规范留空。"
            f"{tail()}"
        ),
        "html": abstract_html,
        "icon32": "",
        "icon128": "",
    }]
    OUT_ABSTRACT.write_text(json.dumps(abstract, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 8 条子资料 ──
    children = []
    for tier, frag, val in TIERS:
        old = by_name.get(f"AE2 库存覆盖板（{tier}）")
        icon32 = old.get("icon32", "") if old else ""
        children.append({
            "id": f"ae2_stocker_{frag}",
            "name": f"AE2 库存覆盖板（{tier}）",
            "ename": "",
            "regname": f"{NS}:ae2.stocker.{frag}",
            "category": "覆盖板",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                f"GregTech Energistics 子资料（待综合）：物品 id 为 {NS}:ae2.stocker.{frag}，"
                f"最大库存 {val:,}。正文由抽象资料「AE2 库存覆盖板」统一提供，本条不单独撰写。"
                f"{tail()}"
            ),
            "html": "",
            "icon32": icon32,
            "icon128": upscale128(icon32),
        })
    OUT_CHILD.write_text(json.dumps(children, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 其余 4 条保留，补 icon128 ──
    rest = []
    for r in rows:
        if r["name"].startswith("AE2 库存覆盖板"):
            continue
        if not r.get("icon128"):
            r["icon128"] = upscale128(r.get("icon32", ""))
        rest.append(r)
    OUT_REST.write_text(json.dumps(rest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"抽象资料 1 条 → {OUT_ABSTRACT.name}  ({OUT_ABSTRACT.stat().st_size/1024:.1f} KB)")
    print(f"  正文 {len(abstract_html)} 字符，表格 8 行")
    print(f"子资料 {len(children)} 条 → {OUT_CHILD.name}")
    print(f"其余 {len(rest)} 条 → {OUT_REST.name}（已补 icon128）")
    print("\n  等级      最大库存      相对LV")
    for t, _, v in TIERS:
        print(f"  {t:<8}{v:>12,}{v//1280:>8}×")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
