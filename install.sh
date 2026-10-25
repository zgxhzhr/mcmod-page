#!/usr/bin/env bash
# install.sh —— 把本技能装进 DSH 技能目录（macOS / Linux）
# 用法：解压后在本文件夹里执行 bash install.sh
set -euo pipefail

dest="${HOME}/.dsh/skills/mcmod-page"
mkdir -p "$dest"
cp -r "$(cd "$(dirname "$0")" && pwd)"/. "$dest"/

echo ""
echo "[OK] 已安装到 $dest"
echo "     下一步：重启会话，然后说「帮我优化这个百科页」；也可显式 skill mcmod-page"
echo "     自检：cd \"$dest/scripts\" && python3 md2mcmod.py 示例-源.md -o 示例.mcmod.html"
echo ""
