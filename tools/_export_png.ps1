$ErrorActionPreference = "Stop"
# 用 PowerPoint COM 把 pptx 逐页导出 PNG（本机 slidep screenshot 不可用）
$src = $args[0]
$out = $args[1]
if (Test-Path $out) { New-Item -ItemType Directory -Force -Path $out | Out-Null } else { New-Item -ItemType Directory -Force -Path $out | Out-Null }

$app = New-Object -ComObject PowerPoint.Application
# DisplayAlerts: 1 = ppAlertsNone 是非法值，合法为 1=None? 实际 ppAlertLevel: 1=ppAlertsNone, 2=ppAlertsAll
$app.DisplayAlerts = 1
$pres = $app.Presentations.Open($src, $true, $false, $false)
$pres.Export($out, "PNG", 1600, 900)
$pres.Close()
$app.Quit()
Write-Output "exported to $out"
Get-ChildItem $out | Select-Object -ExpandProperty Name
