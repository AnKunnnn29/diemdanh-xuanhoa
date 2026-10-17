param(
    [Parameter(Mandatory)][string]$Hostname,
    [Parameter(Mandatory)][Guid]$TunnelId,
    [Parameter(Mandatory)][string]$CredentialsFile,
    [ValidateRange(1024,65535)][int]$Port=8765
)
$ErrorActionPreference='Stop'
$remoteProject=Split-Path $PSScriptRoot -Parent
$remoteHostname=$Hostname.ToLowerInvariant()
if ($remoteHostname -notmatch '^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$') { throw 'Nhập tên miền đầy đủ, không có https:// hoặc đường dẫn.' }
if ($TunnelId -eq [Guid]::Empty) { throw 'Thay UUID mẫu bằng tunnel thật.' }
$remoteCredentials=(Resolve-Path -LiteralPath $CredentialsFile).Path
if ($remoteCredentials -match '[\r\n]') { throw 'Đường dẫn credentials không hợp lệ.' }
$remoteConfigFolder=Join-Path $remoteProject '.local/remote'
New-Item -ItemType Directory -Force -Path $remoteConfigFolder | Out-Null
$remoteConfig=Join-Path $remoteConfigFolder 'config.yml'
$remoteCredentialYaml=$remoteCredentials.Replace('\','/').Replace("'","''")
$remoteYaml=@"
tunnel: $TunnelId
credentials-file: '$remoteCredentialYaml'
ingress:
  - hostname: $remoteHostname
    service: http://127.0.0.1:$Port
    originRequest:
      httpHostHeader: $remoteHostname
      connectTimeout: 10s
  - service: http_status:404
"@
Set-Content -LiteralPath $remoteConfig -Value $remoteYaml -Encoding utf8
Write-Host "Đã tạo cấu hình: $remoteConfig"
Write-Host "Ứng dụng: ./Start-DiemDanh.ps1 -PublicOrigin https://$remoteHostname -Port $Port"
if (Get-Command cloudflared -ErrorAction SilentlyContinue) {
    & cloudflared tunnel --config $remoteConfig ingress validate
    if ($LASTEXITCODE -ne 0) { throw 'Cấu hình tunnel chưa hợp lệ.' }
} else { Write-Host 'Chưa cài cloudflared; xem REMOTE-ACCESS.md.' }
Write-Host 'Chưa tạo DNS hay kết nối công khai. Thực hiện các bước trong REMOTE-ACCESS.md khi sẵn sàng.'
