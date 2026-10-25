# install.ps1 —— 把本技能装进 DSH 技能目录（Windows）
# 用法：解压后在本文件夹里右键「使用 PowerShell 运行」，或执行
#   powershell -ExecutionPolicy Bypass -File .\install.ps1

$ErrorActionPreference = "Stop"
$dest = Join-Path $env:USERPROFILE ".dsh\skills\mcmod-page"

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot "*") -Destination $dest -Recurse -Force

Write-Host ""
Write-Host "[OK] 已安装到 $dest" -ForegroundColor Green
Write-Host "     下一步：重启会话，然后说「帮我优化这个百科页」；也可显式 skill mcmod-page"
Write-Host "     自检：cd `"$dest\scripts`"; python md2mcmod.py 示例-源.md -o 示例.mcmod.html"
Write-Host ""
