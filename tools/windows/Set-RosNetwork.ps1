[CmdletBinding()]
param(
    [int]$DomainId = 42,
    [string]$DiscoveryServer = "",
    [switch]$PersistForUser
)

$values = @{
    ROS_DOMAIN_ID       = "$DomainId"
    ROS_LOCALHOST_ONLY  = "0"
    RMW_IMPLEMENTATION  = "rmw_fastrtps_cpp"
    FASTRTPS_DEFAULT_PROFILES_FILE = (
        Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) `
            "config\fastdds.xml"
    )
}
if ($DiscoveryServer) {
    $values.ROS_DISCOVERY_SERVER = $DiscoveryServer
}

foreach ($entry in $values.GetEnumerator()) {
    Set-Item -Path "Env:$($entry.Key)" -Value $entry.Value
    if ($PersistForUser) {
        [Environment]::SetEnvironmentVariable(
            $entry.Key,
            $entry.Value,
            [EnvironmentVariableTarget]::User
        )
    }
}

Write-Host "ROS 2 network environment configured for this PowerShell process."
if ($PersistForUser) {
    Write-Host "It was also persisted for the current Windows user."
}
