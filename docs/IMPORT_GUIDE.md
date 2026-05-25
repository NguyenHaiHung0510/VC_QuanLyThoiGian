# IMPORT_GUIDE.md - Chi tiết Parser ICS/Excel

Tài liệu này giải thích chi tiết cách thức hoạt động của hai loại import chính: **ICS (iCalendar)** và **Excel**.

## 1. ICS Parser (`import_ics_schedule()`)

### 1.1 RFC 5545 - iCalendar Format

ICS là định dạng chuẩn để trao đổi sự kiện lịch. Cấu trúc cơ bản:

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//My Calendar//EN
BEGIN:VEVENT
UID:event123@example.com
DTSTART;TZID=Asia/Ho_Chi_Minh:20250518T070000
DTEND;TZID=Asia/Ho_Chi_Minh:20250518T090000
SUMMARY:Math Class
LOCATION:Room A2
DESCRIPTION:Advanced Calculus
END:VEVENT
END:VCALENDAR
```

### 1.2 Quy trình Parse ICS

#### Step 1: Unfolding (RFC 5545 Section 3.1)

**Problem**: ICS có thể chứa dòng dài bị chia thành multiple lines, mỗi dòng tiếp theo bắt đầu bằng space hoặc tab.

```ics
# Ví dụ multiline (folded)
SUMMARY:This is a very long summary that continues
 on the next line
```

**Solution**: Ghép các dòng tiếp theo vào dòng trước

```python
def unfold_ics_lines(content_lines):
    """
    Ghép lại các dòng bị fold theo RFC 5545
    Dòng tiếp theo bắt đầu bằng SPACE/TAB → ghép vào dòng trước
    """
    unfolded_lines = []
    for line in content_lines:
        if line.startswith(" ") or line.startswith("\t"):
            if unfolded_lines:
                unfolded_lines[-1] += line.strip()
        else:
            unfolded_lines.append(line)
    return unfolded_lines
```

#### Step 2: Event Extraction

Lặp qua các dòng unfold và trích xuất từng VEVENT block:

```python
in_event = False
curr_event = {}

for line in unfolded_lines:
    if line == "BEGIN:VEVENT":
        in_event = True
        curr_event = {}
    elif line == "END:VEVENT":
        in_event = False
        # Process curr_event
    elif in_event:
        # Parse key:value
        if ":" in line:
            key_part, val_part = line.split(":", 1)
            key_name = key_part.split(";")[0]  # Xóa tham số (TZID=...)
            curr_event[key_name] = val_part
```

#### Step 3: Date/Time Parsing

**Challenge**: ICS có thể chứa datetime ở nhiều format khác nhau.

```ics
# Format 1: UTC (Z suffix)
DTSTART:20250518T070000Z

# Format 2: Local + Timezone Parameter
DTSTART;TZID=Asia/Ho_Chi_Minh:20250518T070000

# Format 3: Date only (no time)
DTSTART:20250518
```

**Solution**: `parse_ics_date()` xử lý tất cả cases

```python
def parse_ics_date(dt_str):
    """
    Chuyển ICS date string → datetime object
    
    Hỗ trợ:
    - "20250518T070000Z" (UTC)
    - "TZID=Asia/Ho_Chi_Minh:20250518T070000" (with timezone)
    - "20250518" (date only)
    """
    if not dt_str:
        return None
    
    # Xóa timezone prefix nếu có
    clean_str = dt_str.split(":")[-1].replace("Z", "").strip()
    
    try:
        # Try full datetime
        return datetime.strptime(clean_str, "%Y%m%dT%H%M%S")
    except ValueError:
        try:
            # Try date only
            return datetime.strptime(clean_str, "%Y%m%d")
        except:
            return None
```

#### Step 4: Event Storage

```python
# Kiểm tra required fields
if "DTSTART" in curr_event and "SUMMARY" in curr_event:
    dt_start = parse_ics_date(curr_event["DTSTART"])
    dt_end = parse_ics_date(curr_event.get("DTEND"))
    
    # Nếu không có end time, mặc định +90 phút
    if not dt_end:
        dt_end = dt_start + timedelta(minutes=90)
    
    subj = curr_event["SUMMARY"]
    loc = curr_event.get("LOCATION", "Trường")  # Default location
    
    # Format lại thành YYYY-MM-DD HH:MM
    d_str = dt_start.strftime("%Y-%m-%d")
    t_start = dt_start.strftime("%H:%M")
    t_end = dt_end.strftime("%H:%M")
    
    # Insert vào DB
    cur.execute(
        "INSERT INTO schedule (subject, time_start, time_end, location, date_str) VALUES (?, ?, ?, ?, ?)",
        (subj, t_start, t_end, loc, d_str)
    )
    count += 1
```

### 1.3 Error Handling

| Scenario | Xử lý |
|----------|-------|
| File not found | Try-except wraps whole function |
| Invalid encoding | Open with UTF-8 (có thể cần fallback) |
| Malformed VEVENT | Skip event nếu missing DTSTART/SUMMARY |
| Invalid date format | Return None, skip event |
| Duplicate events | Không check duplicates (cho phép reimport) |

---

## 2. Excel Parser (`import_excel_schedule()`)

### 2.1 Thách thức Excel

Excel không có chuẩn định dạng, nên parser phải "flexible" để detect:

```
Tùy-chỉnh Excel có thể có cột nào:
- Môn học
- Học phần  
- Lịch thi (row headers khác nhau)
- Ngày thi / Ngày khai giảng
- Ca thi (Ca 1, Ca 2, Sáng, Chiều, 07:00-09:00)
- Địa điểm / Phòng / Lớp
```

### 2.2 Quy trình Parse Excel

#### Step 1: Header Detection

Quét 10 dòng đầu để tìm dòng header chứa các keyword:

```python
for r_idx, row in enumerate(sheet.iter_rows(max_row=10, values_only=True), 1):
    row_lower = [str(c).lower() if c else "" for c in row]
    
    # Tìm keyword
    if any("môn" in c or "học phần" in c for c in row_lower):
        header_row_idx = r_idx
        
        # Map columns
        col_map = {}
        for c_idx, val in enumerate(row_lower):
            if "môn" in val or "học phần" in val:
                col_map["sub"] = c_idx
            elif "ngày" in val:
                col_map["date"] = c_idx
            elif "giờ" in val or "ca" in val:
                col_map["time"] = c_idx
            elif "phòng" in val or "địa điểm" in val:
                col_map["loc"] = c_idx
```

**Validation**: Phải có "Môn" + "Ngày", nếu không return error

#### Step 2: Row Parsing

```python
for row in sheet.iter_rows(min_row=header_row_idx + 1, values_only=True):
    raw_sub = row[col_map["sub"]]
    raw_date = row[col_map["date"]]
    raw_time = row[col_map.get("time", -1)] if "time" in col_map else "07:00"
    raw_loc = row[col_map.get("loc", -1)] if "loc" in col_map else "Trường"
    
    if not raw_sub or not raw_date:
        continue  # Skip empty rows
```

#### Step 3: Smart Date Parsing

Excel có thể trả về `datetime object` hoặc `string`, nên cần xử lý cả hai:

```python
date_obj = None

# Case 1: Excel tự động parse thành datetime object
if isinstance(raw_date, datetime):
    date_obj = raw_date

# Case 2: String - thử các format phổ biến
else:
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            date_obj = datetime.strptime(str(raw_date).strip(), fmt)
            break
        except:
            pass

if not date_obj:
    continue  # Skip nếu không parse được
```

**Examples**:
- `18/05/2025` → `%d/%m/%Y`
- `18-05-2025` → `%d-%m-%Y`
- `2025-05-18` → `%Y-%m-%d`

#### Step 4: Exam Slot Mapping

Thi thường có "Ca" (slots), parser tự map sang giờ:

```python
t_start = "07:00"  # Default

if raw_time:
    s_time = str(raw_time).lower()
    
    # Detect ca thi
    if "1" in s_time or "sáng" in s_time:
        t_start = "07:00"
    elif "2" in s_time or "chiều" in s_time:
        t_start = "13:00"
    elif ":" in s_time:
        # Format: "07:00-09:00" → lấy phần đầu
        t_start = s_time.split("-")[0].strip()
```

**Mapping Table**:
| Input | Output |
|-------|--------|
| "Ca 1", "1", "Sáng" | 07:00 |
| "Ca 2", "2", "Chiều" | 13:00 |
| "07:00-09:00" | 07:00 |

#### Step 5: Lưu vào DB

```python
subj_title = f"[THI] {raw_sub}"  # Thêm prefix để phân biệt
d_str = date_obj.strftime("%Y-%m-%d")

cur.execute(
    "INSERT INTO schedule (subject, time_start, time_end, location, date_str) VALUES (?, ?, ?, ?, ?)",
    (subj_title, t_start, "??:??", str(raw_loc), d_str)
)
count += 1
```

**Note**: `time_end` được set thành `"??:??"` vì Excel thường không có thông tin này

### 2.3 Error Handling

| Scenario | Xử lý |
|----------|-------|
| Missing openpyxl | Return error message (user cần install) |
| No valid header | Return "Không tìm thấy cột 'Môn' và 'Ngày'" |
| Invalid date format | Skip row |
| Empty subject/date | Skip row |
| Duplicate rows | Không check (cho phép reimport) |

---

## 3. So sánh ICS vs Excel

| Aspect | ICS | Excel |
|--------|-----|-------|
| **Format** | Chuẩn RFC 5545 | Tự-định nghĩa |
| **DateTime** | Cô đông, timezone-aware | Flexible, thường gặp lỗi format |
| **Location** | Có field riêng | Tuỳ thuộc cột |
| **End Time** | Thường có (DTEND) | Hiếm có → mặc định |
| **Validation** | Chặt (RFC compliance) | Lỏng (smart detect) |
| **Use Case** | Lịch học từ Google Calendar | Lịch thi từ nhà trường |

---

## 4. Quy trình Sử dụng

### Import từ Google Calendar (ICS)

1. Google Calendar → Share → Get ICS link
2. Hoặc Export từ Outlook/Apple Calendar
3. Mở app microSchedule
4. Menu → Import Schedule → Chọn file `.ics`
5. App parse + display success message

### Import từ Excel (Lịch thi)

1. Nhà trường cung cấp file Excel lịch thi
2. Đảm bảo có cột "Môn" + "Ngày"
3. Mở app microSchedule
4. Menu → Import Schedule → Chọn file `.xlsx`
5. App auto-detect columns, parse, insert

---

## 5. Best Practices & Troubleshooting

### ICS Best Practices
- ✅ Export từ Google Calendar (format tương thích)
- ✅ Đặt event name/location rõ ràng
- ⚠️ Timezone có thể không được parse đúng (nên set local time)
- ⚠️ Recurring events thường không được support (phải export specific instances)

### Excel Best Practices
- ✅ Đặt header rõ ràng (chứa từ "Môn", "Ngày")
- ✅ Dùng format ngày consistent (DD/MM/YYYY hoặc YYYY-MM-DD)
- ✅ Điền đầy đủ "Giờ" và "Địa điểm"
- ⚠️ Tránh merge cells (parser không xử lý)
- ⚠️ Không nên có các row trống giữa data

### Troubleshooting

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-----------|----------|
| "File not found" | Path sai | Check file path again |
| "Không tìm thấy 'Môn' và 'Ngày'" | Header không đúng | Rename columns to include "Môn", "Ngày" |
| "Lỗi đọc Excel" | openpyxl chưa cài | `pip install openpyxl` |
| Import 0 events | Format date sai | Thử format khác (DD/MM/YYYY, YYYY-MM-DD) |
| Duplicate events sau reimport | Không có dedup logic | Delete old events trước reimport |

---

## 6. Future Enhancements

- [ ] Support iCal recurrence rules (RRULE)
- [ ] Auto-detect date format (không cần user chỉ định)
- [ ] Deduplication logic (check duplicate before insert)
- [ ] Batch import (multiple files)
- [ ] Timezone conversion (convert to local time)
- [ ] Validation report (list events được import)

---
*Tài liệu cập nhật ngày 25/05/2026.*
