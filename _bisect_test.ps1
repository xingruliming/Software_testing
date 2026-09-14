$ErrorActionPreference = "Continue"
$log = "E:\0_work\1shijian\Software_testing\_bisect_log.txt"
"=== bisect ===" | Out-File -FilePath $log -Encoding utf8

$names = @("_stageX","_stage0","_stage1","_stage2","_stage3")
$stamp = Get-Date -Format "HHmmss"
$i = 0
foreach ($n in $names) {
    $i++
    $src = "E:\0_work\1shijian\Software_testing\$n.pptx"
    $out = "E:\0_work\1shijian\Software_testing\_bpng_${stamp}_$i"
    New-Item -ItemType Directory -Path $out -Force | Out-Null
    try {
        $app = New-Object -ComObject PowerPoint.Application
        $app.DisplayAlerts = 1
        $pres = $app.Presentations.Open($src, $true, $false, $false)
        $c = $pres.Slides.Count
        $pres.Export($out, "PNG", 1200, 675)
        $e = (Get-ChildItem $out | Measure-Object).Count
        $pres.Close()
        $app.Quit()
        "$n : OPEN OK slides=$c exported=$e" | Out-File $log -Append -Encoding utf8
    } catch {
        "$n : FAILED - " + $_.Exception.Message | Out-File $log -Append -Encoding utf8
    }
}
"=== done ===" | Out-File -FilePath $log -Append -Encoding utf8
