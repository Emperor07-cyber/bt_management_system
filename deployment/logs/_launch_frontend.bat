@echo off
cd /d "C:\Users\HomePC\Documents\GitHub\bt_management_system\deployment\.."
"C:\Users\HomePC\Documents\GitHub\bt_management_system\deployment\..\backend\venv\Scripts\waitress-serve.exe" --listen=127.0.0.1:8080 --threads=2 deployment.serve_frontend:application >> "C:\Users\HomePC\Documents\GitHub\bt_management_system\deployment\logs\frontend.log" 2>&1
