@echo off
echo ==========================================
echo Starting Monthly MTG Meta Data Update...
echo ==========================================

cd /d "%~dp0"

echo 1. Fetching new matchup matrices from MTGDecks...
python scripts\fetch_mtgdecks_matrices.py

echo 2. Updating top decklists...
python scripts\scrape_decklists.py

echo 3. Creating monthly historical snapshot...
python scripts\snapshot_history.py

echo ==========================================
echo Data update and backup complete!
echo ==========================================
pause
