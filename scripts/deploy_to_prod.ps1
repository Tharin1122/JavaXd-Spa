# ===== Deploy UAT -> PROD =====
# กติกา: deploy ได้เฉพาะเมื่อ pytest ผ่านครบ — สคริปต์รันเทสให้ก่อนเสมอ ไม่ผ่าน = ไม่ปล่อย
# ใช้: powershell -ExecutionPolicy Bypass -File scripts\deploy_to_prod.ps1
$uat  = "C:\Users\ACER\Desktop\Project Tharin Dav By claude\Obsidian\projects\spa-mms"
$prod = "C:\Users\ACER\Desktop\Project Tharin Dav By claude\Obsidian\projects\spa-mms-prod"

Write-Host "[1/3] รันเทสบน UAT ก่อน deploy..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = "utf-8"
Set-Location $uat
& "$uat\.venv\Scripts\python.exe" -m pytest tests -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] เทสไม่ผ่าน — ยกเลิก deploy (แก้ให้เขียวก่อน)" -ForegroundColor Red
    exit 1
}

Write-Host "[2/3] คัดลอกโค้ด UAT -> PROD (ไม่แตะ DB ของ prod)..." -ForegroundColor Cyan
robocopy $uat $prod /E /XD .venv __pycache__ .pytest_cache /XF *.db *.db-journal /NFL /NDL /NJH | Out-Null
if ($LASTEXITCODE -ge 8) { Write-Host "[X] คัดลอกล้มเหลว (robocopy=$LASTEXITCODE)" -ForegroundColor Red; exit 1 }

# run.bat ของ prod ต้องคงพอร์ต 8089 เสมอ (กันโดนทับด้วยของ UAT ที่เป็น 8088)
$rb = Join-Path $prod "run.bat"
(Get-Content $rb -Raw -Encoding utf8) -replace '8088', '8089' | Set-Content $rb -Encoding utf8

Write-Host "[3/3] เสร็จ — รีสตาร์ทเซิร์ฟเวอร์ prod (พอร์ต 8089) เพื่อให้โค้ดใหม่ทำงาน" -ForegroundColor Green
Write-Host "    เทสผ่านแล้วเท่านั้นที่มาถึงบรรทัดนี้ | DB ของ prod ไม่ถูกแตะ"
