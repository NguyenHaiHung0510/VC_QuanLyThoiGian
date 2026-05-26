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

### Giai đoạn hiện tại: Đồng bộ Lịch tháng & Tối ưu hóa UX/UI (Đang thực hiện)
- **Bối cảnh**:
  - Trong tab "Lịch tháng", việc cuộn làm số lượng tháng hiển thị trên mini-calendar thay đổi (từ 1 sang 2 tháng và ngược lại), gây giật gián đoạn vị trí (layout shift).
  - Trong tab "Chi tiết ngày", độ dài của chuỗi ngày thay đổi (khi có/không có chữ "(Hôm nay)") làm dịch chuyển vị trí của các nút bấm điều hướng.
- **Yêu cầu cải tiến & Giải pháp**:
  1. **Cố định hiển thị 2 tháng liên tiếp**:
     - Mini-calendar sẽ luôn luôn hiển thị đúng 2 block tháng liên tiếp để giữ nguyên chiều cao layout.
     - Nếu viewport chỉ hiển thị các ngày thuộc duy nhất 1 tháng `M`, mini-calendar vẫn hiển thị thêm tháng liền trước `M - 1` ở phía trên (mặc dù tháng `M - 1` không được highlight) để tránh giật UI.
  2. **Cố định vị trí điều hướng Chi tiết ngày**:
     - Đưa text hiển thị ngày `lbl_current_date` vào một `ft.Container` có chiều rộng cố định (ví dụ `width=300`) và căn giữa (`alignment=ft.alignment.center`). Dù chuỗi chữ dài hay ngắn, các nút chevron `<`/`>` và "VỀ HÔM NAY" vẫn đứng cố định tại vị trí của chúng.
  3. **Đồng bộ highlight & tương tác**:
     - Highlight vùng ngày hiển thị trong viewport bằng màu hồng nhạt (`theme["primary_light"]`).
     - Click ngày trên mini-calendar để cuộn main calendar tới tuần đó.
     - Click chevron trên mini-calendar để cuộn main calendar theo tháng.
