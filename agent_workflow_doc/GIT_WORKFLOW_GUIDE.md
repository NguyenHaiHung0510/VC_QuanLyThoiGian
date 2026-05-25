# Quy chuẩn làm việc với Git và Tự động hóa Commit

Tài liệu này quy định cách AI Agent thực hiện các thao tác Git (Branching, Committing, Pushing) trong quá trình phát triển dự án FANG và miCareer-mini.

---

## 1. Cấu trúc Nhánh (Branching Strategy)

Hệ thống sử dụng mô hình Git Flow rút gọn với hai nhánh chính:
- **`main`**: Nhánh sản phẩm (Production). Chỉ chứa code đã ổn định.
- **`develop`**: Nhánh phát triển. Mọi tính năng mới đều được bắt đầu từ đây.

### Quy tắc đặt tên nhánh tính năng:
Khi thực hiện một Task, AI phải tạo nhánh mới từ `develop` theo định dạng:
`type/ten-tinh-nang-viet-lien-khong-dau`

**Các loại tiền tố (type):**
- `feat/`: Khi thêm tính năng mới hoặc nghiên cứu mới.
- `fix/`: Khi sửa lỗi (bug).
- `docs/`: Khi chỉ cập nhật tài liệu, file markdown, nghiên cứu.
- `refactor/`: Khi tối ưu hóa, cấu trúc lại mã nguồn mà không đổi logic.

---

## 2. Quy chuẩn Commit (Commit Message)

Sử dụng tiêu chuẩn **Conventional Commits** kết hợp với nội dung tiếng Việt.

### Cấu trúc Message:
```text
<type>: <tóm tắt ngắn gọn bằng tiếng Việt>

<chi tiết các thay đổi (body)>
- Ý thứ nhất
- Ý thứ hai
```

### Các loại `type` bắt buộc:
- `feat`: Tính năng mới (Feature).
- `fix`: Sửa lỗi (Bug fix).
- `docs`: Cập nhật tài liệu (Documentation).
- `style`: Thay đổi định dạng (Formatting, missing semi-colons, v.v.).
- `refactor`: Cơ cấu lại code (Refactoring).
- `chore`: Các việc vặt về build, thư viện, cấu hình.

**Ví dụ chuẩn:**
`docs: bổ sung nghiên cứu NMAIex_3 về Hybrid Scoring`
`Bổ sung chi tiết về 3 công thức tính điểm: RRF, Base Score và Penalty.`

---

## 3. Quy trình thực hiện tự động cho AI

Mỗi khi được giao Task và cần thực hiện thay đổi, AI tuân thủ các bước sau:

1. **Kiểm tra trạng thái:** Đảm bảo đang ở nhánh `develop` và đã pull bản mới nhất.
2. **Rẽ nhánh:** Tạo nhánh mới phù hợp với Task (`git checkout -b <branch_name>`).
3. **Thực thi:** Hoàn thành code/tài liệu.
4. **Kiểm tra:** Tự review lại các thay đổi.
5. **Stage & Commit:** 
   - `git add .`
   - Tạo commit message đúng quy chuẩn đã nêu ở mục 2.
6. **Push:** Đẩy nhánh lên remote (`git push origin <branch_name>`).
7. **Báo cáo:** Gửi xác nhận cho User kèm theo tên nhánh và nội dung commit.

