@echo off
call %~dp0\inference\venv\Scripts\activate.bat >nul 2>&1
IF "%~2"=="" (
    call python %~dp0\inference\inference.py -i %1
) ELSE (
    IF "%~3"=="" (
        call python %~dp0\inference\inference.py -i %1 -m %2
    ) ELSE (
        call python %~dp0\inference\inference.py -i %1 -m %2 -r %3
    )
)
