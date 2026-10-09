param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$OutputDir = "release\dist"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$distRoot = Join-Path $repoRoot $OutputDir
$assetsRoot = Join-Path $PSScriptRoot "assets"

if ($Version.StartsWith("v")) {
    $Version = $Version.Substring(1)
}
if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "Version must not be empty."
}

$translationFiles = @(
    "SkylandsForaging-BG_P.pak",
    "SkylandsForaging-BG_P.utoc",
    "SkylandsForaging-BG_P.ucas"
)
$fontFiles = @("SkylandsForaging-Font_P.pak")

foreach ($file in $translationFiles + $fontFiles) {
    $source = Join-Path $assetsRoot $file
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing release asset: $source"
    }
}

if (Test-Path -LiteralPath $distRoot) {
    Remove-Item -LiteralPath $distRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $distRoot | Out-Null

function New-GameArchive {
    param(
        [string]$Name,
        [string[]]$Files
    )

    $packageRoot = Join-Path $distRoot $Name
    $paksRoot = Join-Path $packageRoot "SkylandsForaging\Content\Paks"
    New-Item -ItemType Directory -Force -Path $paksRoot | Out-Null
    foreach ($file in $Files) {
        Copy-Item -LiteralPath (Join-Path $assetsRoot $file) -Destination (Join-Path $paksRoot $file) -Force
    }
    $archive = Join-Path $distRoot ("{0}-{1}.zip" -f $Name, $Version)
    Compress-Archive -Path (Join-Path $packageRoot "SkylandsForaging") -DestinationPath $archive -CompressionLevel Optimal
    Remove-Item -LiteralPath $packageRoot -Recurse -Force
    Write-Host "Created $archive"
}

New-GameArchive -Name "SkylandsForaging-Bulgarian-Localization" -Files $translationFiles
New-GameArchive -Name "SkylandsForaging-Universal-Font" -Files $fontFiles
