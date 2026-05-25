from typing import Dict, List
from .planner_dto import PlannerExportDTO, ExportEvent, ExportTask, ExportNote

class MarkdownExporter:
    @staticmethod
    def export(dto: PlannerExportDTO) -> str:
        lines = ["# microSchedule Export\n"]

        # 1. Metadata
        lines.append("## Metadata")
        lines.append(f"- **Thời gian xuất**: {dto.metadata.generated_at}")
        lines.append(f"- **Ngày mốc lập kế hoạch**: {dto.metadata.threshold_date}")
        lines.append(f"- **Mô tả**: {dto.metadata.description}\n")

        # 1.1 Warnings (nếu có)
        if dto.warnings:
            lines.append("> [!WARNING]")
            lines.append("> **Cảnh báo xung đột lịch trình detected:**")
            for warning in dto.warnings:
                lines.append(f"> - {warning}")
            lines.append("")

        # 2. Upcoming Schedule
        lines.append("## Upcoming Schedule")
        if not dto.schedule_events:
            lines.append("Không có lịch học hoặc lịch thi sắp tới.\n")
        else:
            # Nhóm events theo ngày
            events_by_date: Dict[str, List[ExportEvent]] = {}
            for event in dto.schedule_events:
                events_by_date.setdefault(event.date_str, []).append(event)

            # Sort theo ngày
            for date_str in sorted(events_by_date.keys()):
                lines.append(f"### {date_str}")
                for event in events_by_date[date_str]:
                    event_type_str = "Lịch thi" if "exam" in event.event_type.lower() else "Lịch học"
                    lines.append(
                        f"- [{event.time_start} - {event.time_end}] **{event.subject}** tại *{event.location}* ({event.source_name} - {event_type_str})"
                    )
            lines.append("")

        # 3. Open Tasks
        lines.append("## Open Tasks")
        if not dto.todo_tasks:
            lines.append("Không có công việc nào cần hoàn thành.\n")
        else:
            for task in dto.todo_tasks:
                status_box = "[x]" if task.is_completed == 1 else "[ ]"
                overdue_prefix = "[QUÁ HẠN] " if "OVERDUE" in task.context_note else ""
                lines.append(
                    f"- {status_box} {overdue_prefix}**{task.title}** (Hạn: {task.date_str}) | Độ ưu tiên: {task.priority} | {task.context_note}"
                )
                if task.note:
                    lines.append(f"  - *Ghi chú*: {task.note}")

                # Render subtasks
                for sub in task.subtasks_list:
                    sub_box = "[x]" if sub.is_completed == 1 else "[ ]"
                    lines.append(f"  - {sub_box} {sub.content}")
            lines.append("")

        # 4. Notes
        lines.append("## Notes")
        if not dto.notes:
            lines.append("Không có ghi chú nào.\n")
        else:
            for note in dto.notes:
                pin_prefix = "**[GHIM]** " if note.pinned == 1 else ""
                priority_suffix = f" (Độ ưu tiên: {note.priority})" if note.priority else ""
                lines.append(f"### {pin_prefix}{note.title}{priority_suffix}")
                if note.body:
                    lines.append(f"{note.body}")

                # Render note items
                for item in note.note_items:
                    item_box = "[x]" if item.is_done == 1 else "[ ]"
                    lines.append(f"- {item_box} {item.content}")
                lines.append("")

        # 5. Suggested AI Instructions
        lines.append("## Suggested AI Instructions")
        lines.append(
            "Bạn có thể sao chép toàn bộ nội dung Markdown trên và dán vào Chat AI (ChatGPT, Claude, Gemini) kèm theo câu lệnh sau:\n"
        )
        lines.append("```markdown")
        lines.append("Dưới đây là lịch học/thi, danh sách công việc cần làm và các ghi chú cá nhân của tôi.")
        lines.append("Hãy giúp tôi phân tích xem có công việc nào quá hạn cần ưu tiên xử lý gấp hay không,")
        lines.append("phát hiện các xung đột lịch trình, và xây dựng một kế hoạch học tập/làm việc tối ưu cho 7 ngày tới.")
        lines.append("```")

        return "\n".join(lines)
