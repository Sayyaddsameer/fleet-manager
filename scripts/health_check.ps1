# Windows Health Check Script

# Collect hostname
$hostName = $env:COMPUTERNAME

# Collect uptime in seconds
$os = Get-CimInstance -ClassName Win32_OperatingSystem
$lastBoot = $os.LastBootUpTime
$uptimeSpan = New-TimeSpan -Start $lastBoot -End (Get-Date)
$uptimeSeconds = [math]::Floor($uptimeSpan.TotalSeconds)

# Collect CPU usage percentage
$cpuItems = Get-CimInstance -ClassName Win32_Processor
$cpuUsage = ($cpuItems | Measure-Object -Property LoadPercentage -Average).Average
if ($null -eq $cpuUsage) {
    $cpuUsage = 0.0
}
$cpuUsage = [math]::Round($cpuUsage, 1)

# Collect free memory in MB
$freeMemoryKB = $os.FreePhysicalMemory
$freeMemoryMB = [math]::Round($freeMemoryKB / 1024, 0)

# Collect free disk space on C: drive in GB
$cVolume = Get-Volume -DriveLetter C
$freeDiskGB = [math]::Round($cVolume.SizeRemaining / 1GB, 1)

# Build the output object and convert to compressed JSON
$healthData = [ordered]@{
    os                  = "windows"
    hostname            = $hostName
    uptime_seconds      = $uptimeSeconds
    cpu_usage_percent   = $cpuUsage
    memory_free_mb      = $freeMemoryMB
    disk_free_c_drive_gb = $freeDiskGB
}

$healthData | ConvertTo-Json -Compress | Write-Output
