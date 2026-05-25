from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ExportMetadata:
    generated_at: str  # YYYY-MM-DD HH:MM:SS
    threshold_date: str  # DD/MM/YYYY
    date_format: str = "YYYY-MM-DD"
    description: str = "Dữ liệu dùng để lập kế hoạch ôn thi."

@dataclass
class ExportEvent:
    subject: str
    time_start: str  # HH:MM
    time_end: str    # HH:MM
    location: str
    date_str: str    # YYYY-MM-DD
    source_name: str
    event_type: str  # 'class', 'exam', 'manual', 'holiday', 'other', 'legacy'

@dataclass
class ExportSubtask:
    content: str
    is_completed: int  # 0 hoặc 1

@dataclass
class ExportTask:
    id: str
    title: str
    is_completed: int  # 0 hoặc 1
    priority: str
    date_str: str    # YYYY-MM-DD
    note: Optional[str]
    subtasks_list: List[ExportSubtask]
    context_note: str  # Ví dụ: "OVERDUE (Quá hạn). Tiến độ: X/Y" hoặc "UPCOMING. Tiến độ: X/Y"

@dataclass
class ExportNoteItem:
    content: str
    is_done: int  # 0 hoặc 1

@dataclass
class ExportNote:
    id: str
    title: str
    body: Optional[str]
    pinned: int  # 0 hoặc 1
    priority: Optional[str]
    note_items: List[ExportNoteItem]

@dataclass
class PlannerExportDTO:
    metadata: ExportMetadata
    schedule_events: List[ExportEvent]
    todo_tasks: List[ExportTask]
    notes: List[ExportNote]
    warnings: List[str] = field(default_factory=list)
