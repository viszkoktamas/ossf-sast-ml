@echo off
call %~dp0\inference\venv\Scripts\activate.bat >nul 2>&1
call python %~dp0\inference\inference.py -i %1
