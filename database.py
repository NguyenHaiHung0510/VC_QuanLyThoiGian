import sqlite3
import json
import os
import shutil
import glob
import time
from datetime import datetime, timedelta
import re  # Dùng Regex để parse ICS tốt hơn

# Thử import openpyxl, nếu chưa cài thì báo lỗi sau
try:
    import openpyxl
except ImportError:
    openpyxl = None

# --- CẤU HÌNH ---
DATA_DIR = r"C:\Users\os\Desktop\Tools\VC_microSchedule_home"
DB_PATH = os.path.join(DATA_DIR, "todo.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

MAX_BACKUPS = 15
BACKUP_INTERVAL_HOURS = 2


def init_environment():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    con = get_connection()
    cur = con.cursor()

    cur.execute(
        "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, is_completed INTEGER DEFAULT 0, priority TEXT DEFAULT 'Nên làm', date_str TEXT, note TEXT)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS subtasks (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, content TEXT, is_completed INTEGER DEFAULT 0)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS schedule (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, time_start TEXT, time_end TEXT, location TEXT, date_str TEXT, is_cancelled INTEGER DEFAULT 0)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    )

    cur.execute("SELECT value FROM settings WHERE key='app_title'")
    if not cur.fetchone():
        _setup_defaults(cur)
    con.commit()
    con.close()
    perform_smart_backup()


def _setup_defaults(cur):
    default_locs = [
        {"name": "A2", "icon": "School"},
        {"name": "A3", "icon": "School"},
        {"name": "Thư viện", "icon": "Library"},
        {"name": "Home", "icon": "Home"},
        {"name": "Học Online", "icon": "Online"},
    ]
    default_prios = [
        {"name": "Optional", "label": "Optional", "color": "Grey", "icon": "Low"},
        {"name": "Nên làm", "label": "Nên làm", "color": "Green", "icon": "Check"},
        {"name": "Phải làm", "label": "Phải làm", "color": "Amber", "icon": "High"},
        {
            "name": "Bỏ là nhót",
            "label": "Bỏ là nhót 💀",
            "color": "Orange",
            "icon": "Danger",
        },
        {
            "name": "Nguy hiểm",
            "label": "ĐẶC BIỆT NGUY HIỂM 🆘",
            "color": "Red",
            "icon": "Warning",
        },
    ]
    default_durs = [
        {"label": "45p (1 tiết)", "value": 45},
        {"label": "90p (2 tiết)", "value": 90},
        {"label": "3h (Vibe)", "value": 180},
    ]

    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("app_title", '"microSchedule"'),
    )
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("locations", json.dumps(default_locs)),
    )
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("priorities", json.dumps(default_prios)),
    )
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("durations", json.dumps(default_durs)),
    )


def perform_smart_backup():
    if not os.path.exists(DB_PATH):
        return
    list_of_files = glob.glob(os.path.join(BACKUP_DIR, "todo_backup_*.db"))

    if list_of_files:
        latest_file = max(list_of_files, key=os.path.getmtime)
        latest_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
        if (datetime.now() - latest_time).total_seconds() < (
            BACKUP_INTERVAL_HOURS * 3600
        ):
            return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, f"todo_backup_{timestamp}.db"))

    list_of_files = glob.glob(os.path.join(BACKUP_DIR, "todo_backup_*.db"))
    list_of_files.sort(key=os.path.getmtime)
    if len(list_of_files) > MAX_BACKUPS:
        for f in list_of_files[:-MAX_BACKUPS]:
            try:
                os.remove(f)
            except:
                pass


# --- API CƠ BẢN ---
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load_settings():
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    con.close()
    settings = {}
    for key, val in rows:
        try:
            settings[key] = json.loads(val)
        except:
            settings[key] = val
    return settings


def save_single_setting(key, value):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    con.commit()
    con.close()


# ==========================================
# --- LOGIC IMPORT (MODULE HÓA) ---
# ==========================================


def parse_ics_date(dt_str):
    """Chuyển chuỗi ngày ICS (VD: 20250818T070000) sang datetime object"""
    if not dt_str:
        return None
    # Xóa các tham số múi giờ nếu có (VD: TZID=Asia/Ho_Chi_Minh:2025...)
    clean_str = dt_str.split(":")[-1].replace("Z", "").strip()
    try:
        return datetime.strptime(clean_str, "%Y%m%dT%H%M%S")
    except ValueError:
        try:
            return datetime.strptime(clean_str, "%Y%m%d")  # Trường hợp chỉ có ngày
        except:
            return None


def import_ics_schedule(file_path):
    """Đọc file .ics và lưu vào DB"""
    con = get_connection()
    cur = con.cursor()
    count = 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Kỹ thuật Unfold: Nối các dòng bị ngắt xuống dòng (bắt đầu bằng space)
            content_lines = f.read().splitlines()
            unfolded_lines = []
            for line in content_lines:
                if line.startswith(" ") or line.startswith("\t"):
                    if unfolded_lines:
                        unfolded_lines[-1] += line.strip()
                else:
                    unfolded_lines.append(line)

            # Parse từng Event
            in_event = False
            curr_event = {}

            for line in unfolded_lines:
                if line == "BEGIN:VEVENT":
                    in_event = True
                    curr_event = {}
                elif line == "END:VEVENT":
                    in_event = False
                    # Xử lý lưu DB
                    if "DTSTART" in curr_event and "SUMMARY" in curr_event:
                        dt_start = parse_ics_date(curr_event["DTSTART"])
                        dt_end = parse_ics_date(curr_event.get("DTEND"))

                        if dt_start:
                            # Nếu không có giờ kết thúc, mặc định +90p
                            if not dt_end:
                                dt_end = dt_start + timedelta(minutes=90)

                            subj = curr_event["SUMMARY"]
                            loc = curr_event.get("LOCATION", "Trường")
                            d_str = dt_start.strftime("%Y-%m-%d")
                            t_start = dt_start.strftime("%H:%M")
                            t_end = dt_end.strftime("%H:%M")

                            cur.execute(
                                "INSERT INTO schedule (subject, time_start, time_end, location, date_str) VALUES (?, ?, ?, ?, ?)",
                                (subj, t_start, t_end, loc, d_str),
                            )
                            count += 1
                elif in_event:
                    # Tách Key:Value (Lưu ý: Key có thể chứa tham số như DTSTART;TZID=...)
                    if ":" in line:
                        key_part, val_part = line.split(":", 1)
                        key_name = key_part.split(";")[0]  # Lấy tên gốc (VD: DTSTART)
                        curr_event[key_name] = val_part

        con.commit()
        return True, f"Đã import {count} lịch học!"
    except Exception as e:
        return False, f"Lỗi Import ICS: {str(e)}"
    finally:
        con.close()


def import_excel_schedule(file_path):
    """Đọc file Excel (.xlsx) và lưu vào DB"""
    if openpyxl is None:
        return False, "Thiếu thư viện openpyxl. Hãy chạy: pip install openpyxl"

    con = get_connection()
    cur = con.cursor()
    count = 0

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active  # Lấy sheet đầu tiên

        # 1. Tìm dòng Header
        header_row_idx = None
        col_map = {}  # Lưu vị trí cột: {'mon': 1, 'ngay': 3, ...}

        # Quét 10 dòng đầu để tìm header
        for r_idx, row in enumerate(sheet.iter_rows(max_row=10, values_only=True), 1):
            row_lower = [str(c).lower() if c else "" for c in row]
            if any("môn" in c or "học phần" in c for c in row_lower):
                header_row_idx = r_idx
                # Map cột
                for c_idx, val in enumerate(row_lower):
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
            return False, "Không tìm thấy cột 'Môn' và 'Ngày' trong file Excel!"

        # 2. Duyệt dữ liệu
        for row in sheet.iter_rows(min_row=header_row_idx + 1, values_only=True):
            # Lấy dữ liệu thô
            raw_sub = row[col_map["sub"]]
            raw_date = row[col_map["date"]]
            raw_time = (
                row[col_map.get("time", -1)] if "time" in col_map else "07:00"
            )  # Mặc định sáng nếu ko có giờ
            raw_loc = row[col_map.get("loc", -1)] if "loc" in col_map else "Trường"

            if not raw_sub or not raw_date:
                continue

            # Xử lý Ngày (Excel có thể trả về datetime object hoặc string)
            date_obj = None
            if isinstance(raw_date, datetime):
                date_obj = raw_date
            else:
                try:
                    # Thử parse các format phổ biến
                    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                        try:
                            date_obj = datetime.strptime(str(raw_date).strip(), fmt)
                            break
                        except:
                            pass
                except:
                    pass

            if date_obj:
                # Xử lý Giờ
                t_start = "07:00"
                if raw_time:
                    # Nếu là ca thi (VD: Ca 1, Ca 2), tự map ra giờ
                    s_time = str(raw_time).lower()
                    if "1" in s_time or "sáng" in s_time:
                        t_start = "07:00"
                    elif "2" in s_time or "chiều" in s_time:
                        t_start = "13:00"
                    elif ":" in s_time:
                        t_start = s_time.split("-")[0].strip()  # VD: 07:00-09:00

                # Lưu vào DB
                # Lịch thi thì ghi rõ là THI
                subj_title = f"[THI] {raw_sub}"
                d_str = date_obj.strftime("%Y-%m-%d")

                cur.execute(
                    "INSERT INTO schedule (subject, time_start, time_end, location, date_str) VALUES (?, ?, ?, ?, ?)",
                    (subj_title, t_start, "??:??", str(raw_loc), d_str),
                )
                count += 1

        con.commit()
        return True, f"Đã import {count} lịch thi!"

    except Exception as e:
        return False, f"Lỗi đọc Excel: {str(e)}"
    finally:
        con.close()


def get_subtasks_for_task(conn, task_id):
    """Lấy danh sách subtasks cho một task cụ thể."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, content, is_completed FROM subtasks WHERE task_id = ?",
        (task_id,),
    )
    # Vì conn.row_factory đã là sqlite3.Row, nên dùng map(dict) để chuyển về dict dễ dùng
    return list(map(dict, cursor.fetchall()))


def export_planner_data(threshold_date_str: str, date_format: str = "%Y-%m-%d"):
    """
    Trích xuất dữ liệu lịch trình (Schedule) và nhiệm vụ (Tasks) chưa hoàn thành/tương lai.
    Ngày mốc (threshold_date_str) phải có định dạng YYYY-MM-DD (ISO format).
    """

    # OUTPUT_FILE phải nằm trong thư mục DATA_DIR cố định
    OUTPUT_FILE = os.path.join(DATA_DIR, "export_planner_data.json")

    try:
        # Sử dụng hàm get_connection đã có sẵn trong database.py
        conn = get_connection()
        cursor = conn.cursor()

        # 1. LẤY SCHEDULE (Lịch cố định)
        # Chỉ lấy các sự kiện có ngày >= ngày mốc
        cursor.execute(
            "SELECT subject, time_start, time_end, location, date_str FROM schedule WHERE date_str >= ?",
            (threshold_date_str,),
        )
        schedules = list(map(dict, cursor.fetchall()))

        # 2. LẤY TASKS (Nhiệm vụ)
        # Logic: (date_str >= ngày mốc) OR (is_completed = 0)
        # Điều này đảm bảo:
        #   - Tất cả tasks TƯƠNG LAI đều được lấy
        #   - Tất cả tasks QUÁ HẠN/CHƯA HOÀN THÀNH cũng được lấy
        cursor.execute(
            "SELECT id, title, is_completed, priority, date_str, note FROM tasks WHERE date_str >= ? OR is_completed = 0",
            (threshold_date_str,),
        )
        tasks = list(map(dict, cursor.fetchall()))

        # 3. GẮN SUBTASK VÀ TẠO NGỮ CẢNH (Context Note)
        tasks_with_subs = []
        for task in tasks:
            subtasks = get_subtasks_for_task(conn, task["id"])
            task["subtasks_list"] = subtasks

            total_sub = len(subtasks)
            done_sub = sum(1 for s in subtasks if s["is_completed"] == 1)

            # Tạo context_note (như trong truy_van.py)
            if task["date_str"] < threshold_date_str and task["is_completed"] == 0:
                task["context_note"] = (
                    f"OVERDUE (Quá hạn). Tiến độ: {done_sub}/{total_sub}"
                )
            else:
                task["context_note"] = f"UPCOMING. Tiến độ: {done_sub}/{total_sub}"

            tasks_with_subs.append(task)

        conn.close()

        # 4. GOM DỮ LIỆU VÀO CẤU TRÚC JSON CUỐI CÙNG
        final_data = {
            "metadata": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "threshold_date": datetime.strptime(
                    threshold_date_str, date_format
                ).strftime(
                    "%d/%m/%Y"
                ),  # Chuyển lại định dạng dễ đọc
                "description": "Dữ liệu lập kế hoạch cho AI (microSchedule).",
            },
            "schedule_events": schedules,
            "todo_tasks": tasks_with_subs,
        }

        # Xuất file JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            # Dùng indent=2 để JSON dễ đọc hơn khi AI đọc
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        # Trả về nội dung JSON dưới dạng string để main.py có thể copy vào clipboard
        return json.dumps(final_data, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Lỗi khi export dữ liệu: {e}")
        return None


init_environment()
