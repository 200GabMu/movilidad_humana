@echo off
REM Doble clic para instalar (la primera vez) y abrir la app en el navegador.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno e instalando dependencias, espera un momento...
    python -m venv .venv || (echo No se encontro Python. Instala Python 3.11+ desde python.org marcando "Add to PATH". & pause & exit /b 1)
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
