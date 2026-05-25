import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, date

from app.exporters.planner_dto import (
    PlannerExportDTO,
    ExportMetadata,
    ExportEvent,
    ExportSubtask,
    ExportTask,
    ExportNoteItem,
    ExportNote,
)
from app.exporters.markdown_exporter import MarkdownExporter
from app.exporters.json_exporter import JSONExporter
from app.services.export_service import ExportService

class TestExportService(unittest.TestCase):
    def setUp(self):
        self.service = ExportService()

        # Tạo dữ liệu giả lập cho DTO
        self.metadata = ExportMetadata(
            generated_at="2026-05-25 10:00:00",
            threshold_date="25/05/2026",
            description="Dữ liệu kiểm thử."
        )

        self.events = [
            ExportEvent(
                subject="Lớp Giải tích",
                time_start="07:00",
                time_end="08:30",
                location="A2-301",
                date_str="2026-05-26",
                source_name="Lịch học kỳ 2",
                event_type="class"
            ),
            ExportEvent(
                subject="Thi Vật lý",
                time_start="13:00",
                time_end="15:00",
                location="A3-102",
                date_str="2026-05-26",
                source_name="Lịch thi kỳ 2",
                event_type="exam_schedule"
            )
        ]

        self.tasks = [
            ExportTask(
                id=1,
                title="Làm bài tập lớn",
                is_completed=0,
                priority="Phải làm",
                date_str="2026-05-26",
                note="Nộp qua Teams",
                subtasks_list=[
                    ExportSubtask(content="Viết báo cáo", is_completed=1),
                    ExportSubtask(content="Vẽ biểu đồ", is_completed=0)
                ],
                context_note="UPCOMING. Tiến độ: 1/2"
            ),
            ExportTask(
                id=2,
                title="Đọc sách",
                is_completed=0,
                priority="Optional",
                date_str="2026-05-24",
                note=None,
                subtasks_list=[],
                context_note="OVERDUE (Quá hạn). Tiến độ: 0/0"
            )
        ]

        self.notes = [
            ExportNote(
                id=1,
                title="Ý tưởng AI Agent",
                body="Nghiên cứu LangGraph",
                pinned=1,
                priority="Nên làm",
                note_items=[
                    ExportNoteItem(content="Đọc bài báo", is_done=1),
                    ExportNoteItem(content="Code thử", is_done=0)
                ]
            )
        ]

        self.dto = PlannerExportDTO(
            metadata=self.metadata,
            schedule_events=self.events,
            todo_tasks=self.tasks,
            notes=self.notes,
            warnings=["Trùng lịch học thử nghiệm"]
        )

    def test_markdown_exporter(self):
        markdown_output = MarkdownExporter.export(self.dto)

        # Verify markdown content
        self.assertIn("# microSchedule Export", markdown_output)
        self.assertIn("## Metadata", markdown_output)
        self.assertIn("- **Thời gian xuất**: 2026-05-25 10:00:00", markdown_output)
        self.assertIn("- **Ngày mốc lập kế hoạch**: 25/05/2026", markdown_output)

        # Verify schedule events
        self.assertIn("### 2026-05-26", markdown_output)
        self.assertIn("[07:00 - 08:30] **Lớp Giải tích** tại *A2-301*", markdown_output)

        # Verify tasks
        self.assertIn("[ ] **Làm bài tập lớn** (Hạn: 2026-05-26)", markdown_output)
        self.assertIn("[QUÁ HẠN] **Đọc sách** (Hạn: 2026-05-24)", markdown_output)

        # Verify notes
        self.assertIn("### **[GHIM]** Ý tưởng AI Agent", markdown_output)
        self.assertIn("LangGraph", markdown_output)

        # Verify warnings
        self.assertIn("> [!WARNING]", markdown_output)
        self.assertIn("Trùng lịch học thử nghiệm", markdown_output)

    def test_json_exporter(self):
        json_output = JSONExporter.export(self.dto)

        # Verify json parses and keys exist
        import json
        data = json.loads(json_output)

        self.assertEqual(data["metadata"]["generated_at"], "2026-05-25 10:00:00")
        self.assertEqual(len(data["schedule_events"]), 2)
        self.assertEqual(data["schedule_events"][0]["subject"], "Lớp Giải tích")
        self.assertEqual(data["todo_tasks"][0]["title"], "Làm bài tập lớn")
        self.assertEqual(data["todo_tasks"][0]["subtasks_list"][0]["content"], "Viết báo cáo")
        self.assertEqual(data["notes"][0]["title"], "Ý tưởng AI Agent")
        self.assertEqual(data["warnings"][0], "Trùng lịch học thử nghiệm")

    def test_conflict_detection(self):
        # 1. Trùng lặp
        overlapped_events = [
            ExportEvent(
                subject="Event A", time_start="08:00", time_end="10:00",
                location="R1", date_str="2026-05-25", source_name="S1", event_type="E1"
            ),
            ExportEvent(
                subject="Event B", time_start="09:00", time_end="11:00",
                location="R2", date_str="2026-05-25", source_name="S1", event_type="E1"
            )
        ]
        warnings = self.service._detect_conflicts(overlapped_events)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Trùng lịch", warnings[0])
        self.assertIn("Event A", warnings[0])
        self.assertIn("Event B", warnings[0])

        # 2. Không trùng lặp (nối tiếp nhau)
        non_overlapped_events = [
            ExportEvent(
                subject="Event A", time_start="08:00", time_end="09:00",
                location="R1", date_str="2026-05-25", source_name="S1", event_type="E1"
            ),
            ExportEvent(
                subject="Event B", time_start="09:00", time_end="10:00",
                location="R2", date_str="2026-05-25", source_name="S1", event_type="E1"
            )
        ]
        warnings = self.service._detect_conflicts(non_overlapped_events)
        self.assertEqual(len(warnings), 0)

    @patch("app.services.export_service.ExportService.get_settings")
    def test_generate_export_data_mock(self, mock_get_settings):
        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Cài đặt mock settings
        mock_get_settings.return_value = {
            "export.default_format": "markdown",
            "export.include_notes": True,
            "export.include_completed": False,
            "export.lookahead_days": None
        }

        # Giả lập dữ liệu trả về cho cursor.fetchall() theo thứ tự gọi:
        # Lần 1: calendar_events
        # Lần 2: tasks
        # Lần 3: task_items (cho task id 1)
        # Lần 4: notes
        # Lần 5: note_items (cho note id 10)

        mock_cursor.fetchall.side_effect = [
            # 1. Calendar events
            [
                ("Học Máy", datetime(2026, 5, 26, 8, 0), datetime(2026, 5, 26, 9, 30), "Room 201", "class", "Lịch kỳ 2")
            ],
            # 2. Tasks
            [
                (1, "Nộp bài tập", "Gửi qua mail", "Phải làm", date(2026, 5, 26), "open", None)
            ],
            # 3. Task items
            [
                ("Hoàn thành code", 0)
            ],
            # 4. Notes
            [
                (10, "Memo họp nhóm", "Bàn về v2", 1, "Nên làm")
            ],
            # 5. Note items
            [
                ("Phân chia công việc", 1)
            ]
        ]

        threshold_dt = datetime(2026, 5, 25, 0, 0, 0)
        dto = self.service.generate_export_data(mock_conn, threshold_dt=threshold_dt)

        # Verify DTO
        self.assertEqual(dto.metadata.threshold_date, "25/05/2026")
        self.assertEqual(len(dto.schedule_events), 1)
        self.assertEqual(dto.schedule_events[0].subject, "Học Máy")
        self.assertEqual(dto.schedule_events[0].date_str, "2026-05-26")
        self.assertEqual(dto.schedule_events[0].time_start, "08:00")

        self.assertEqual(len(dto.todo_tasks), 1)
        self.assertEqual(dto.todo_tasks[0].title, "Nộp bài tập")
        self.assertEqual(dto.todo_tasks[0].subtasks_list[0].content, "Hoàn thành code")

        self.assertEqual(len(dto.notes), 1)
        self.assertEqual(dto.notes[0].title, "Memo họp nhóm")
        self.assertEqual(dto.notes[0].note_items[0].content, "Phân chia công việc")

    @patch("app.services.export_service.ExportService.get_settings")
    def test_export_to_string_format(self, mock_get_settings):
        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Trả về các danh sách trống
        mock_cursor.fetchall.return_value = []

        mock_get_settings.return_value = {
            "export.default_format": "markdown",
            "export.include_notes": True
        }

        # Test markdown string output
        md_str = self.service.export_to_string(mock_conn, format_type="markdown")
        self.assertIn("# microSchedule Export", md_str)

        # Test json string output
        json_str = self.service.export_to_string(mock_conn, format_type="json")
        self.assertIn('"metadata"', json_str)
        self.assertIn('"schedule_events"', json_str)

if __name__ == "__main__":
    unittest.main()
