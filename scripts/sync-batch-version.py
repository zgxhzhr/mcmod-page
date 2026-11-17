# -*- coding: utf-8 -*-
"""sync-batch-version.py — 批量脚本的版本号三处保持一致

背景（rules/05 §6.9 坑 2 / v2.49→2.50 实测）：版本号有三个落点，
只改 `@version` 而漏掉 `const MB_VERSION`，面板会一直显示旧版本号
（面板标题读的是 MB_VERSION，不是 @version）。

三处：
  1. script 里的 `// @version`
  2. script 里的 `const MB_VERSION`
  3. 扩展目录的 `manifest.json` 的 "version"

用法：
  python sync-batch-version.py                # 检查（不一致退出码 1）
  python sync-batch-version.py --set 2.51     # 把三处统一改成 2.51（并同步扩展副本）
  python sync-batch-version.py --set 2.51 --no-copy   # 只改技能目录里的源文件
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SRC = SKILL / "scripts" / "mcmod-batch.user.js"
EXT = Path(os.environ.get("LOCALAPPDATA", "")) / "McmodBatchExt"


def get_versions(path: Path):
    t = path.read_text(encoding="utf-8")
    m_at = re.search(r"//\s*@version\s+(\S+)", t)
    m_mb = re.search(r"const MB_VERSION\s*=\s*'([^']+)'", t)
    return (m_at.group(1) if m_at else None,
            m_mb.group(1) if m_mb else None)


def manifest_version() -> str | None:
    mf = EXT / "manifest.json"
    if not mf.exists():
        return None
    try:
        return json.loads(mf.read_text(encoding="utf-8")).get("version")
    except Exception:
        return None


def report():
    at, mb = get_versions(SRC)
    mfv = manifest_version()
    print(f"技能源文件  @version = {at}")
    print(f"技能源文件  MB_VERSION = {mb}")
    print(f"扩展 manifest version = {mfv}   (扩展目录: {EXT})")
    ext_c = EXT / "content.js"
    if ext_c.exists():
        at2, mb2 = get_versions(ext_c)
        print(f"扩展 content.js  @version={at2}  MB_VERSION={mb2}  "
              f"更新于 {ext_c.stat().st_mtime:.0f}")
    ok = at == mb and (mfv is None or mfv == at)
    print("→", "一致 ✓" if ok else "不一致 ✗（用 --set <版本> 统一）")
    return ok


def apply(new: str, copy: bool):
    t = SRC.read_text(encoding="utf-8")
    t2 = re.sub(r"(//\s*@version\s+)\S+", rf"\g<1>{new}", t, count=1)
    t2 = re.sub(r"(const MB_VERSION\s*=\s*')[^']+(')", rf"\g<1>{new}\g<2>", t2, count=1)
    if t2 == t and new not in t:
        print("✗ 没找到版本号锚点", file=sys.stderr)
        sys.exit(1)
    SRC.write_text(t2, encoding="utf-8")
    # 回读校验
    at, mb = get_versions(SRC)
    assert at == new and mb == new, f"回读失败: @version={at} MB_VERSION={mb}"
    print(f"✓ 源文件三处→{new}（回读 @version={at} MB_VERSION={mb}）")

    if not copy:
        return
    mf = EXT / "manifest.json"
    if mf.exists():
        d = json.loads(mf.read_text(encoding="utf-8"))
        d["version"] = new
        mf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✓ manifest.json → {new}")
    if (EXT / "content.js").parent.exists():
        shutil.copy(SRC, EXT / "content.js")
        at2, mb2 = get_versions(EXT / "content.js")
        assert at2 == new and mb2 == new, "扩展副本回读失败"
        print(f"✓ 扩展副本已同步（回读 {at2} / {mb2}）——去 edge://extensions 点一次「重新加载」")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="")
    ap.add_argument("--no-copy", action="store_true")
    a = ap.parse_args()
    if a.set:
        apply(a.set, copy=not a.no_copy)
    sys.exit(0 if report() else 1)
