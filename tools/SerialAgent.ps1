# Read-only local bridge for the KTV app. It exposes only the motherboard serial.
# It binds to loopback, accepts only the KEY BẢN QUYỀN preview origin, and runs no remote commands.
$ErrorActionPreference = 'Stop'
$allowedOrigin = 'https://quan-ly-ban-quyen-da-du-an-t7yqeumld4e9pkwgwaekpl.streamlit.app'
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add('http://127.0.0.1:8765/')

function Send-Json($response, [int]$status, $body, $origin) {
    $response.StatusCode = $status
    $response.ContentType = 'application/json; charset=utf-8'
    $response.Headers['Cache-Control'] = 'no-store'
    $response.Headers['Vary'] = 'Origin'
    if ($origin -eq $allowedOrigin) {
        $response.Headers['Access-Control-Allow-Origin'] = $allowedOrigin
        $response.Headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($body | ConvertTo-Json -Compress))
    $response.ContentLength64 = $bytes.Length
    $response.OutputStream.Write($bytes, 0, $bytes.Length)
    $response.Close()
}

try {
    $listener.Start()
    Write-Host 'Cong cu doc serial mainboard dang chay tai 127.0.0.1:8765.' -ForegroundColor Green
    Write-Host 'Quay lai app, chon viec cua PC nay va bam Doc serial mainboard.'
    Write-Host 'Chi doc serial; khong gui du lieu ra ngoai, khong chay lenh tu app.'
    Write-Host 'Dong cua so nay de dung cong cu.'
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        $origin = $request.Headers['Origin']
        $path = $request.Url.AbsolutePath

        if ($origin -ne $allowedOrigin) {
            Send-Json $response 403 @{ ok = $false; error = 'Nguon truy cap khong duoc phep.' } $origin
            continue
        }
        if ($request.HttpMethod -eq 'OPTIONS') {
            $response.StatusCode = 204
            $response.Headers['Access-Control-Allow-Origin'] = $allowedOrigin
            $response.Headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            $response.Headers['Access-Control-Max-Age'] = '60'
            $response.Close()
            continue
        }
        if ($request.HttpMethod -ne 'GET') {
            Send-Json $response 405 @{ ok = $false; error = 'Phuong thuc khong ho tro.' } $origin
            continue
        }
        if ($path -eq '/health') {
            Send-Json $response 200 @{ ok = $true } $origin
            continue
        }
        if ($path -ne '/serial') {
            Send-Json $response 404 @{ ok = $false; error = 'Khong tim thay tac vu.' } $origin
            continue
        }

        try {
            $board = Get-CimInstance -ClassName Win32_BaseBoard
            $serial = ([string]$board.SerialNumber).Trim()
            if (-not $serial -or $serial.ToUpperInvariant() -in @('DEFAULT STRING', 'TO BE FILLED BY O.E.M.', 'UNKNOWN', 'NONE', 'N/A')) {
                Send-Json $response 422 @{ ok = $false; error = 'Mainboard khong tra serial hop le; hay doi chieu BIOS/tem vat ly.' } $origin
            } else {
                Send-Json $response 200 @{ ok = $true; serial = $serial; manufacturer = [string]$board.Manufacturer; product = [string]$board.Product } $origin
            }
        } catch {
            Send-Json $response 500 @{ ok = $false; error = 'Windows khong doc duoc serial mainboard.' } $origin
        }
    }
} finally {
    if ($listener.IsListening) { $listener.Stop() }
    $listener.Close()
}
