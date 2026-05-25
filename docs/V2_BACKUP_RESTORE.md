# Hướng dẫn Backup & Restore PostgreSQL - microSchedule v2

Tài liệu này hướng dẫn cách cấu hình, vận hành hệ thống sao lưu tự động (Backup) và quy trình khôi phục dữ liệu (Restore) cho PostgreSQL v2 của dự án `microSchedule`.

---

## 1. Cấu Hình Hệ Thống Backup

Hệ thống backup đọc các tham số cấu hình từ file `.env` đặt tại thư mục gốc của dự án:

* **`DATABASE_URL`**: Đường dẫn kết nối database PostgreSQL.
  * Định dạng: `postgresql://<user>:<password>@<host>:<port>/<dbname>`
  * Ví dụ: `postgresql://postgres:<password>@localhost:5432/microschedule_v2`
* **`MICROSCHEDULE_DATA_DIR`**: Thư mục dữ liệu v2 của ứng dụng.
  * Ví dụ: `C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2`
* **`MICROSCHEDULE_BACKUP_DIR`** *(Tùy chọn)*: Đường dẫn cụ thể tới thư mục lưu trữ backup. Nếu không cấu hình, mặc định sẽ lưu tại `{MICROSCHEDULE_DATA_DIR}\backups`.

> [!NOTE]
> Thư mục `C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2` đã được cấu hình đồng bộ trực tiếp lên Google Drive. Do đó, các file backup sinh ra tại đây sẽ được tự động đồng bộ lên đám mây nhằm đảm bảo an toàn tối đa.

---

## 2. Cơ Chế Sao Lưu (Backup Policy)

Dịch vụ `BackupService` trong `app/services/backup_service.py` thực thi các bước sau một cách tự động khi được gọi:

1. **Sao lưu nguyên tử (Atomic Write)**:
   * Chạy lệnh `pg_dump -F c -b -f <temp_file> <database>` để xuất dữ liệu ra một file tạm dạng `temp_backup_YYYYMMDD_HHMMSS_*.dump`.
   * Sử dụng biến môi trường `PGPASSWORD` để truyền mật khẩu kết nối một cách an toàn cho tiến trình `pg_dump` mà không bị lộ trên dòng lệnh.
   * Sau khi xuất thành công, đổi tên file tạm thành file chính thức dạng `backup_YYYYMMDD_HHMMSS.dump`. Điều này giúp Google Drive không đồng bộ hóa các file đang ghi dở dang.

2. **Chính sách Retention (Lưu trữ và Dọn dẹp)**:
   * **Quy tắc 1 (48 bản gần nhất)**: Luôn giữ lại 48 file backup mới nhất theo thời gian tạo.
   * **Quy tắc 2 (30 daily snapshots)**: Giữ lại 1 bản backup đại diện (bản sớm nhất của ngày) cho mỗi ngày trong vòng 30 ngày có backup gần nhất.
   * **Dọn dẹp**: Xóa toàn bộ các file backup `.dump` cũ khác không nằm trong danh sách cần giữ của cả 2 quy tắc trên để tối ưu dung lượng đĩa.

3. **Ghi nhật ký hệ thống (`backup_runs`)**:
   * Mỗi lượt chạy backup (thành công hoặc thất bại) đều ghi nhận log chi tiết vào bảng `backup_runs` trong PostgreSQL với cấu trúc:
     * `id`: UUID định danh lượt chạy.
     * `kind`: Kiểu chạy (`manual` hoặc `auto`).
     * `status`: Trạng thái lượt chạy (`success` hoặc `failed`).
     * `artifact_path`: Đường dẫn vật lý tới file dump thành công.
     * `started_at`: Thời gian bắt đầu.
     * `finished_at`: Thời gian kết thúc.
     * `message`: Chi tiết thông báo thành công hoặc lỗi chi tiết từ hệ thống/lệnh `pg_dump`.

---

## 3. Quy Trình Khôi Phục Dữ Liệu (Restore Guide)

Để khôi phục dữ liệu từ file backup `.dump` (định dạng custom binary của pg_dump), sử dụng công cụ `pg_restore` đi kèm với PostgreSQL.

### Bước 1: Chuẩn bị môi trường khôi phục
Đảm bảo đã thêm đường dẫn tới thư mục `bin` của PostgreSQL (ví dụ `C:\Program Files\PostgreSQL\<version>\bin`) vào biến môi trường `PATH` để có thể chạy lệnh trực tiếp từ PowerShell.

### Bước 2: Lệnh khôi phục vào Database chính thức

> [!CAUTION]
> Lệnh này sẽ ghi đè dữ liệu hiện tại trong database đích. Vui lòng kiểm tra kỹ trước khi thực thi!

Chạy lệnh sau trên PowerShell:

```powershell
# Thiết lập password tạm thời cho session (tránh truyền password qua cmd arguments)
$env:PGPASSWORD="<your-password>"


# Thực hiện khôi phục dữ liệu
pg_restore -h localhost -p 5432 -U postgres -d microschedule_v2 -c --clean --if-exists -v "C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2\backups\backup_YYYYMMDD_HHMMSS.dump"

# Dọn dẹp password session sau khi xong
Remove-Item Env:\PGPASSWORD
```

**Các tham số quan trọng:**
* `-c` hoặc `--clean`: Xóa (drop) các đối tượng database (tables, indexes, v.v.) trước khi tạo lại chúng để tránh xung đột dữ liệu cũ.
* `--if-exists`: Bổ sung cờ `IF EXISTS` khi thực hiện xóa đối tượng, tránh báo lỗi phiền toái nếu bảng chưa tồn tại.
* `-v` hoặc `--verbose`: Chế độ verbose, hiển thị chi tiết các bước khôi phục lên màn hình.

---

## 4. Hướng Dẫn Kiểm Thử Khôi Phục (Restore Verification to Temp DB)

Để đảm bảo file backup hoàn toàn đáng tin cậy và có thể sử dụng được mà không ảnh hưởng tới Database thật đang chạy, bạn nên thực hiện khôi phục thử nghiệm lên một Database tạm thời:

### Bước 1: Tạo Database tạm thời
Kết nối vào PostgreSQL qua CLI hoặc chạy lệnh PowerShell:

```powershell
# Thiết lập password tạm thời
$env:PGPASSWORD="<your-password>"


# Tạo database temp rỗng
createdb -h localhost -p 5432 -U postgres microschedule_v2_temp

# Dọn dẹp password
Remove-Item Env:\PGPASSWORD
```

### Bước 2: Khôi phục file backup vào database tạm thời

```powershell
$env:PGPASSWORD="<your-password>"


pg_restore -h localhost -p 5432 -U postgres -d microschedule_v2_temp -v "C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2\backups\backup_YYYYMMDD_HHMMSS.dump"

Remove-Item Env:\PGPASSWORD
```

### Bước 3: Xác minh dữ liệu
Kết nối vào `microschedule_v2_temp` bằng psql hoặc bất kỳ công cụ quản trị (DBeaver, pgAdmin) để chạy các câu lệnh kiểm tra số lượng dòng dữ liệu:

```sql
-- Kết nối vào DB temp và thực thi:
SELECT count(*) FROM tasks;
SELECT count(*) FROM notes;
SELECT count(*) FROM calendar_sources;
SELECT count(*) FROM calendar_events;
SELECT * FROM backup_runs ORDER BY started_at DESC LIMIT 5;
```

### Bước 4: Dọn dẹp môi trường kiểm thử
Sau khi xác minh dữ liệu phục hồi thành công và khớp hoàn toàn số lượng, tiến hành drop database tạm thời để giải phóng tài nguyên:

```powershell
$env:PGPASSWORD="<your-password>"

dropdb -h localhost -p 5432 -U postgres microschedule_v2_temp
Remove-Item Env:\PGPASSWORD
```
