@echo off
setlocal EnableDelayedExpansion
title Athena Installer

echo.
echo  =============================================
echo   Athena - Database Intelligence
echo  =============================================
echo.

:: Check Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Docker Desktop is not running.
    echo  Please start Docker Desktop and run this script again.
    echo.
    pause
    exit /b 1
)
echo  [OK] Docker Desktop is running

:: Check for .env
if not exist ".env" (
    if not exist ".env.example" (
        echo  ERROR: .env.example not found. Please re-download the package.
        pause
        exit /b 1
    )
    copy ".env.example" ".env" >nul
    echo.
    echo  Your OpenAI API key is required.
    echo  Get one at: https://platform.openai.com/api-keys
    echo.
    set /p APIKEY=" Enter your OpenAI API key (sk-...): "
    if "!APIKEY!"=="" (
        echo  ERROR: API key cannot be empty.
        pause
        exit /b 1
    )
    :: Write key into .env
    powershell -Command "(Get-Content .env) -replace 'OPENAI_API_KEY=sk-...', 'OPENAI_API_KEY=!APIKEY!' | Set-Content .env"
    echo  [OK] .env configured
) else (
    echo  [OK] .env already exists
)

:: Pull images
echo.
echo  Pulling Athena images (this may take a few minutes on first run)...
docker compose pull
if errorlevel 1 (
    echo  ERROR: Failed to pull images. Check your internet connection.
    pause
    exit /b 1
)
echo  [OK] Images ready

:: Start services
echo.
echo  Starting Athena...
docker compose up -d
if errorlevel 1 (
    echo  ERROR: Failed to start services.
    pause
    exit /b 1
)

:: Wait for startup
echo  Waiting for services to initialize...
timeout /t 8 /nobreak >nul

echo.
echo  =============================================
echo   Athena is running!
echo   Open: http://localhost:8080
echo  =============================================
echo.
echo  To stop Athena:  docker compose down
echo  To view logs:    docker compose logs -f
echo.

:: Open browser
start "" "http://localhost:8080"

pause
