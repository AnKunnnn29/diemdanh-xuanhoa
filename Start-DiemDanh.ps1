param(
    [switch]$Lan,
    [switch]$Stop,
    [string]$PublicOrigin = '',
    [int]$Port = 8765,
    [ValidateSet('portable','native')][string]$GradeEngine = 'portable',
    [string]$DataRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
)
$ErrorActionPreference = 'Stop'
$bridgeState = Join-Path $PSScriptRoot '.local\bridge'
$pidFile = Join-Path $bridgeState 'service.json'
if (-not $Stop) { $resolvedRoot = (Resolve-Path -LiteralPath $DataRoot).Path }
if ($PublicOrigin) {
    $remoteUri = [Uri]$PublicOrigin
    if ($Lan -or $remoteUri.Scheme -ne 'https' -or $remoteUri.AbsolutePath -ne '/' -or $remoteUri.Query -or $remoteUri.Fragment -or $remoteUri.UserInfo -or $PublicOrigin -match '[\s"'';]') { throw 'PublicOrigin cần https://tên-miền, không có đường dẫn; dùng riêng với chế độ LAN.' }
    $PublicOrigin = $remoteUri.GetLeftPart([UriPartial]::Authority).ToLowerInvariant()
}
New-Item -ItemType Directory -Force -Path $bridgeState | Out-Null
if (Test-Path -LiteralPath $pidFile) {
    $saved = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    $ownedProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($saved.pid)"
    if ($ownedProcess -and $ownedProcess.CommandLine -like '*excel_bridge*server.py*') {
        if ($Stop) {
            # HTTP service process owns an isolated Excel instance; stop it through its interrupt endpoint.
            $controlHeaders = @{}
            $controlPath = Join-Path $(if ($saved.stateDir) { $saved.stateDir } else { $bridgeState }) 'control-token.txt'
            if (Test-Path -LiteralPath $controlPath) { $controlHeaders['X-Bridge-Control'] = (Get-Content -LiteralPath $controlPath -Raw).Trim() }
            Invoke-RestMethod -Method Post -Uri "$($saved.url)/api/shutdown" -ContentType 'application/json' -Headers $controlHeaders -Body '{}' -SkipCertificateCheck | Out-Null
            Wait-Process -Id $saved.pid -ErrorAction SilentlyContinue
            Write-Host 'Đã dừng dịch vụ điểm danh và đóng phiên Excel riêng.'
            exit
        }
        if ($saved.root -ne $resolvedRoot) {
            throw 'Dịch vụ đang dùng thư mục khác. Chạy ./Start-DiemDanh.ps1 -Stop rồi mở lại với -DataRoot đã chọn.'
        }
        if ($saved.gradeEngine -and $saved.gradeEngine -ne $GradeEngine) {
            throw 'Dịch vụ đang dùng bộ tính điểm khác. Dừng bằng -Stop rồi mở lại với -GradeEngine đã chọn.'
        }
        if ([string]$saved.publicOrigin -ne $PublicOrigin) { throw 'Chế độ tên miền đã thay đổi. Dừng dịch vụ bằng -Stop rồi mở lại.' }
        Start-Process $saved.url
        Write-Host "Dịch vụ đang chạy: $($saved.url)"
        exit
    }
}
if ($Stop) { Write-Host 'Dịch vụ hiện không chạy.'; exit }
$pythonCommand = (Get-Command python -ErrorAction Stop).Source
& $pythonCommand -c 'import openpyxl, oletools.olevba, win32com.client, cryptography, qrcode, lxml.etree, pymysql' 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Thiếu thư viện Python. Xem bước cài đặt trong README.md.' }
$defaultRoot = (Resolve-Path -LiteralPath (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)).Path
if ($resolvedRoot -ne $defaultRoot) {
    $rootHasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $rootHash = [Convert]::ToHexString($rootHasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($resolvedRoot.ToLowerInvariant()))).Substring(0,16).ToLowerInvariant()
    } finally { $rootHasher.Dispose() }
    $bridgeState = Join-Path $PSScriptRoot ".local\bridge-$rootHash"
    New-Item -ItemType Directory -Force -Path $bridgeState | Out-Null
}
$scriptPath = Join-Path $PSScriptRoot 'excel_bridge\server.py'
$arguments = @('"' + $scriptPath + '"', '--root', '"' + $resolvedRoot + '"', '--state-dir', '"' + $bridgeState + '"', '--port', "$Port")
$arguments += @('--grade-engine',$GradeEngine)
if ($Lan) { $arguments += '--lan' }
if ($PublicOrigin) { $arguments += @('--public-origin',$PublicOrigin) }
$url = "$(if ($Lan) {'https'} else {'http'})://localhost:$Port"
$service = Start-Process -FilePath $pythonCommand -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $bridgeState 'service.log') -RedirectStandardError (Join-Path $bridgeState 'error.log')
$limit = (Get-Date).AddSeconds(60)
do {
    Start-Sleep -Milliseconds 500
    if ($service.HasExited) { throw ('Dịch vụ chưa khởi động. ' + (Get-Content (Join-Path $bridgeState 'error.log') -Raw)) }
    $ready = (Test-Path (Join-Path $bridgeState 'service.log')) -and ((Get-Content (Join-Path $bridgeState 'service.log') -Raw) -like '*READY*')
} until ($ready -or (Get-Date) -gt $limit)
if (-not $ready) { throw 'Dịch vụ vẫn đang đọc dữ liệu. Kiểm tra .local\bridge\service.log.' }
@{pid=$service.Id;url=$url;root=$resolvedRoot;gradeEngine=$GradeEngine;stateDir=$bridgeState;publicOrigin=$PublicOrigin} | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding utf8
Write-Host "Mở điểm danh: $url"
if ($Lan) {
    Write-Host 'Điện thoại đăng nhập bằng tài khoản cá nhân do Admin cấp.'
    [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) | Where-Object AddressFamily -eq 'InterNetwork' | ForEach-Object { Write-Host "Điện thoại cùng Wi-Fi: https://$($_.IPAddressToString):$Port" }
    Write-Host 'Cài và tin cậy chứng chỉ .local\bridge\tls\XuanHoa-Certificate.cer theo README.md trước khi dùng camera.'
}
Start-Process $url
