@echo off
python scripts\build_vfs.py
if errorlevel 1 exit /b 1
python src\main.py ^
    --vfs "vfs\deep.zip" ^
    --log "logs\stage4.xml" ^
    --script "scripts\startup_stage4.txt"