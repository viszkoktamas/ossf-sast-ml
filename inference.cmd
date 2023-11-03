@echo off
call inference\venv\Scripts\activate.bat >nul 2>&1
call python inference\inference.py -i %1
