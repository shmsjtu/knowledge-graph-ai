@echo off
echo ====================================
echo Knowledge Graph AI Assistant
echo ====================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check dependencies
echo Checking dependencies...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install streamlit pyvis networkx openai python-dotenv
)

REM Start application
echo.
echo Starting Streamlit application...
echo.
streamlit run streamlit_app.py

pause
