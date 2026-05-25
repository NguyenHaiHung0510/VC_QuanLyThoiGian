# v1 Legacy Archive

Ban v1 duoc bao luu tren nhanh `main`. Khong can giu `develop` nhu dual-track v1/v2 nua.

Gia tri tham khao cua v1:
- Flet shell ban dau trong `main.py`.
- SQLite DAL trong `database.py`.
- Cach import ICS/Excel cu va JSON export cu.
- Cac docs cu viet boi Claude/agent, neu can doi chieu hanh vi app cu.

Quy tac hien tai:
- Khong sua `main`.
- Khong xoa `main.py`/`database.py` tren `develop` cho den khi WS6 va full UI v2 smoke test pass.
- Moi tai lieu top-level tren `develop` phai viet theo huong v2-first.
- Neu can xoa legacy runtime path, tao task rieng sau khi calendar/task/settings da chay on dinh voi PostgreSQL v2.
