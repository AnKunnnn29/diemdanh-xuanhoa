param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [Parameter(Mandatory=$true)][string]$RecipientFile,
    [string]$EnvFile,
    [string]$AgeDirectory
)
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
if (-not $EnvFile) { $EnvFile = Join-Path $projectDirectory '.env.cloud.local' }
if ($AgeDirectory) {
    $env:PATH = (Resolve-Path -LiteralPath $AgeDirectory).Path + [IO.Path]::PathSeparator + $env:PATH
}
$backupRecipient = (Get-Content -LiteralPath $RecipientFile -Raw).Trim()
if ($backupRecipient -notmatch '^age1[a-z0-9]+$') { throw 'Recipient file must contain a public age recipient only.' }
$destinationDirectory = [IO.Path]::GetFullPath($OutputDirectory)
[IO.Directory]::CreateDirectory($destinationDirectory) | Out-Null
$backupName = 'XuanHoa-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8) + '.age'
$backupFile = Join-Path $destinationDirectory $backupName
$pythonExecutable = Join-Path $projectDirectory '.local\cloud-venv\Scripts\python.exe'
Push-Location -LiteralPath $projectDirectory
try {
    & $pythonExecutable -X utf8 -m cloud_backend.secure_backup backup --env-file $EnvFile --recipient $backupRecipient --output $backupFile
    if ($LASTEXITCODE -ne 0) { throw 'Encrypted backup failed. No success status recorded.' }
    $backupStatus = @{ successfulAtUtc=[DateTime]::UtcNow.ToString('o'); file=$backupName; bytes=(Get-Item -LiteralPath $backupFile).Length }
    $backupStatus | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $destinationDirectory 'last-success.json') -Encoding utf8
} finally {
    Pop-Location
}
# Scheduling/upload/retention are intentionally configured by the operator for
# their selected always-on runner and protected off-site destination.
