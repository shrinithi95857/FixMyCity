@echo off
echo Starting FixMyCity Application...
echo.

echo Starting Backend Server...
cd backend
start "FixMyCity Backend" cmd /k "python app.py"
cd ..

timeout /t 3 /nobreak >nul

echo Starting Frontend Application...
cd frontend
start "FixMyCity Frontend" cmd /k "streamlit run main.py"
cd ..

echo.
echo FixMyCity is now running!
echo Backend: http://127.0.0.1:5000
echo Frontend: http://localhost:8501 (or check the Streamlit window for exact port)
echo.
echo Close this window to stop both applications.
pause