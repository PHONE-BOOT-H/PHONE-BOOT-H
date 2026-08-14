@echo off
REM 카드 재생성 후 변경분만 커밋+푸시. Windows 작업 스케줄러가 하루 1회 실행.
cd /d "%~dp0"
python ai_usage_card.py cards\ai-usage.svg || exit /b 1
git diff --quiet -- cards\ai-usage.svg && exit /b 0
git add cards\ai-usage.svg
git commit -m "chore: AI Usage 카드 갱신" || exit /b 0
git push
