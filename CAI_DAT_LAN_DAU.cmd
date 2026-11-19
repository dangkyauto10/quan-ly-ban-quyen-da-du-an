@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
 echo Can cai Python 3.12 tu python.org, sau do chay lai tep nay.
 pause
 exit /b 1
)
py -3.12 -m venv .venv
if errorlevel 1 goto :fail
.venv\Scripts\python.exe -m pip install -r requirements-v2.txt
if errorlevel 1 goto :fail
echo Cai dat xong. Chay MO_APP_TEST.cmd de mo app.
pause
exit /b 0
:fail
echo Cai dat chua thanh cong. Chup thong bao loi gui B.
pause
exit /b 1
