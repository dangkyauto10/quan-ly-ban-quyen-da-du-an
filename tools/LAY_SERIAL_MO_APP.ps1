# Portable USB helper: read only this PC's motherboard serial and open the app.
# It installs nothing, starts no listener, and stores no account credentials.
$ErrorActionPreference = 'Stop'
$appUrl = 'https://quan-ly-ban-quyen-da-du-an-t7yqeumld4e9pkwgwaekpl.streamlit.app/'

try {
    $board = Get-CimInstance -ClassName Win32_BaseBoard
    $serial = ([string]$board.SerialNumber).Trim()
    if (-not $serial -or $serial.ToUpperInvariant() -in @('DEFAULT STRING', 'TO BE FILLED BY O.E.M.', 'UNKNOWN', 'NONE', 'N/A')) {
        throw 'Windows không trả serial mainboard hợp lệ. Hãy kiểm tra BIOS hoặc tem vật lý.'
    }

    $uri = [System.UriBuilder]::new($appUrl)
    $uri.Query = 'board_serial=' + [System.Uri]::EscapeDataString($serial)
    Write-Host 'Đã đọc serial mainboard:' $serial -ForegroundColor Green
    Write-Host 'Đang mở KEY BẢN QUYỀN. Đăng nhập tài khoản KTV nếu app yêu cầu.'
    Write-Host 'Trong app, chọn đúng PC được giao và xác nhận gắn serial này.'
    Start-Process $uri.Uri.AbsoluteUri
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Read-Host 'Nhấn Enter để đóng tiện ích'
