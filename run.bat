@echo off
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
echo.
echo  JavaXd Massage ^& Spa Suite
echo  เปิดเบราว์เซอร์:  http://127.0.0.1:8088/login.html
echo  เจ้าของร้าน:      owner / Owner@2468
echo  API docs:         http://127.0.0.1:8088/docs
echo.
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8088
