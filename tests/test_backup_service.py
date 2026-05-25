import os
import unittest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
import uuid

from app.services.backup_service import BackupService

class TestBackupService(unittest.TestCase):
    def setUp(self):
        # Thiết lập BackupService với URL giả lập
        self.db_url = "postgresql://postgres@localhost:5432/microschedule_v2"
        with patch.dict(os.environ, {"DATABASE_URL": self.db_url, "MICROSCHEDULE_DATA_DIR": r"C:\fake\dir"}):
            self.service = BackupService()

    def test_parse_db_url_success(self):
        """Xác thực hàm parse_db_url xử lý đúng URL PostgreSQL hợp lệ"""
        url = "postgresql://myuser:test-password@127.0.0.1:9999/mydb"
        params = self.service._parse_db_url(url)

        self.assertEqual(params["username"], "myuser")
        self.assertEqual(params["password"], "test-password")
        self.assertEqual(params["hostname"], "127.0.0.1")
        self.assertEqual(params["port"], 9999)
        self.assertEqual(params["database"], "mydb")

    def test_parse_db_url_defaults(self):
        """Xác thực hàm parse_db_url điền đúng các giá trị mặc định"""
        url = "postgresql://localhost/mydb"
        params = self.service._parse_db_url(url)

        self.assertEqual(params["username"], "postgres")
        self.assertIsNone(params["password"])
        self.assertEqual(params["hostname"], "localhost")
        self.assertEqual(params["port"], 5432)
        self.assertEqual(params["database"], "mydb")

    def test_parse_db_url_invalid_scheme(self):
        """Xác thực hàm parse_db_url báo lỗi khi gặp scheme không được hỗ trợ"""
        url = "mysql://localhost/mydb"
        with self.assertRaises(ValueError):
            self.service._parse_db_url(url)

    def test_parse_db_url_empty(self):
        """Xác thực hàm parse_db_url báo lỗi khi URL rỗng"""
        with self.assertRaises(ValueError):
            self.service._parse_db_url("")

    @patch("app.services.backup_service.glob.glob")
    @patch("app.services.backup_service.os.remove")
    @patch("app.services.backup_service.os.path.exists")
    def test_apply_retention_policy_logic(self, mock_exists, mock_remove, mock_glob):
        """Kiểm tra giải thuật lọc retention policy (48 bản mới nhất + 30 daily snapshots)"""
        mock_exists.return_value = True

        # Giả lập danh sách file backup
        # Tạo 100 file backup trải dài trên 40 ngày (mỗi ngày 2-3 file backup cách nhau vài giờ)
        fake_files = []
        base_time = datetime(2026, 5, 25, 12, 0, 0)

        for day in range(40):
            current_date = base_time - timedelta(days=day)
            date_str = current_date.strftime("%Y%m%d")

            # File backup 1 của ngày (lúc 08:00:00) -> backup sớm nhất của ngày
            file1 = os.path.join(self.service.backup_dir, f"backup_{date_str}_080000.dump")
            fake_files.append(file1)

            # File backup 2 của ngày (lúc 12:00:00)
            file2 = os.path.join(self.service.backup_dir, f"backup_{date_str}_120000.dump")
            fake_files.append(file2)

            # File backup 3 của ngày (lúc 20:00:00)
            file3 = os.path.join(self.service.backup_dir, f"backup_{date_str}_200000.dump")
            fake_files.append(file3)

        mock_glob.return_value = fake_files

        # Chạy logic retention
        retention_msg = self.service.apply_retention_policy()

        # Tính toán thủ công danh sách file nên được giữ:
        # Tổng số file: 120 files
        # 1. 48 file mới nhất: tương đương 16 ngày gần nhất (16 ngày * 3 file/ngày = 48 files)
        #    Tức là các file từ ngày 2026-05-25 về trước đến ngày 2026-05-10
        # 2. 30 daily snapshots (bản sớm nhất của 30 ngày có backup gần nhất):
        #    Các ngày từ 2026-05-25 đến 2026-04-26 (30 ngày gần nhất)
        #    Bản sớm nhất của mỗi ngày đó (file lúc 080000)
        #
        # Xác minh xem mock_remove có được gọi đúng số lần và đúng file không
        keep_set = set()

        # Danh sách file sắp xếp theo thời gian mới nhất -> cũ nhất (ngược lại với thứ tự tạo)
        sorted_fake_backups = []
        for file_path in fake_files:
            filename = os.path.basename(file_path)
            parts = filename.split("_")
            date_part, time_part = parts[1], parts[2].split(".")[0]
            dt = datetime.strptime(f"{date_part}_{time_part}", "%Y%m%d_%H%M%S")
            sorted_fake_backups.append((file_path, dt, date_part))
        sorted_fake_backups.sort(key=lambda x: x[1], reverse=True)

        # Thêm 48 bản mới nhất vào keep_set
        for f, _, _ in sorted_fake_backups[:48]:
            keep_set.add(f)

        # Thêm 30 daily snapshots (bản sớm nhất của từng ngày trong 30 ngày gần nhất)
        daily_groups = {}
        for f, dt, date_str in sorted_fake_backups:
            if date_str not in daily_groups:
                daily_groups[date_str] = []
            daily_groups[date_str].append((f, dt))

        sorted_dates = sorted(daily_groups.keys(), reverse=True)[:30]
        for date_str in sorted_dates:
            day_backups = daily_groups[date_str]
            day_backups.sort(key=lambda x: x[1])  # cũ nhất đến mới nhất của ngày đó -> lấy bản sớm nhất (lúc 08:00:00)
            keep_set.add(day_backups[0][0])

        expected_remove_calls = []
        for f, _, _ in sorted_fake_backups:
            if f not in keep_set:
                expected_remove_calls.append(call(f))

        # Tổng số file bị xóa dự kiến = Tổng file (120) - số file được giữ
        expected_keep_count = len(keep_set)
        expected_deleted_count = len(fake_files) - expected_keep_count

        self.assertEqual(mock_remove.call_count, expected_deleted_count)
        self.assertIn(f"keeping {expected_keep_count} files", retention_msg)
        self.assertIn(f"deleted {expected_deleted_count} old files", retention_msg)

    @patch("app.services.backup_service.subprocess.run")
    @patch("app.services.backup_service.os.replace")
    @patch("app.services.backup_service.os.makedirs")
    @patch("app.services.backup_service.psycopg.connect")
    def test_backup_now_success(self, mock_db_connect, mock_makedirs, mock_replace, mock_subprocess_run):
        """Kiểm tra luồng backup_now chạy thành công"""
        # Mock subprocess.run trả về thành công
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_subprocess_run.return_value = mock_process

        # Mock DB connection
        mock_conn = MagicMock()
        mock_db_connect.return_value.__enter__.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        # Chạy backup
        result = self.service.backup_now(kind="manual")

        self.assertTrue(result["success"])
        self.assertIsNotNone(result["artifact_path"])
        self.assertTrue(result["artifact_path"].endswith(".dump"))
        self.assertIn("Backup completed successfully", result["message"])

        # Xác minh pg_dump được gọi với tham số chuẩn
        mock_subprocess_run.assert_called_once()
        cmd_args = mock_subprocess_run.call_args[0][0]
        self.assertIn("pg_dump", cmd_args)
        self.assertIn("-F", cmd_args)
        self.assertIn("c", cmd_args)
        self.assertIn("-b", cmd_args)

        # Xác minh file tạm được replace thành file chính thức
        mock_replace.assert_called_once()

    @patch("app.services.backup_service.subprocess.run")
    @patch("app.services.backup_service.os.makedirs")
    @patch("app.services.backup_service.psycopg.connect")
    @patch("app.services.backup_service.os.path.exists")
    @patch("app.services.backup_service.os.remove")
    def test_backup_now_failure(self, mock_remove, mock_exists, mock_db_connect, mock_makedirs, mock_subprocess_run):
        """Kiểm tra luồng backup_now gặp lỗi pg_dump"""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Command not found or backup error"
        mock_subprocess_run.return_value = mock_process

        mock_exists.return_value = True

        mock_conn = MagicMock()
        mock_db_connect.return_value.__enter__.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        # Chạy backup
        result = self.service.backup_now(kind="manual")

        self.assertFalse(result["success"])
        self.assertIsNone(result["artifact_path"])
        self.assertIn("pg_dump failed with exit code 1", result["message"])

        # Xác minh có dọn dẹp file tạm khi lỗi
        mock_remove.assert_called_once()

if __name__ == "__main__":
    unittest.main()
