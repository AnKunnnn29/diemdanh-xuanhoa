$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$target = Join-Path $projectRoot '.env.cloud.local'
if (Test-Path -LiteralPath $target) {
    Write-Host 'Existing .env.cloud.local preserved; no secret printed.'
    exit
}
$randomBytes = New-Object byte[] 48
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($randomBytes) } finally { $rng.Dispose() }
$sessionSecret = [Convert]::ToBase64String($randomBytes).TrimEnd('=').Replace('+','-').Replace('/','_')
$template = [IO.File]::ReadAllText((Join-Path $projectRoot '.env.cloud.example'))
[IO.File]::WriteAllText($target, $template.Replace('XH_SESSION_SECRET=', 'XH_SESSION_SECRET='+$sessionSecret), (New-Object Text.UTF8Encoding($false)))
Write-Host 'Prepared private .env.cloud.local. No secret printed. Do not upload this file.'
