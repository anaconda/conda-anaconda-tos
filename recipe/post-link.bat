@echo off
if "%CONDA_PREFIX%"=="" (set _PREFIX="%PREFIX%") else (set "_PREFIX=%CONDA_PREFIX%")
"%_PREFIX%\python.exe" -m conda tos restore >>"%_PREFIX%\.messages.txt" 2>&1
