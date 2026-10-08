param(
    [ValidateSet("auto", "csv", "json")]
    [string]$TranslationFormat = "auto",
    [string]$ConfigPath = "",
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = Split-Path -Parent $PSCommandPath
}
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $WorkspaceRoot "config\UELocKit.config.psd1"
}

$kitScript = "C:\WebStuff\UELocKit\build-locres.ps1"
if (-not (Test-Path -LiteralPath $kitScript)) {
    throw "UELocKit build script not found: $kitScript"
}

& $kitScript `
    -WorkspaceRoot $WorkspaceRoot `
    -ConfigPath $ConfigPath `
    -LocalizationTargetName "Game" `
    -CultureTag "bg" `
    -TranslationFormat $TranslationFormat

exit $LASTEXITCODE
