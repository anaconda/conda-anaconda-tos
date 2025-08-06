@echo off
if "%CONDA_PREFIX%"=="" (set _PREFIX="%PREFIX%") else (set "_PREFIX=%CONDA_PREFIX%")
"%_PREFIX%\python.exe" -m conda tos backup --max-age 604800 --all-locations >>"%_PREFIX%\.messages.txt" 2>&1
