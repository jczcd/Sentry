[CmdletBinding()]
param(
    [string]$Workspace = "",
    [string]$Output = ""
)

$scriptRoot = Split-Path -Parent $PSScriptRoot
if (-not $Workspace) {
    $Workspace = Split-Path -Parent $scriptRoot
}
$workspacePath = [IO.Path]::GetFullPath($Workspace).TrimEnd('\')
$parent = Split-Path -Parent $workspacePath
$name = Split-Path -Leaf $workspacePath
if (-not $Output) {
    $Output = Join-Path $parent "SentinelWorkspace.zip"
}
$outputPath = [IO.Path]::GetFullPath($Output)

if (Test-Path -LiteralPath $outputPath) {
    throw "Output already exists; move or rename it first: $outputPath"
}
if (-not (Get-Command tar.exe -ErrorAction SilentlyContinue)) {
    throw "Windows tar.exe is required."
}

& tar.exe -a -c -f $outputPath `
    --exclude="$name/ros2_ws/build" `
    --exclude="$name/ros2_ws/install" `
    --exclude="$name/ros2_ws/log" `
    --exclude="$name/isaac_sim/assets/legacy_4_1" `
    --exclude="$name/**/__pycache__" `
    -C $parent $name
if ($LASTEXITCODE -ne 0) {
    throw "tar.exe failed with exit code $LASTEXITCODE"
}
Write-Host "Created $outputPath"
