$ErrorActionPreference = 'Stop'
$env:QT_QPA_PLATFORM = 'offscreen'
$exe = (Resolve-Path outputs/SiFengPlanet.exe).Path
try {
    $process = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 7
    $owned = @(Get-CimInstance Win32_Process -Filter "Name='SiFengPlanet.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
    Write-Output "GUI_EXE_RUNNING_PROCESSES: $($owned.Count)"
    if ($owned.Count -lt 2) { exit 1 }
} finally {
    $owned = @(Get-CimInstance Win32_Process -Filter "Name='SiFengPlanet.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
    $owned | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue
}
