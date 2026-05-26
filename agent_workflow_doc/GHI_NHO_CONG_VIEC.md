# GHI NHỚ CÔNG VIỆC - microSchedule v2

Tài liệu này ghi nhớ toàn bộ tiêu chí, cách thức làm việc, tài nguyên sẵn có và các yêu cầu sửa đổi từ người dùng để đảm bảo tính nhất quán và hiệu quả trong phát triển.

---

## 1. Tiêu chí & Quy tắc làm việc (Rules & Workflow)
- **Quy chuẩn Git & Commit**:
  - Thực hiện đúng quy định tại [GIT_WORKFLOW_GUIDE.md](file:///c:/Users/os/Desktop/old_prj/VC_QuanLyThoiGian/agent_workflow_doc/GIT_WORKFLOW_GUIDE.md).
  - Commit message theo chuẩn Conventional Commits kết hợp mô tả tiếng Việt (Ví dụ: `feat: ...`, `fix: ...`).
- **Dọn dẹp tài nguyên**:
  - Trước khi commit và bàn giao, bắt buộc phải dọn dẹp sạch sẽ các file tạm, file log rác (ví dụ: `flet_run.log`, `commit_msg.txt`, các file `.tmp`).
- **Môi trường chạy ứng dụng**:
  - Giữ lệnh chạy mặc định là Desktop dạng native app (`ft.app(target=main)`).
  - Khi cần debug trên web, sử dụng Flet CLI (`flet run --web main.py`) để Flet tự động ghi đè giao diện web. Tránh cấu hình cứng `view=ft.AppView.WEB_BROWSER` trong mã nguồn commit.
- **Quy trình Planning Mode**:
  - Luôn viết/cập nhật `implementation_plan.md` khi bắt đầu task mới hoặc thay đổi kiến trúc lớn.
  - Đợi người dùng duyệt trước khi thực thi.
  - Sử dụng `task.md` để theo dõi tiến độ và `walkthrough.md` để báo cáo kết quả sau khi hoàn thành.

---

## 2. Tài nguyên sẵn có (Available Resources)
- **Công cụ kiểm thử & Debug**:
  - `chrome-devtools-mcp`: Cung cấp các thao tác tương tác với trình duyệt (click, type, screenshot, snapshot, evaluate_script).
  - CLI commands: Chạy ứng dụng Python và các script test trong virtual environment (`.\venv\Scripts\python`).
- **Database**:
  - PostgreSQL cơ sở dữ liệu local `microschedule_v2`.
  - Connection string = postgresql://postgres:hungklv123@localhost:5432/microschedule_v2`
  - Kết nối được định nghĩa qua `load_config()` trong `app.config` và khởi tạo ở `main.py`.
  - Chứa đầy đủ dữ liệu thử nghiệm (ví dụ: 31 ghi chú, các lịch học/thi tháng 5 & 6 năm 2026).

---

## 3. Nhật ký yêu cầu của người dùng
### Giai đoạn trước: Tab Ghi chú cá nhân (Đã hoàn thành)
- Tự động xuống dòng 2 dòng (wrap text) cho tiêu đề ghi chú và checklist items.
- Tương tác check/uncheck trực tiếp trên checkbox của note card ngoài màn hình.
- Bấm vào `+ N mục khác...` để mở popup chỉnh sửa chi tiết.
- Thêm nút Lưu nhanh (icon check) bên cạnh ô nhập tiêu đề ghi chú nhanh.
- Dropdown sắp xếp ghi chú theo Tiêu đề (A-Z) hoặc Chỉnh sửa mới nhất (ghi chú ghim luôn ở trên đầu).
- Gom nhóm các ghi chú đã lưu trữ (Archived) xuống cuối trang, làm mờ độ đục `opacity=0.6`, cung cấp nút Khôi phục (Unarchive).

### Giai đoạn hiện tại: Đồng bộ Lịch tháng, Quản lý Nguồn lịch & Tối ưu hóa Ghi chú (Đang thực hiện)
- **Bối cảnh**:
  - Trong tab "Lịch tháng", việc cuộn làm số lượng tháng hiển thị trên mini-calendar thay đổi (từ 1 sang 2 tháng và ngược lại), gây giật gián đoạn vị trí (layout shift).
  - Trong tab "Chi tiết ngày", độ dài của chuỗi ngày thay đổi (khi có/không có chữ "(Hôm nay)") làm dịch chuyển vị trí của các nút bấm điều hướng.
  - Người dùng cần quản lý nguồn lịch ở góc trái dưới bằng cách mở một Dialog thay vì click trực tiếp thay đổi trạng thái checkbox, đồng thời hỗ trợ cập nhật file lịch mới ghi đè file lịch cũ (có lưu lịch sử nhập và ẩn sự kiện cũ).
  - Tab "Ghi chú" cần thêm tooltip chi tiết khi hover qua note cell và cho phép click trực tiếp tiêu đề note để sửa.
- **Yêu cầu cải tiến & Giải pháp**:
  1. **Cố định hiển thị 2 tháng liên tiếp**:
     - Mini-calendar sẽ luôn luôn hiển thị đúng 2 block tháng liên tiếp để giữ nguyên chiều cao layout.
     - Nếu viewport chỉ hiển thị các ngày thuộc duy nhất 1 tháng `M`, mini-calendar vẫn hiển thị thêm tháng liền trước `M - 1` ở phía trên để tránh giật UI.
  2. **Cố định vị trí điều hướng Chi tiết ngày**:
     - Đưa text hiển thị ngày `lbl_current_date` vào một `ft.Container` có chiều rộng cố định `width=300` và căn giữa.
  3. **Quản lý Nguồn lịch (Sidebar)**:
     - Tách Checkbox nguồn lịch: click vào ô vuông để tick/untick (ẩn/hiện lịch), click vào chữ hiển thị để mở Dialog quản lý.
     - Dialog quản lý hiển thị: Tên hiển thị (cho sửa), tên file gốc của version active, vị trí file copy tượng trưng (`storage/copied_calendars/<file_name>`), và lịch sử nhập (sắp xếp thời gian mới nhất lên trước, gồm tên hiển thị và thời gian).
     - Nút "Cập nhật File mới": Mở FilePicker tải file `.ics` hoặc `.xlsx` mới, gọi `CalendarImportService.import_file` để sinh phiên bản mới hoạt động (active) thay thế phiên bản cũ (revert/supersede lịch cũ bằng cách đổi status version và ẩn các event cũ).
  4. **Tối ưu hóa Ghi chú**:
     - Tooltip note card: Khi hover qua note card, hiển thị tooltip tĩnh gồm tên ghi chú đầy đủ (auto ngắt dòng) và các task con (checklist items) từ trên xuống dưới, dài quá 8 mục thì hiện `+N mục khác...`.
     - Click tiêu đề ghi chú: Bấm trực tiếp vào tiêu đề ghi chú trên note card sẽ kích hoạt mở dialog "chỉnh sửa chi tiết".

### Giai đoạn Tiếp theo: Sửa lỗi Đồng bộ dữ liệu Lịch/Task & Khắc phục Crash Dialog Quản lý Nguồn lịch (Đang thực hiện)
- **Bối cảnh & Yêu cầu lỗi**:
  1. **Thêm lịch cứng ở Chi tiết ngày không hiển thị**: Nút `+ LỊCH CỐ ĐỊNH` (`open_add_schedule_dialog`) chỉ chèn vào SQLite (`schedule`), trong khi Day View và Month View đã chuyển sang dùng PostgreSQL (`calendar_events`).
     - *Giải pháp*: Khi người dùng lưu lịch cứng qua `open_add_schedule_dialog()`, ngoài việc lưu vào SQLite `schedule` (để tương thích ngược), cần đồng thời chèn sự kiện này vào bảng `calendar_events` trong PostgreSQL dưới nguồn `'v1_sqlite_schedule'` (loại `legacy`, `status = 'active'`).
  2. **Task không hiển thị ở Lịch tháng**: Người dùng thêm Task ở tab Chi tiết ngày nhưng sang Lịch tháng không nhìn thấy Task này vì Lịch tháng chỉ load từ `calendar_events`.
     - *Giải pháp*: Cải tiến hàm `get_events_by_range` của `CalendarViewService` trong PostgreSQL để truy vấn thêm các Task có hạn (`due_at`) trong khoảng thời gian tương ứng từ bảng `tasks` (loại trừ các task `archived`), sau đó map các Task này thành dạng dict sự kiện với `event_type = 'task'` để Lịch tháng tự động hiển thị dưới dạng các event chip và tooltip.
  3. **Crash khi mở Dialog quản lý Nguồn lịch**: Khi bấm vào tên nguồn lịch ở góc trái dưới tab Lịch tháng, ứng dụng bị crash im lặng do thuộc tính `max_height=180` không được Flet hỗ trợ trong constructor `ft.Column`.
     - *Giải pháp*: Đổi `max_height=180` thành `height=180` trực tiếp khi khởi tạo `ft.Column` cho lịch sử nhập.
