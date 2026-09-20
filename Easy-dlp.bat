@echo off
rem Launch without a console window when pythonw is available.
setlocal
cd /d "%~dp0"
where pythonw >nul 2>&1 && (start "" pythonw "app.py" & exit /b)
python "app.py"
