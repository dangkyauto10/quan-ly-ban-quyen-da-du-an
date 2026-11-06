@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Chay CAI_DAT_LAN_DAU.cmd truoc.
 pause
 exit /b 1
)
set "APP_MODE=activation_demo"
set "LICENSE_TEST_DATA_DIR=%~dp0activation-test-data"
echo MO PHONG KICH HOAT - chi du lieu gia, khong ket noi Microsoft.
echo PC va dien thoai cung Wi-Fi co the mo cung moi truong thu.
echo Khong dung key that. Khong mo cong router ra Internet.
echo PC: http://localhost:8502
echo Dia chi IPv4 cua PC:
ipconfig
.venv\Scripts\python.exe -m streamlit run activation_test_app.py --server.address 0.0.0.0 --server.port 8502 --browser.gatherUsageStats false
pause
