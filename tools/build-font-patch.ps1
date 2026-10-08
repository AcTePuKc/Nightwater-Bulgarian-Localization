param(
    [string]$BaseFont = "",
    [string]$DonorFont = "",
    [string]$PackageName = "SkylandsForaging-BG_Font_P",
    [string]$OutputDir = "",
    [string]$GamePaksDir = "C:\MyGames\Isle of Industry\SkylandsForaging\Content\Paks",
    [switch]$DeployToGame
)

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

if ([string]::IsNullOrWhiteSpace($BaseFont)) {
    $BaseFont = Join-Path $workspaceRoot "source\font-reference\original\SkylandsForaging\Content\SkylandsForaging\UI\Fonts\ChelseaMarket-Regular.ufont"
}
if ([string]::IsNullOrWhiteSpace($DonorFont)) {
    $DonorFont = "C:\WebStuff\Bmfont\Playpen_Sans\static\PlaypenSans-ExtraBold.ttf"
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $workspaceRoot "pak-output"
}

$python = "C:\WebStuff\BMFont-Python\.venv\Scripts\python.exe"
$mergeScript = Join-Path $workspaceRoot "tools\merge-font-glyphs.py"
$unrealPak = "C:\WebStuff\Dispatch-mod\tools\UnrealPak.exe"
$prototypeDir = Join-Path $workspaceRoot "source\font-prototypes"
$mergedFont = Join-Path $prototypeDir "ChelseaMarket-Regular-BG.ufont"
$responseFile = Join-Path $workspaceRoot ("tools\filelist-{0}.txt" -f $PackageName)
$pakPath = Join-Path $OutputDir ("{0}.pak" -f $PackageName)
$targetPath = "../../../SkylandsForaging/Content/SkylandsForaging/UI/Fonts/ChelseaMarket-Regular.ufont"
$stagingFont = Join-Path $workspaceRoot ("pak-staging\{0}\SkylandsForaging\Content\SkylandsForaging\UI\Fonts\ChelseaMarket-Regular.ufont" -f $PackageName)

foreach ($required in @($BaseFont, $DonorFont, $python, $mergeScript, $unrealPak)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing required font build input: $required"
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir, $prototypeDir | Out-Null

& $python $mergeScript --base $BaseFont --donor $DonorFont --output $mergedFont --ranges 0400-045F 0490-0493
if ($LASTEXITCODE -ne 0) {
    throw "Font merge failed with exit code $LASTEXITCODE"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $stagingFont) | Out-Null
Copy-Item -LiteralPath $mergedFont -Destination $stagingFont -Force

$responseLine = '"{0}" "{1}"' -f $stagingFont, $targetPath
Set-Content -LiteralPath $responseFile -Value $responseLine -Encoding ASCII

if (Test-Path -LiteralPath $pakPath) {
    Remove-Item -LiteralPath $pakPath -Force
}

& $unrealPak $pakPath "-create=$responseFile"
if ($LASTEXITCODE -ne 0) {
    throw "UnrealPak failed with exit code $LASTEXITCODE"
}

if ($DeployToGame) {
    if (-not (Test-Path -LiteralPath $GamePaksDir)) {
        throw "Missing game Paks directory: $GamePaksDir"
    }
    Copy-Item -LiteralPath $pakPath -Destination (Join-Path $GamePaksDir (Split-Path -Leaf $pakPath)) -Force
    Write-Host "Installed font patch: $(Join-Path $GamePaksDir (Split-Path -Leaf $pakPath))"
}

Write-Host "Created font patch: $pakPath"
