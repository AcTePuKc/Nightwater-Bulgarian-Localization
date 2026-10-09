param(
    [ValidateSet("auto", "csv", "json")]
    [string]$TranslationFormat = "auto",
    [string]$ConfigPath = "",
    [bool]$DeployToGame = $false,
    [bool]$CreateZip = $false,
    [bool]$IncludeFont = $false
)

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $workspaceRoot "config\UELocKit.config.psd1"
}
$config = Import-PowerShellDataFile -LiteralPath $ConfigPath

$kitScript = "C:\WebStuff\UELocKit\tools\build-standalone-locmod.ps1"
if (-not (Test-Path -LiteralPath $kitScript)) {
    throw "UELocKit packaging script not found: $kitScript"
}

& $kitScript `
    -WorkspaceRoot $workspaceRoot `
    -ConfigPath $ConfigPath `
    -TranslationFormat $TranslationFormat `
    -DeployToGame $DeployToGame

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeFont) {
    $fontScript = Join-Path $workspaceRoot "tools\build-font-patch.ps1"
    if (-not (Test-Path -LiteralPath $fontScript)) {
        throw "Font build script not found: $fontScript"
    }

    & $fontScript
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $packageName = [string]$config.PackageName
    $gameName = [string]$config.GameName
    $outputDir = Join-Path $workspaceRoot "pak-output"
    $responseFile = Join-Path $workspaceRoot ("tools\filelist-{0}.txt" -f $packageName)
    $fontStaging = Join-Path $workspaceRoot ("pak-staging\SkylandsForaging-Font_P\SkylandsForaging\Content\SkylandsForaging\UI\Fonts\ChelseaMarket-Regular.ufont")
    $fontTarget = "../../../{0}/Content/SkylandsForaging/UI/Fonts/ChelseaMarket-Regular.ufont" -f $gameName

    if (-not (Test-Path -LiteralPath $fontStaging)) {
        throw "Merged font staging file not found: $fontStaging"
    }

    $responseLines = @(Get-Content -LiteralPath $responseFile)
    $fontResponseLine = '"{0}" "{1}"' -f $fontStaging, $fontTarget
    if ($responseLines -notcontains $fontResponseLine) {
        $responseLines += $fontResponseLine
        Set-Content -LiteralPath $responseFile -Value $responseLines -Encoding ASCII
    }

    $unrealPak = [string]$config.UnrealPakPath
    $retoc = [string]$config.RetocPath
    $pakOutput = Join-Path $outputDir ("{0}.pak" -f $packageName)
    $utocOutput = Join-Path $outputDir ("{0}.utoc" -f $packageName)
    $ucasOutput = Join-Path $outputDir ("{0}.ucas" -f $packageName)

    foreach ($path in @($pakOutput, $utocOutput, $ucasOutput)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
        }
    }

    & $unrealPak $pakOutput "-create=$responseFile"
    if ($LASTEXITCODE -ne 0) { throw "UnrealPak failed while adding the font" }
    & $retoc to-zen --version UE5_6 $pakOutput $utocOutput
    if ($LASTEXITCODE -ne 0) { throw "retoc failed while rebuilding the combined package" }

    if ($DeployToGame) {
        $gamePaksDir = [string]$config.GamePaksDir
        Copy-Item -LiteralPath $pakOutput -Destination (Join-Path $gamePaksDir (Split-Path -Leaf $pakOutput)) -Force
        Copy-Item -LiteralPath $utocOutput -Destination (Join-Path $gamePaksDir (Split-Path -Leaf $utocOutput)) -Force
        Copy-Item -LiteralPath $ucasOutput -Destination (Join-Path $gamePaksDir (Split-Path -Leaf $ucasOutput)) -Force
        Write-Host "Added merged Bulgarian font to the deployed localization package."
    }
}

if ($CreateZip) {
    $outputDir = Join-Path $workspaceRoot "pak-output"
    $zipPath = Join-Path $outputDir ("{0}.zip" -f [string]$config.PackageName)
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -LiteralPath @(
        (Join-Path $outputDir ("{0}.pak" -f [string]$config.PackageName)),
        (Join-Path $outputDir ("{0}.utoc" -f [string]$config.PackageName)),
        (Join-Path $outputDir ("{0}.ucas" -f [string]$config.PackageName))
    ) -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Host "Created release archive: $zipPath"
}
