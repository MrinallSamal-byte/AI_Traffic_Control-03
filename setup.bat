@echo off
echo 🚀 Setting up Smart Transportation System development environment...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3 is required but not installed
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is required but not installed
    exit /b 1
)

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is required but not installed
    exit /b 1
)

echo ✅ Prerequisites check passed

REM Install Python dependencies
echo 📦 Installing Python dependencies...
pip install -r requirements.txt
pip install -r requirements-dev.txt

REM Install frontend dependencies
echo 📦 Installing frontend dependencies...
cd frontend
npm ci
cd ..

REM Install pre-commit hooks
echo 🔧 Setting up pre-commit hooks...
pre-commit install

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env
)

echo 🎉 Setup complete! You can now run:
echo   make dev     # Start development environment
echo   make test    # Run tests
echo   make lint    # Run linters