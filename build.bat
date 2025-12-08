@echo off
ECHO Bat dau qua trinh build...

REM Kich hoat moi truong ao
CALL .\venv\Scripts\activate

REM Cai dat cac thu vien tu requirements.txt
ECHO Dang cai dat cac thu vien tu requirements.txt...
pip install -r requirements.txt

REM Chay lenh build cua PyInstaller (su dung python -m de dam bao)
ECHO Dang chay PyInstaller...
python -m PyInstaller microSchedule.spec

ECHO Qua trinh build da hoan tat. Nhan phim bat ky de dong cua so.
pause
