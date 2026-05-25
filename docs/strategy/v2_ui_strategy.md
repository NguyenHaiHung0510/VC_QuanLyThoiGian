# v2 UI Strategy

## Boi Canh

Flet UI v1 van la shell chay duoc. V2 can tach notes khoi tasks, sau do thay month grid bang continuous calendar co source filters.

## Quyet Dinh

- Refactor UI theo tung tab/workstream, khong rewrite full app.
- Notes UI duoc merge truoc vi giai quyet data pain lon nhat.
- Continuous calendar la WS6 va can strong model/Codex vi dung `main.py` nhieu.
- V1 code chi bi go bo sau khi cac tab chinh da chay bang PostgreSQL v2.

## Trade-off

- Giu Flet: it rui ro hon rewrite web, phu hop app ca nhan.
- Sua `main.py` dan dan: de conflict hon trong ngan han, nhung nhanh co UI dung duoc.
- Chua tach backend/frontend: tranh tang surface van hanh khi schema v2 moi on dinh.

## Tac Dong

- Moi UI moi phai dung service layer v2 thay vi query SQLite.
- UI docs khong duoc claim WS6 xong khi month grid cu van con.
- Notes khong can due date va khong hien nhu overdue task.

## Quality Gates

- Notes CRUD PostgreSQL pass tests.
- UI graceful error khi PostgreSQL unreachable.
- Calendar WS6 phai prefetch events theo range, khong query DB per day cell.
- Source filters phai an/hien theo `calendar_sources.is_visible`.
