@echo off
REM Windows batch script to train ML model

echo.
echo ========================================
echo   Smart Agri Cloud - ML Training
echo ========================================
echo.

cd /d D:\Test\smart-agri-cloud\ml

REM Check if dataset exists
if not exist "data\crop_recommendation.csv" (
    echo.
    echo ERROR: Dataset not found at: data\crop_recommendation.csv
    echo.
    echo Please download from:
    echo   https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset
    echo.
    echo Then place the CSV file at:
    echo   D:\Test\smart-agri-cloud\ml\data\crop_recommendation.csv
    echo.
    pause
    exit /b 1
)

echo Checking dependencies...
pip install -q pandas scikit-learn joblib numpy 2>nul

echo.
echo Starting ML model training...
echo.

python train.py

if errorlevel 1 (
    echo.
    echo ERROR: Training failed!
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Training Completed Successfully!
echo ========================================
echo.
echo Model saved to: models\crop_rf.joblib
echo.
echo Next steps:
echo   1. Restart API: docker compose restart api
echo   2. Test: Visit http://localhost:8501
echo   3. Push to GitHub
echo.
pause
