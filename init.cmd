call pip install virtualenv
call python -m venv inference\venv
call inference\venv\Scripts\activate.bat
call pip install -r inference\requirements.txt
