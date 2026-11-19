@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Chay CAI_DAT_LAN_DAU.cmd truoc.
 pause
 exit /b 1
)
echo BAN THU DU LIEU GIA - KHONG NHAP KEY THAT.
echo Chi dung trong mang noi bo tin cay. Khong mo cong router ra Internet.
echo PC nay: http://localhost:8501
echo Dien thoai: cung Wi-Fi, mo http://IPv4-cua-PC:8501
echo Xem IPv4 cua may o ket qua ipconfig ben duoi.
ipconfig
.venv\Scripts\python.exe -c "from license_app.shared_test import shared_config; shared_config()"
if errorlevel 1 goto :fail
.venv\Scripts\python.exe -m streamlit run test_app.py --server.address 0.0.0.0 --server.port 8501 --browser.gatherUsageStats false
pause
exit /b 0
:fail
echo Khong khoi tao duoc du lieu thu. Khong xoa thu muc test-data; gui loi cho B.
pause
