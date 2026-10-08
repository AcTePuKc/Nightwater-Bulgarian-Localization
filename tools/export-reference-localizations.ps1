param(
    [string]$RawRoot = "",
    [string]$OutputRoot = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

if ([string]::IsNullOrWhiteSpace($RawRoot)) {
    $RawRoot = Join-Path $workspaceRoot "source\raw\SkylandsForaging\Content\Localization\Game"
}
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $workspaceRoot "source\reference-localizations"
}

$unrealLocres = "C:\WebStuff\Dispatch-mod\tools\UnrealLocres.exe"
if (-not (Test-Path -LiteralPath $RawRoot)) {
    throw "Raw localization root not found: $RawRoot"
}
if (-not (Test-Path -LiteralPath $unrealLocres)) {
    throw "UnrealLocres not found: $unrealLocres"
}
if ((Test-Path -LiteralPath $OutputRoot) -and -not $Force) {
    throw "Output already exists: $OutputRoot. Use -Force for an intentional refresh."
}
if (Test-Path -LiteralPath $OutputRoot) {
    Remove-Item -LiteralPath $OutputRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$locresFiles = Get-ChildItem -LiteralPath $RawRoot -Directory | ForEach-Object {
    $locres = Join-Path $_.FullName "Game.locres"
    if (Test-Path -LiteralPath $locres) {
        [PSCustomObject]@{ Culture = $_.Name; Path = $locres }
    }
}

foreach ($item in $locresFiles) {
    $cultureOutput = Join-Path $OutputRoot $item.Culture
    New-Item -ItemType Directory -Force -Path $cultureOutput | Out-Null
    $csv = Join-Path $cultureOutput "Game.csv"
    & $unrealLocres export -f csv $item.Path -o $csv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not export $($item.Culture): exit code $LASTEXITCODE"
    }
    Write-Host "Exported $($item.Culture): $csv"
}

Write-Host "Reference localization export complete: $OutputRoot"
