# install.ps1 —— 把本技能装进 DSH 技能目录（Windows）
# 用法：在本文件夹里执行
#   powershell -ExecutionPolicy Bypass -File .\install.ps1

$ErrorActionPreference = "Stop"
$dest = Join-Path $env:USERPROFILE ".dsh\skills\mcmod-page"

New-Item -ItemType Directory -Force -Path $dest | Out-Null

$exclude = @(".git", ".gitattributes", ".gitignore")
Get-ChildItem -Path $PSScriptRoot -Force | Where-Object {
    $name = $_.Name
    if ($exclude -contains $name) { return $false }
    if ($name -like "*.bak*") { return $false }
    return $true
} | ForEach-Object {
    if ($_.PSIsContainer) {
        Copy-Item $_.FullName -Destination $dest -Recurse -Force
    } else {
        Copy-Item $_.FullName -Destination $dest -Force
    }
}

Write-Host ""
Write-Host "[OK] 已安装到 $dest" -ForegroundColor Green
Write-Host ""
Write-Host "内容核对：" -ForegroundColor Cyan

$md = Join-Path $dest "SKILL.md"
if (Test-Path $md) {
    $kb = [math]::Round((Get-Item $md).Length / 1KB, 1)
    Write-Host ("  SKILL.md   {0} KB" -f $kb)
}

$sc = Join-Path $dest "scripts"
if (Test-Path $sc) {
    $cnt = (Get-ChildItem $sc -Recurse -File).Count
    Write-Host ("  scripts/   {0} 个文件" -f $cnt)
}

$as = Join-Path $dest "assets"
if (Test-Path $as) {
    $cnt2 = (Get-ChildItem $as -Recurse -File).Count
    Write-Host ("  assets/    {0} 个文件" -f $cnt2)
}

Write-Host ""
Write-Host "下一步：重启会话，说「帮我写这个模组的百科页」；也可显式 skill mcmod-page" -ForegroundColor Gray
Write-Host ""
Write-Host "自检（跑不通就是没装好）：" -ForegroundColor Cyan
Write-Host ("  cd " + $dest) -ForegroundColor Gray
Write-Host "  python scripts\check-page-structure.py --help" -ForegroundColor Gray
Write-Host ""
