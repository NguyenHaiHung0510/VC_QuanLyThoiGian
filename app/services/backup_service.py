import os
import re
import glob
import uuid
import subprocess
from datetime import datetime
from urllib.parse import urlparse
import psycopg
from dotenv import load_dotenv

class BackupService:
    def __init__(self, dotenv_path=None):
        # Load environment variables từ file .env
        if dotenv_path:
            load_dotenv(dotenv_path)
        else:
            load_dotenv()

        self.database_url = os.getenv("DATABASE_URL")
        self.data_dir = os.getenv("MICROSCHEDULE_DATA_DIR", r"C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2")
        self.backup_dir = os.getenv("MICROSCHEDULE_BACKUP_DIR", os.path.join(self.data_dir, "backups"))

    def _parse_db_url(self, url):
        """Parse DATABASE_URL thành các tham số kết nối cho pg_dump và psycopg"""
        if not url:
            raise ValueError("DATABASE_URL is not set or empty")

        parsed = urlparse(url)
        # Hỗ trợ định dạng postgresql://
        if parsed.scheme not in ("postgresql", "postgres"):
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")

        return {
            "username": parsed.username or "postgres",
            "password": parsed.password,
            "hostname": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/") if parsed.path else "microschedule_v2"
        }

    def _log_backup_run(self, run_id, kind, status, artifact_path, started_at, finished_at, message):
        """Ghi nhận log của tiến trình backup vào database PostgreSQL"""
        if not self.database_url:
            return

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO backup_runs (id, kind, status, artifact_path, started_at, finished_at, message)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        str(run_id),
                        kind,
                        status,
                        artifact_path,
                        started_at,
                        finished_at,
                        message
                    ))
                    conn.commit()
        except Exception as e:
            print(f"[Backup Warning] Failed to log backup run to existing backup_runs table: {e}")

    def backup_now(self, kind="manual"):
        """
        Thực hiện sao lưu database hiện tại bằng pg_dump.
        Trả về dictionary dạng:
        {
            "success": bool,
            "artifact_path": str or None,
            "message": str,
            "started_at": datetime,
            "finished_at": datetime
        }
        """
        started_at = datetime.now()
        run_id = uuid.uuid4()

        # Đảm bảo thư mục backup tồn tại
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except Exception as e:
            err_msg = f"Failed to create backup directory '{self.backup_dir}': {e}"
            print(f"[Backup Error] {err_msg}")
            finished_at = datetime.now()
            self._log_backup_run(run_id, kind, "failed", None, started_at, finished_at, err_msg)
            return {
                "success": False,
                "artifact_path": None,
                "message": err_msg,
                "started_at": started_at,
                "finished_at": finished_at
            }

        # Parse DATABASE_URL
        try:
            db_params = self._parse_db_url(self.database_url)
        except Exception as e:
            err_msg = f"Failed to parse database connection URL: {e}"
            print(f"[Backup Error] {err_msg}")
            finished_at = datetime.now()
            self._log_backup_run(run_id, kind, "failed", None, started_at, finished_at, err_msg)
            return {
                "success": False,
                "artifact_path": None,
                "message": err_msg,
                "started_at": started_at,
                "finished_at": finished_at
            }

        timestamp = started_at.strftime("%Y%m%d_%H%M%S")
        temp_filename = f"temp_backup_{timestamp}_{run_id.hex[:8]}.dump"
        official_filename = f"backup_{timestamp}.dump"

        temp_file_path = os.path.join(self.backup_dir, temp_filename)
        official_file_path = os.path.join(self.backup_dir, official_filename)

        # Xây dựng lệnh pg_dump
        cmd = ["pg_dump", "-F", "c", "-b"]

        if db_params["hostname"]:
            cmd.extend(["-h", db_params["hostname"]])
        if db_params["port"]:
            cmd.extend(["-p", str(db_params["port"])])
        if db_params["username"]:
            cmd.extend(["-U", db_params["username"]])

        cmd.extend(["-f", temp_file_path, db_params["database"]])

        # Chuẩn bị môi trường truyền password an toàn
        env = os.environ.copy()
        if db_params["password"]:
            env["PGPASSWORD"] = db_params["password"]

        # Chạy pg_dump
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                # Rename file tạm thành file chính thức (atomic write)
                os.replace(temp_file_path, official_file_path)
                finished_at = datetime.now()

                msg = f"Backup completed successfully: {official_filename}"
                print(f"[Backup Success] {msg}")

                # Chạy dọn dẹp retention policy sau khi backup thành công
                retention_msg = self.apply_retention_policy()
                msg = f"{msg}. {retention_msg}"

                self._log_backup_run(run_id, kind, "success", official_file_path, started_at, finished_at, msg)
                return {
                    "success": True,
                    "artifact_path": official_file_path,
                    "message": msg,
                    "started_at": started_at,
                    "finished_at": finished_at
                }
            else:
                # pg_dump trả về lỗi
                finished_at = datetime.now()
                err_msg = f"pg_dump failed with exit code {result.returncode}. Error: {result.stderr.strip()}"
                print(f"[Backup Error] {err_msg}")

                # Dọn dẹp file tạm nếu được tạo ra
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except Exception:
                        pass

                self._log_backup_run(run_id, kind, "failed", None, started_at, finished_at, err_msg)
                return {
                    "success": False,
                    "artifact_path": None,
                    "message": err_msg,
                    "started_at": started_at,
                    "finished_at": finished_at
                }

        except Exception as e:
            finished_at = datetime.now()
            err_msg = f"Exception occurred during pg_dump execution: {e}"
            print(f"[Backup Error] {err_msg}")

            # Dọn dẹp file tạm nếu có
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass

            self._log_backup_run(run_id, kind, "failed", None, started_at, finished_at, err_msg)
            return {
                "success": False,
                "artifact_path": None,
                "message": err_msg,
                "started_at": started_at,
                "finished_at": finished_at
            }

    def apply_retention_policy(self):
        """
        Áp dụng retention policy:
        - Giữ 48 bản backup gần nhất.
        - Giữ 30 daily snapshots (bản backup sớm nhất của mỗi ngày trong vòng 30 ngày gần nhất có backup).
        - Xóa các bản khác.
        Trả về chuỗi thông báo kết quả dọn dẹp.
        """
        try:
            if not os.path.exists(self.backup_dir):
                return "Backup directory does not exist."

            # Lấy toàn bộ file backup khớp pattern backup_YYYYMMDD_HHMMSS.dump
            pattern = os.path.join(self.backup_dir, "backup_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9].dump")
            files = glob.glob(pattern)

            if not files:
                return "No backup files found for retention."

            # Parse thông tin file: tuple (filepath, datetime_object, date_str)
            backup_list = []
            filename_regex = re.compile(r"backup_(\d{8})_(\d{6})\.dump$")

            for filepath in files:
                filename = os.path.basename(filepath)
                match = filename_regex.match(filename)
                if match:
                    date_part, time_part = match.groups()
                    try:
                        dt = datetime.strptime(f"{date_part}_{time_part}", "%Y%m%d_%H%M%S")
                        backup_list.append((filepath, dt, date_part))
                    except ValueError:
                        continue

            # Sắp xếp danh sách file theo thời gian từ mới nhất đến cũ nhất
            backup_list.sort(key=lambda x: x[1], reverse=True)

            files_to_keep = set()

            # Quy tắc 1: Giữ 48 bản backup mới nhất
            latest_keep = backup_list[:48]
            for filepath, _, _ in latest_keep:
                files_to_keep.add(filepath)

            # Quy tắc 2: Giữ 30 daily snapshots (bản backup sớm nhất của từng ngày)
            # Nhóm các backup theo ngày (date_str)
            daily_groups = {}
            for filepath, dt, date_str in backup_list:
                if date_str not in daily_groups:
                    daily_groups[date_str] = []
                daily_groups[date_str].append((filepath, dt))

            # Sắp xếp các ngày từ gần nhất về sau và lấy tối đa 30 ngày
            sorted_dates = sorted(daily_groups.keys(), reverse=True)[:30]

            for date_str in sorted_dates:
                # Trong mỗi ngày, chọn bản backup sớm nhất làm snapshot đại diện
                day_backups = daily_groups[date_str]
                day_backups.sort(key=lambda x: x[1])  # Sắp xếp từ cũ nhất đến mới nhất của ngày đó
                earliest_backup_of_day = day_backups[0][0]
                files_to_keep.add(earliest_backup_of_day)

            # Duyệt qua toàn bộ file ban đầu, xóa các file không nằm trong danh sách cần giữ
            deleted_count = 0
            for filepath, _, _ in backup_list:
                if filepath not in files_to_keep:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception as e:
                        print(f"[Backup Warning] Failed to delete old backup file '{filepath}': {e}")

            return f"Retention applied: keeping {len(files_to_keep)} files, deleted {deleted_count} old files."

        except Exception as e:
            err_msg = f"Error applying retention policy: {e}"
            print(f"[Backup Warning] {err_msg}")
            return err_msg
