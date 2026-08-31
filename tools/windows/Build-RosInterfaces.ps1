[CmdletBinding()]
param(
    [string]$Workspace = ""
)

$scriptRoot = Split-Path -Parent $PSScriptRoot
if (-not $Workspace) {
    $Workspace = Split-Path -Parent $scriptRoot
}
$workspacePath = [IO.Path]::GetFullPath($Workspace)

if (-not (Get-Command ros2 -ErrorAction SilentlyContinue)) {
    throw "Source a ROS 2 Windows/Pixi environment before running this script."
}
if (-not (Get-Command colcon -ErrorAction SilentlyContinue)) {
    throw "colcon is not available in this PowerShell environment."
}

Push-Location (Join-Path $workspacePath "ros2_ws")
try {
    colcon build --merge-install --packages-select sentinel_interfaces
    if ($LASTEXITCODE -ne 0) {
        throw "colcon failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
Write-Host "Built sentinel_interfaces for Windows."
