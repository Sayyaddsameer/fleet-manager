# Windows Server Setup Script

Write-Output "Starting Windows server setup..."

# Create the C:\CompanyData directory if it does not exist
if (-not (Test-Path -Path "C:\CompanyData")) {
    New-Item -ItemType Directory -Path "C:\CompanyData" -Force | Out-Null
    Write-Output "Directory C:\CompanyData created."
} else {
    Write-Output "Directory C:\CompanyData already exists, skipping."
}

# Create the status file with the required content
Set-Content -Path "C:\CompanyData\status.txt" -Value "Initial setup complete."
Write-Output "Status file written to C:\CompanyData\status.txt."

# Create the svcaccount local user if it does not already exist
try {
    $existingUser = Get-LocalUser -Name "svcaccount" -ErrorAction Stop
    Write-Output "User svcaccount already exists, skipping creation."
} catch {
    $securePassword = ConvertTo-SecureString "P@ssw0rd2024!" -AsPlainText -Force
    New-LocalUser -Name "svcaccount" -Password $securePassword -Description "Service Account" -PasswordNeverExpires | Out-Null
    Write-Output "User svcaccount created."
}

Write-Output "Windows server setup complete."
