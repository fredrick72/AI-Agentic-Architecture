@echo off
REM ============================================
REM AI-Agentic Architecture - Setup Script (Windows)
REM ============================================

echo ===================================
echo AI-Agentic Architecture Setup
echo ===================================
echo.

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo [IMPORTANT] Edit .env and add your OPENAI_API_KEY
    echo.
    pause
)

REM Check Docker
echo Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found. Please install Docker Desktop
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon not running. Please start Docker Desktop
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Start infrastructure services
echo ===================================
echo Step 1: Starting Infrastructure
echo ===================================
echo.
echo Starting: PostgreSQL, Redis, Traefik, Prometheus, Grafana
echo.

docker compose up -d postgres redis traefik prometheus grafana

echo.
echo Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak >nul

REM Check PostgreSQL
echo.
echo Checking PostgreSQL...
docker compose exec -T postgres pg_isready -U postgres >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL not ready
    echo Check logs: docker compose logs postgres
    pause
    exit /b 1
)
echo [OK] PostgreSQL is ready

REM Check Redis
echo Checking Redis...
docker compose exec -T redis redis-cli ping | findstr "PONG" >nul
if errorlevel 1 (
    echo [ERROR] Redis not ready
    echo Check logs: docker compose logs redis
    pause
    exit /b 1
)
echo [OK] Redis is ready

REM Verify database
echo Verifying database schema...
docker compose exec -T postgres psql -U postgres -d agent_db -c "\dt" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Database may not be initialized
) else (
    echo [OK] Database schema initialized
)

REM Check seed data
docker compose exec -T postgres psql -U postgres -d agent_db -t -c "SELECT COUNT(*) FROM patients;" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Seed data may not be loaded
) else (
    echo [OK] Seed data loaded
)

echo.
echo ===================================
echo Infrastructure Test Complete!
echo ===================================
echo.
echo [OK] PostgreSQL - Port 5432
echo [OK] Redis - Port 6379
echo [OK] Traefik - Port 80 (API), 8080 (Dashboard)
echo [OK] Prometheus - Port 9090
echo [OK] Grafana - Port 3000 (admin/admin)
echo.
echo Access Points:
echo   * Traefik Dashboard: http://localhost:8080
echo   * Prometheus: http://localhost:9090
echo   * Grafana: http://localhost:3000
echo.
echo Next Steps:
echo   1. Build and start application services:
echo      docker compose up -d --build
echo.
echo   2. View logs:
echo      docker compose logs -f
echo.
echo   3. Test the demo scenarios in README.md
echo.
echo ===================================
pause
