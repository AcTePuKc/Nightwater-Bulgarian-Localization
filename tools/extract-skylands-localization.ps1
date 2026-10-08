param(
    [string]$GamePaksDir = "C:\MyGames\Isle of Industry\SkylandsForaging\Content\Paks",
    [string]$OutputRoot = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $workspaceRoot "source\raw"
}

$pak = Join-Path $GamePaksDir "SkylandsForaging-Windows.pak"
$repak = "C:\WebStuff\Dispatch-mod\tools\repak\repak.exe"
if (-not (Test-Path -LiteralPath $pak)) { throw "Game pak not found: $pak" }
if (-not (Test-Path -LiteralPath $repak)) { throw "repak.exe not found: $repak" }
if ((Test-Path -LiteralPath $OutputRoot) -and -not $Force) {
    throw "Output already exists: $OutputRoot. Use -Force for an intentional refresh."
}
if (Test-Path -LiteralPath $OutputRoot) {
    Remove-Item -LiteralPath $OutputRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

& $repak unpack $pak -o $OutputRoot -s "../../../" -f -i "SkylandsForaging/Content/Localization/Game" -q
if ($LASTEXITCODE -ne 0) { throw "repak failed with exit code $LASTEXITCODE" }

$rawRoot = Join-Path $OutputRoot "SkylandsForaging\Content\Localization\Game"
Copy-Item -LiteralPath (Join-Path $rawRoot "en\Game.locres") -Destination (Join-Path $workspaceRoot "source\Game.en.locres") -Force
Copy-Item -LiteralPath (Join-Path $rawRoot "bs\Game.locres") -Destination (Join-Path $workspaceRoot "source\Game.bs.locres") -Force

Write-Host "Localization extraction complete: $OutputRoot"
Write-Host "English source: $(Join-Path $workspaceRoot 'source\Game.en.locres')"
Write-Host "Override reference: $(Join-Path $workspaceRoot 'source\Game.bs.locres')"
