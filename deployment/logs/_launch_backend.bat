@echo off
cd /d "C:\Users\HomePC\Documents\GitHub\bt_management_system\deployment\..\backend"
"C:\Users\HomePC\Documents\GitHub\bt_management_system\deployment\..\backend\venv\Scripts\waitress-serve.exe" --listen=127.0.0.1:8000 --threads=4 config.wsgi:application >> "C:\Users\HomePC\Documents\GitHub\bt_management_system\deployment\logs\backend.log" 2>&1
