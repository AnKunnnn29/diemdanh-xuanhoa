$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.local/cloud-venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Không tìm thấy Python của dự án tại .local/cloud-venv/Scripts/python.exe.'
}
& $pythonPath -X utf8 (Join-Path $PSScriptRoot 'export-login-list.py')
if ($LASTEXITCODE -ne 0) {
    throw 'Xuất danh sách thất bại; kiểm tra cấu hình cloud và kết nối mạng.'
}
