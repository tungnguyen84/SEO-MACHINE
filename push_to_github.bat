@echo off
chcp 65001 >nul
echo ============================================================
echo   OPENSEO / SEO-MACHINE - DONG BO CODE LEN GITHUB
echo   Repo: https://github.com/tungnguyen84/SEO-MACHINE
echo ============================================================

set msg=%~1
if "%msg%"=="" set msg=update: cai tien ma nguon va toi uu tinh nang

echo [1/3] Kiem tra trang thai Git...
git status --short

echo [2/3] Dang stage va commit cac thay doi...
git add .
git commit -m "%msg%"

echo [3/3] Dang push len nhanh main cua GitHub...
git push origin main

echo.
echo ============================================================
echo   DA PUSH CODE THANH CONG LEN GITHUB!
echo   ChatGPT hoac audit bot da co the truy cap:
echo   https://github.com/tungnguyen84/SEO-MACHINE
echo ============================================================
pause
