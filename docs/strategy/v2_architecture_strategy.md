# v2 Architecture Strategy

## Boi Canh

microSchedule v1 la Flet desktop app du dung ca nhan, nhung tight coupling UI + SQLite lam kho them import versioning, notes rieng, backup PostgreSQL va AI agent/tools.

## Quyet Dinh

- `develop` la dong v2.
- PostgreSQL `microschedule_v2` la data store chinh.
- App van giu Flet desktop shell trong giai doan refactor.
- Service layer trong `app/` la noi dat business logic moi.
- `main` bao luu v1, khong dong vao.

## Trade-off

- Khong rewrite full web/backend ngay: giam rui ro va giu app dung duoc.
- Khong xoa `main.py`/`database.py` ngay: tranh pha UI shell khi WS6 chua xong.
- Chuyen docs sang v2-first ngay: giam nham lan cho agent.

## Tac Dong

- Tier 2 phai dung `app/db/schema.sql` va service layer v2 lam source of truth.
- Code legacy chi duoc xem nhu shell/runtime tam thoi.
- Moi tinh nang moi tren `develop` phai uu tien PostgreSQL v2.

## Quality Gates

- `python -m pytest` pass.
- Khong hardcode secret.
- Khong sua SQLite v1.
- Moi docs top-level phai noi ro trang thai v2 hien tai, khong claim tinh nang chua merge.
