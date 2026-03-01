@echo off
echo ==========================================
echo Starting Monthly MTG Meta Data Update...
echo ==========================================

cd /d "%~dp0"

echo 1. Fetching matrices and updating historization...
python scripts\update_data_monthly.py

echo 2. Updating top decklists...
python scripts\scrape_decklists.py

echo ==========================================
echo Data update and backup complete!
echo ==========================================
pause
