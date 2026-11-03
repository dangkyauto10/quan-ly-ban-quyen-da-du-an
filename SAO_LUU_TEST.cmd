@echo off
cd /d "%~dp0"
echo Dung app bang Ctrl+C tai cua so MO_APP_TEST truoc khi sao luu.
echo Khi da dung, bam phim bat ky de tiep tuc.
pause >nul
powershell -NoProfile -Command "$name='backup-test-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.zip'; Compress-Archive -Path 'test-data' -DestinationPath $name -ErrorAction Stop; Write-Host $name"
pause
