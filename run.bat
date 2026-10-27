@echo off

cd /d "%~dp0\data"
git pull

cd /d "%~dp0"
uv run streamlit run main.py

cd /d "%~dp0\data"
call gitpush.bat
