param(
    [string]$PackageName = "SkylandsForaging-Font_P",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $workspaceRoot "pak-output"
}

$pakPath = Join-Path $OutputDir ("{0}.pak" -f $PackageName)
$noticePath = Join-Path $workspaceRoot "licenses\ThirdPartyNotices-Font.txt"
$oflSource = "C:\WebStuff\Bmfont\Playpen_Sans\OFL.txt"
$archiveRoot = Join-Path $workspaceRoot "release-staging\SkylandsForaging-Font_P"
$archivePath = Join-Path $OutputDir ("{0}.zip" -f $PackageName)

foreach ($required in @($pakPath, $noticePath, $oflSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing archive input: $required"
    }
}

if (Test-Path -LiteralPath $archiveRoot) {
    Remove-Item -LiteralPath $archiveRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $archiveRoot | Out-Null
Copy-Item -LiteralPath $pakPath -Destination (Join-Path $archiveRoot (Split-Path -Leaf $pakPath))
Copy-Item -LiteralPath $noticePath -Destination (Join-Path $archiveRoot "ThirdPartyNotices.txt")
Copy-Item -LiteralPath $oflSource -Destination (Join-Path $archiveRoot "OFL-1.1.txt")

if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
Compress-Archive -Path (Join-Path $archiveRoot '*') -DestinationPath $archivePath -CompressionLevel Optimal
Write-Host "Created font sharing archive: $archivePath"
