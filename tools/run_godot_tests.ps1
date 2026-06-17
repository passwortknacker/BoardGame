<#
.SYNOPSIS
  Run all Godot engine checks headlessly (import + smoke/determinism + behavioural assertions).
.DESCRIPTION
  Finds the Godot 4 executable (via the GODOT env var, PATH, or %LOCALAPPDATA%\Godot), builds the
  class cache, then runs tests/run_headless.gd and tests/test_effects.gd. Exits non-zero on failure.
.EXAMPLE
  pwsh tools/run_godot_tests.ps1
  $env:GODOT = "C:\path\to\Godot.exe"; pwsh tools/run_godot_tests.ps1
#>
$ErrorActionPreference = "Stop"
$proj = Join-Path $PSScriptRoot "..\godot" | Resolve-Path

function Find-Godot {
    if ($env:GODOT -and (Test-Path $env:GODOT)) { return $env:GODOT }
    $cmd = Get-Command godot -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $local = Get-ChildItem "$env:LOCALAPPDATA\Godot" -Filter "Godot_v4*win64.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($local) { return $local.FullName }
    throw "Godot not found. Set `$env:GODOT to the Godot 4 executable."
}

function Invoke-Godot([string[]]$gargs, [string]$label) {
    $out = New-TemporaryFile; $err = New-TemporaryFile
    # Quote any arg containing spaces (Start-Process joins array args with spaces, breaking paths).
    $argline = ($gargs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
    $p = Start-Process -FilePath $godot -ArgumentList $argline -NoNewWindow -Wait `
        -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    $stdout = Get-Content $out -Raw; $stderr = Get-Content $err -Raw
    Remove-Item $out, $err -Force
    Write-Host "----- $label -----"
    if ($stdout) { Write-Host $stdout }
    $scriptErrors = if ($stderr) { ($stderr -split "`n" | Select-String "SCRIPT ERROR|Failed to load|Parse Error") } else { @() }
    if ($scriptErrors) { Write-Host "SCRIPT ERRORS:" -ForegroundColor Red; $scriptErrors | ForEach-Object { Write-Host "  $_" } }
    return @{ exit = $p.ExitCode; errors = ($scriptErrors.Count -gt 0); stdout = $stdout }
}

$godot = Find-Godot
Write-Host "Godot: $godot"
Write-Host "Project: $proj`n"

# 1) import (builds the global class-name cache; required on a fresh checkout)
Invoke-Godot @("--headless", "--path", "$proj", "--import") "import" | Out-Null

$fail = $false
foreach ($t in @("run_headless", "test_effects")) {
    $r = Invoke-Godot @("--headless", "--path", "$proj", "--script", "res://tests/$t.gd") $t
    if ($r.exit -ne 0 -or $r.errors -or ($r.stdout -match "failed" -and $r.stdout -notmatch "0 failed")) { $fail = $true }
}

Write-Host "`n================================="
if ($fail) { Write-Host "RESULT: FAILURES (see above)" -ForegroundColor Red; exit 1 }
else { Write-Host "RESULT: ALL GODOT CHECKS PASSED" -ForegroundColor Green; exit 0 }
