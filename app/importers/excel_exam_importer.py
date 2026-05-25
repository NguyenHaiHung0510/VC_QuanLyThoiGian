import hashlib
import re
from datetime import datetime, timedelta, timezone
import openpyxl

VIETNAM_TZ = timezone(timedelta(hours=7))

class ExcelExamImporter:
    def __init__(self):
        pass

    def parse_time_slot(self, time_val) -> tuple[str, str]:
        """
        Parses time string or ca thi and returns (start_time_str, end_time_str) in 'HH:MM' format.
        Defaults to ("07:00", "08:30") if unknown.
        """
        if not time_val:
            return "07:00", "08:30"

        s_time = str(time_val).strip().lower()

        # Regex to find HH:MM or HHhMM
        time_matches = re.findall(r"(\d{1,2})[h:](\d{2})", s_time)
        if time_matches:
            # Format found, e.g., [('07', '00'), ('09', '00')] or [('13', '30')]
            start_h, start_m = time_matches[0]
            start_str = f"{int(start_h):02d}:{int(start_m):02d}"

            if len(time_matches) > 1:
                end_h, end_m = time_matches[1]
                end_str = f"{int(end_h):02d}:{int(end_m):02d}"
            else:
                # Default duration is 90 mins
                start_dt = datetime.strptime(start_str, "%H:%M")
                end_dt = start_dt + timedelta(minutes=90)
                end_str = end_dt.strftime("%H:%M")
            return start_str, end_str

        # Ca thi / Shift detection
        if "1" in s_time or "sáng" in s_time:
            return "07:00", "08:30"
        elif "2" in s_time or "chiều" in s_time:
            return "13:00", "14:30"
        elif "3" in s_time:
            return "15:30", "17:00"

        return "07:00", "08:30"

    def parse(self, file_path: str) -> tuple[list, list]:
        """
        Parses Excel exam schedule, returning (events, warnings).
        """
        events = []
        warnings = []

        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
        except Exception as e:
            raise IOError(f"Failed to read Excel file: {str(e)}")

        header_row_idx = None
        col_map = {}

        # Scan first 10 rows for header
        for r_idx in range(1, 11):
            row_values = [sheet.cell(row=r_idx, column=c_idx).value for c_idx in range(1, sheet.max_column + 1)]
            row_lower = [str(c).lower() if c is not None else "" for c in row_values]

            if any("môn" in c or "học phần" in c for c in row_lower):
                header_row_idx = r_idx
                for c_idx, val in enumerate(row_lower, 1):
                    if "môn" in val or "học phần" in val:
                        col_map["sub"] = c_idx
                    elif "ngày" in val:
                        col_map["date"] = c_idx
                    elif "giờ" in val or "ca" in val:
                        col_map["time"] = c_idx
                    elif "phòng" in val or "địa điểm" in val:
                        col_map["loc"] = c_idx
                break

        if header_row_idx is None or "sub" not in col_map or "date" not in col_map:
            raise ValueError("Không tìm thấy cột 'Môn' và 'Ngày' trong file Excel!")

        for r_idx in range(header_row_idx + 1, sheet.max_row + 1):
            sub_cell = sheet.cell(row=r_idx, column=col_map["sub"])
            date_cell = sheet.cell(row=r_idx, column=col_map["date"])

            raw_sub = sub_cell.value
            raw_date = date_cell.value

            if raw_sub is None or raw_date is None:
                continue

            # Process Date
            date_obj = None
            suspicious_date = False

            # Check number format for suspicious mm-dd-yy
            num_fmt = str(date_cell.number_format).lower()
            if "m" in num_fmt and "d" in num_fmt:
                # If 'm' comes before 'd', it's suspicious of mm-dd-yy, except yyyy-mm-dd
                if num_fmt.find("m") < num_fmt.find("d") and "yyyy" not in num_fmt:
                    suspicious_date = True

            if isinstance(raw_date, datetime):
                date_obj = raw_date
            else:
                # String parse
                date_str_clean = str(raw_date).strip()
                for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                    try:
                        date_obj = datetime.strptime(date_str_clean, fmt)
                        break
                    except ValueError:
                        pass

                # Check if it parsed but was in mm/dd/yyyy format instead
                if not date_obj:
                    for fmt in ["%m/%d/%Y", "%m-%d-%Y"]:
                        try:
                            date_obj = datetime.strptime(date_str_clean, fmt)
                            suspicious_date = True
                            break
                        except ValueError:
                            pass

            if not date_obj:
                warnings.append(f"Dòng {r_idx}: Không thể phân tích ngày thi '{raw_date}'")
                continue

            if suspicious_date:
                warnings.append(
                    f"Dòng {r_idx}: Cột ngày sử dụng định dạng đáng ngờ '{date_cell.number_format or raw_date}' (nguy cơ mm-dd-yy)."
                )

            # Process Time
            raw_time = sheet.cell(row=r_idx, column=col_map["time"]).value if "time" in col_map else None
            t_start_str, t_end_str = self.parse_time_slot(raw_time)

            # Combine date and time
            try:
                start_h, start_m = map(int, t_start_str.split(":"))
                starts_at = date_obj.replace(hour=start_h, minute=start_m, second=0, microsecond=0, tzinfo=VIETNAM_TZ)

                end_h, end_m = map(int, t_end_str.split(":"))
                ends_at = date_obj.replace(hour=end_h, minute=end_m, second=0, microsecond=0, tzinfo=VIETNAM_TZ)

                # If end time is before start time, it might cross midnight
                if ends_at < starts_at:
                    ends_at += timedelta(days=1)
            except Exception as e:
                warnings.append(f"Dòng {r_idx}: Lỗi ghép ngày/giờ: {str(e)}")
                continue

            # Process Subject/Title
            title = str(raw_sub).strip()
            if not title.upper().startswith("[THI]"):
                title = f"[THI] {title}"

            raw_loc = sheet.cell(row=r_idx, column=col_map["loc"]).value if "loc" in col_map else "Trường"
            location = str(raw_loc).strip() if raw_loc is not None else None

            # Generate stable external_uid for Excel
            # Format: excel-{starts_at.strftime('%Y%m%d%H%M')}-{hash(title)}
            title_clean = re.sub(r"\s+", "", title).lower()
            uid_payload = f"{starts_at.isoformat()}-{title_clean}"
            external_uid = f"excel-{hashlib.md5(uid_payload.encode('utf-8')).hexdigest()}"

            # Compute content hash
            starts_at_str = starts_at.isoformat()
            ends_at_str = ends_at.isoformat()
            location_str = location if location else ""
            hash_payload = f"{title}|{location_str}|{starts_at_str}|{ends_at_str}|exam"
            content_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

            events.append({
                "external_uid": external_uid,
                "content_hash": content_hash,
                "title": title,
                "description": f"Imported from Excel exam schedule. Raw Time: {raw_time}",
                "starts_at": starts_at,
                "ends_at": ends_at,
                "location": location,
                "event_type": "exam",
                "status": "active"
            })

        return events, warnings
