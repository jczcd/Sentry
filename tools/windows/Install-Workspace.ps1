[CmdletBinding()]
param(
    [string]$Source = "",
    [string]$Target = "E:\RoboMaster\Sentinel\workspace",
    [switch]$Force
)

$scriptRoot = Split-Path -Parent $PSScriptRoot
$defaultSource = Split-Path -Parent $scriptRoot
if (-not $Source) {
    $Source = $defaultSource
}
$sourcePath = [IO.Path]::GetFullPath($Source)
$targetPath = [IO.Path]::GetFullPath($Target)

if ($sourcePath.TrimEnd('\') -eq $targetPath.TrimEnd('\')) {
    Write-Host "Workspace is already at $targetPath"
    exit 0
}
if (-not (Test-Path -LiteralPath (Join-Path $sourcePath "README.md"))) {
    throw "Source is not a Sentinel workspace: $sourcePath"
}
if ((Test-Path -LiteralPath $targetPath) -and -not $Force) {
    throw "Target exists. Inspect it first, or rerun with -Force: $targetPath"
}

New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
Get-ChildItem -LiteralPath $sourcePath -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName `
        -Destination $targetPath -Recurse -Force
}
Write-Host "Installed Sentinel workspace at $targetPath"
