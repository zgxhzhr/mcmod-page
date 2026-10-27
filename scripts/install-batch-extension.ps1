# 把「MC百科 批量新增」装成浏览器扩展（Edge / Chrome 通用）
# 装一次之后，打开 /item/add/ 页面就自动在工具栏出现「批量新增」按钮，不需要书签、不需要控制台。
#
# 用法（在本文件所在目录）：
#   powershell -ExecutionPolicy Bypass -File install-batch-extension.ps1
#   powershell -ExecutionPolicy Bypass -File install-batch-extension.ps1 -Uninstall

param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$src     = Join-Path $here 'mcmod-batch.user.js'
$dest    = Join-Path $env:LOCALAPPDATA 'McmodBatchExt'

if ($Uninstall) {
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Write-Host "已删除扩展目录：$dest" -ForegroundColor Yellow
    Write-Host "别忘了到 edge://extensions 里把「MC百科 批量新增」移除。" -ForegroundColor Yellow
    return
}

if (-not (Test-Path $src)) { throw "找不到 mcmod-batch.user.js，请把它和本脚本放同一目录。" }

if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
Copy-Item $src (Join-Path $dest 'content.js') -Force

$manifest = @'
{
  "manifest_version": 3,
  "name": "MC百科 批量新增",
  "version": "2.0",
  "description": "在 MC百科 新增资料页注入「批量新增」按钮，批量填充并提交资料。",
  "content_scripts": [
    {
      "matches": [
        "https://www.mcmod.cn/item/add/*",
        "https://www1.mcmod.cn/item/add/*"
      ],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ]
}
'@
$manifest | Set-Content -Path (Join-Path $dest 'manifest.json') -Encoding UTF8 -NoNewline

Write-Host ''
Write-Host ' 扩展文件已生成：' -ForegroundColor Green
Write-Host "   $dest" -ForegroundColor Cyan
Write-Host ''
Write-Host ' 接下来 3 步（只需一次）：' -ForegroundColor Green
Write-Host '   1) 浏览器打开  edge://extensions  （Chrome 用 chrome://extensions）'
Write-Host '   2) 右上角打开「开发人员模式」'
Write-Host '   3) 点「加载解压缩的扩展」，选择上面那个目录'
Write-Host ''
Write-Host ' 装完后打开 https://www.mcmod.cn/item/add/<classId>/ ，' -ForegroundColor Green
Write-Host ' 工具栏「读取 (Ctrl+O)」后面会出现「批量新增」按钮。' -ForegroundColor Green
Write-Host ''

try { Start-Process 'msedge.exe' 'edge://extensions' } catch { Write-Host '（无法自动打开浏览器，请手动打开 edge://extensions）' }
