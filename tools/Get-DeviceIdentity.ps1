# Read-only local helper: no network request, no activation or policy changes.
$ErrorActionPreference = 'Stop'
$bios = Get-CimInstance Win32_BIOS
$board = Get-CimInstance Win32_BaseBoard
$pc = Get-CimInstance Win32_ComputerSystem
[PSCustomObject]@{
    Manufacturer = $pc.Manufacturer
    Model = $pc.Model
    ComputerSerial = $bios.SerialNumber
    MainboardSerial = $board.SerialNumber
} | Format-List
Write-Host 'Verify blank/default serials against physical labels. No data was uploaded.'
Read-Host 'Press Enter to close'
