@echo off
python scripts\build_vfs.py
if errorlevel 1 exit /b 1
python src\main.py ^
    --vfs "vfs\deep.zip" ^
    --log "logs\deep.xml" ^
    --script "scripts\startup_stage3.txt"