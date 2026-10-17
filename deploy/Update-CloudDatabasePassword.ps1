$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$configPath = Join-Path $projectRoot '.env.cloud.local'
$configLines = [IO.File]::ReadAllLines($configPath)
$uriLines = @($configLines | Where-Object { $_.StartsWith('XH_DATABASE_URL=') })
if ($uriLines.Count -ne 1) { throw 'Cần đúng một dòng XH_DATABASE_URL trong file cấu hình riêng.' }
$currentUri = $uriLines[0].Substring('XH_DATABASE_URL='.Length).Trim()
$parsed = [regex]::Match($currentUri, '^(postgresql(?:\+psycopg)?://[^:@/]+:)[^@]*(@[^/]+/.*)$')
if (-not $parsed.Success) { throw 'Chưa có URI pooler hợp lệ. Kiểm tra cấu hình riêng, không gửi mật khẩu vào chat.' }
$securePassword = Read-Host 'Nhập mật khẩu database mới vừa đặt trên Supabase (ẩn ký tự)' -AsSecureString
if ($securePassword.Length -eq 0) { throw 'Mật khẩu trống; giữ nguyên cấu hình.' }
$databasePassword = [Net.NetworkCredential]::new('', $securePassword).Password
try {
    $encodedPassword = [Uri]::EscapeDataString($databasePassword)
    $updatedUri = $parsed.Groups[1].Value + $encodedPassword + $parsed.Groups[2].Value
    $updatedLines = foreach ($line in $configLines) {
        if ($line.StartsWith('XH_DATABASE_URL=')) { 'XH_DATABASE_URL=' + $updatedUri } else { $line }
    }
    [IO.File]::WriteAllLines($configPath, [string[]]$updatedLines, [Text.UTF8Encoding]::new($false))
} finally {
    $databasePassword = $null
    $encodedPassword = $null
    $updatedUri = $null
    $securePassword.Dispose()
}
Write-Host 'Đã lưu mật khẩu mới trong cấu hình riêng; không in secret.'
Push-Location -LiteralPath $projectRoot
try {
    & (Join-Path $projectRoot '.local/cloud-venv/Scripts/python.exe') -m cloud_backend.manage check
    if ($LASTEXITCODE -ne 0) { throw 'Chưa kiểm tra được kết nối với mật khẩu mới.' }
} finally { Pop-Location }
