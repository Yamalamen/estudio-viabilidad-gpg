@echo off
chcp 65001 >nul
title Avisos Mantenimiento Judicial

echo.
echo =========================================================
echo   AVISOS MANTENIMIENTO - SEDES JUDICIALES ALICANTE
echo   Abriendo la aplicacion...
echo =========================================================
echo.
echo La app se abrira en tu navegador en unos segundos.
echo Para cerrarla, cierra esta ventana negra.
echo.

streamlit run app.py --server.headless false --browser.gatherUsageStats false

pause
