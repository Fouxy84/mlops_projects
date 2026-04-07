@echo off
REM ====================================
REM Dashboard Streamlit - Setup & Run
REM ====================================

echo.
echo ========================================
echo    MLOps Dashboard - Rakuten Challenge
echo ========================================
echo.

setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..

echo [1/5] Verification des prerequis...

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python non trouve. Installez Python 3.9+
    pause
    exit /b 1
)
echo ✅ Python trouve

pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip non trouve
    pause
    exit /b 1
)
echo ✅ pip trouve

echo.
echo [3/5] Installation des packages...


pip install -r "%ROOT_DIR%\requirements.txt" --quiet
pip install streamlit>=1.28.0 plotly requests --quiet
echo ✅ Packages installes

echo.
echo [4/5] Verification de la configuration...

if not exist "%SCRIPT_DIR%\.streamlit" (
    mkdir "%SCRIPT_DIR%\.streamlit"
)

if not exist "%SCRIPT_DIR%\.streamlit\config.toml" (
    echo Création de la configuration Streamlit...
    (
        echo [theme]
        echo primaryColor = "#667eea"
        echo backgroundColor = "#f0f2f6"
        echo.
        echo [server]
        echo headless = true
        echo port = 8501
    ) > "%SCRIPT_DIR%\.streamlit\config.toml"
    echo ✅ Configuration creee
) else (
    echo ✅ Configuration trouvee
)

echo.
echo [5/5] Lancement de l'application...
echo.

cd "%SCRIPT_DIR%"
echo Streamlit démarre sur: http://localhost:8501
echo.
echo Comptes de test:
echo  - admin / admin123
echo  - scientist / scientist123
echo  - user / user123
echo.

streamlit run streamlit_rakuten.py --server.port 8501

echo.
echo Application fermée
echo ========================================
pause

