@echo off
chcp 65001 >nul
title Instalador - Avisos Mantenimiento Judicial

echo.
echo =========================================================
echo   AVISOS MANTENIMIENTO - SEDES JUDICIALES ALICANTE
echo   Instalador automatico para Windows
echo =========================================================
echo.

REM Verificar que Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado.
    echo.
    echo Por favor descarga Python desde: https://www.python.org/downloads/
    echo IMPORTANTE: Durante la instalacion marca la casilla "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo Python encontrado:
python --version
echo.

REM Actualizar pip
echo Actualizando pip...
python -m pip install --upgrade pip --quiet

REM Instalar dependencias
echo Instalando librerias necesarias (puede tardar unos minutos)...
pip install streamlit>=1.32.0 --quiet
pip install streamlit-authenticator==0.3.3 --quiet
pip install streamlit-aggrid>=0.3.4 --quiet
pip install pandas>=2.0.0 --quiet
pip install openpyxl>=3.1.0 --quiet
pip install apscheduler>=3.10.0 --quiet
pip install bcrypt>=4.0.0 --quiet
pip install pyyaml --quiet

echo.
echo Instalacion completada.
echo.
echo =========================================================
echo   Iniciando la aplicacion...
echo   Se abrira automaticamente en tu navegador.
echo   Para cerrar la app, cierra esta ventana.
echo =========================================================
echo.

streamlit run app.py --server.headless false --browser.gatherUsageStats false

pause
