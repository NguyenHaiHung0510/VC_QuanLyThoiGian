# EXPORT_GUIDE.md - JSON Schema + AI Integration

Tài liệu này mô tả cách thức export dữ liệu từ microSchedule sang JSON và cách integrate với AI systems.

## 1. Export Flow

### 1.1 Trigger Points

Export có thể được trigger từ ba cách:

```python
# 1. Menu action (UI button)
def export_data_to_json(e):
    # Dialog: "Save to file" or "Copy to clipboard"

# 2. Direct call (programmatic)
data = generate_planner_data()

# 3. Batch export (future)
# export_all_tasks_since_date(threshold_date)
```

### 1.2 Core Function: `generate_planner_data()`

```python
def generate_planner_data():
    """
    Aggregates data từ database và tạo structured JSON.

    Flow:
    1. Determine threshold (current_date)
    2. Query 3 entities: schedule, tasks, subtasks
    3. Enrich với context (OVERDUE/UPCOMING, progress)
    4. Return structured dict
    """
    threshold_dt = current_date
    threshold_iso = threshold_dt.strftime("%Y-%m-%d")

    # ... queries ...

    final_data = {
        "metadata": {...},
        "schedule_events": [...],
        "todo_tasks": [...]
    }
    return final_data
```

---

## 2. JSON Schema

### 2.1 Complete Schema (with examples)

```json
{
  "metadata": {
    "generated_at": "2025-05-25 14:35:22",
    "threshold_date": "25/05/2025",
    "date_format": "YYYY-MM-DD",
    "description": "Dữ liệu dùng để lập kế hoạch ôn thi."
  },

  "schedule_events": [
    {
      "subject": "Math Midterm",
      "time_start": "07:00",
      "time_end": "09:00",
      "location": "Room A2",
      "date_str": "2025-05-26"
    },
    {
      "subject": "Physics Class",
      "time_start": "13:00",
      "time_end": "14:30",
      "location": "Online",
      "date_str": "2025-05-27"
    }
  ],

  "todo_tasks": [
    {
      "id": 1,
      "title": "Review Chapter 3-5",
      "is_completed": 0,
      "priority": "Phải làm",
      "date_str": "2025-05-26",
      "note": "Focus on derivatives",
      "subtasks_list": [
        {
          "content": "Read pages 45-60",
          "is_completed": 1
        },
        {
          "content": "Do practice problems 1-10",
          "is_completed": 0
        }
      ],
      "context_note": "UPCOMING. Tiến độ: 1/2"
    },
    {
      "id": 3,
      "title": "Complete Assignment 2",
      "is_completed": 0,
      "priority": "Optional",
      "date_str": "2025-05-24",
      "note": null,
      "subtasks_list": [],
      "context_note": "OVERDUE (Quá hạn). Tiến độ: 0/0"
    }
  ]
}
```

### 2.2 Schema Specification

#### Metadata
| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | string | ISO 8601 timestamp (YYYY-MM-DD HH:MM:SS) |
| `threshold_date` | string | Vietnamese format (DD/MM/YYYY) |
| `date_format` | string | Reference format (always "YYYY-MM-DD") |
| `description` | string | Human-readable description |

#### Schedule Events
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | string | Yes | Event name (e.g., "Math Midterm") |
| `time_start` | string | Yes | Start time in HH:MM format |
| `time_end` | string | Yes | End time in HH:MM format |
| `location` | string | Yes | Location/classroom name |
| `date_str` | string | Yes | Date in YYYY-MM-DD format |

#### Todo Tasks
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | int | Yes | Unique task ID |
| `title` | string | Yes | Task name |
| `is_completed` | int | Yes | 0 = incomplete, 1 = complete |
| `priority` | string | Yes | Priority name (see section 3.2) |
| `date_str` | string | Yes | Due date in YYYY-MM-DD |
| `note` | string/null | No | Additional notes |
| `subtasks_list` | array | Yes | Array of subtask objects |
| `context_note` | string | Yes | "OVERDUE/UPCOMING. Tiến độ: X/Y" |

#### Subtask Object
| Field | Type | Description |
|-------|------|-------------|
| `content` | string | Subtask description |
| `is_completed` | int | 0 = incomplete, 1 = complete |

### 2.3 Query Logic (Data Assembly)

#### Step 1: Get Schedule
```python
query_schedule = """
    SELECT subject, time_start, time_end, location, date_str
    FROM schedule
    WHERE date_str >= ?
    ORDER BY date_str ASC, time_start ASC
"""
cur.execute(query_schedule, (threshold_iso,))
schedules = rows_to_dicts(cur, cur.fetchall())
```

**Logic**: Lấy tất cả schedule events từ `threshold_date` trở đi (inclusive).

#### Step 2: Get Tasks
```python
query_tasks = """
    SELECT id, title, is_completed, priority, date_str, note
    FROM tasks
    WHERE date_str >= ?
       OR (date_str < ? AND is_completed = 0)
    ORDER BY date_str ASC
"""
cur.execute(query_tasks, (threshold_iso, threshold_iso))
tasks_raw = rows_to_dicts(cur, cur.fetchall())
```

**Logic**:
- Include: Tasks từ `threshold_date` trở đi
- Include: Incomplete tasks từ quá khứ (OVERDUE)
- Exclude: Completed tasks từ quá khứ

#### Step 3: Enrich Tasks with Subtasks
```python
for task in tasks_raw:
    # Get subtasks
    query_sub = """
        SELECT content, is_completed
        FROM subtasks
        WHERE task_id = ?
    """
    cur.execute(query_sub, (task["id"],))
    subtasks = rows_to_dicts(cur, cur.fetchall())

    # Calculate progress
    task["subtasks_list"] = subtasks
    total_sub = len(subtasks)
    done_sub = sum(1 for s in subtasks if s["is_completed"] == 1)

    # Create context note
    task_dt = datetime.strptime(task["date_str"], "%Y-%m-%d")
    if task_dt.date() < threshold_dt.date() and task["is_completed"] == 0:
        task["context_note"] = f"OVERDUE (Quá hạn). Tiến độ: {done_sub}/{total_sub}"
    else:
        task["context_note"] = f"UPCOMING. Tiến độ: {done_sub}/{total_sub}"
```

---

## 3. AI Integration Strategy

### 3.1 Use Cases

#### Use Case 1: Revision Planner
```
Input: JSON export (threshold = today)
Processing: AI analyzes schedule + tasks → creates study timeline
Output: "Recommended schedule for next 7 days"
```

#### Use Case 2: Progress Tracker
```
Input: JSON export (multiple dates)
Processing: AI detects overdue tasks → prioritizes
Output: "Action plan for catching up"
```

#### Use Case 3: Time Optimizer
```
Input: JSON export + user calendar
Processing: AI finds free slots → maps to tasks
Output: "Optimized study schedule"
```

### 3.2 Integration Points

#### Option A: Clipboard-based (Current)
```python
# User exports → copy to clipboard
page.set_clipboard(json_string)

# User pastes into AI chat (ChatGPT, Claude, etc.)
# AI processes JSON directly
```

**Pros**:
- Zero setup
- Works with any AI platform
- User has control

**Cons**:
- Manual workflow
- JSON limited by clipboard size (~64KB)
- No real-time sync

#### Option B: File-based Export
```python
# User exports → save to disk
with open("planner_data.json", "w") as f:
    json.dump(data, f, indent=2)

# AI reads file via upload
# Some AI platforms support JSON parsing
```

**Pros**:
- No clipboard size limit
- Can archive historical exports
- Structured format

**Cons**:
- Still manual (need to upload)
- File management overhead

#### Option C: API-based (Future)
```python
# microSchedule runs API server
# POST /api/export → returns JSON
# AI system (e.g., FANG) subscribes to updates
# Real-time sync enabled
```

**Pros**:
- Fully automated
- Real-time
- Can integrate with larger systems

**Cons**:
- Requires network setup
- Security considerations
- Out of scope for current version

### 3.3 AI Prompt Template

When using JSON with AI, recommended prompt structure:

```markdown
# Study Planner Context

You are a study planning assistant. Here is my current schedule and task list:

<schedule_and_tasks_json_here>

## Analysis Questions:
1. What are my overdue tasks?
2. What's an optimal study sequence?
3. Which topics are blocking others?
4. Recommend a daily schedule

## Format:
- Concise bullet points
- Prioritize by context_note (OVERDUE first)
- Consider time_start/time_end constraints
```

### 3.4 JSON Field Mapping for AI

| JSON Field | AI Use | Example |
|-----------|--------|---------|
| `threshold_date` | Reference point | "Planning from 25/05/2025" |
| `priority` | Ranking signal | "Nguy hiểm" → must do |
| `context_note` | Urgency signal | "OVERDUE" → priority |
| `date_str` | Time constraint | Can't schedule past date |
| `time_start/time_end` | Calendar conflict detection | "This time slot is taken" |
| `subtasks_list` | Decomposition analysis | "5 steps remaining" |

---

## 4. Export Formats & Variants

### 4.1 Full Export (Current Standard)

```json
{
  "metadata": {...},
  "schedule_events": [...],
  "todo_tasks": [...]
}
```

**Use**: Complete data snapshot, AI analysis, archival

### 4.2 Minimal Export (Future)

```json
{
  "tasks": [
    {
      "title": "Review Ch3",
      "priority": "Phải làm",
      "overdue": true,
      "progress": "1/2"
    }
  ],
  "date": "2025-05-25"
}
```

**Use**: Quick summary, mobile preview

### 4.3 AI-Optimized Export (Future)

```json
{
  "today": "2025-05-25",
  "urgent_overdue": [
    {"task": "Assignment 2", "days_late": 1}
  ],
  "todays_schedule": [
    {"time": "07:00-09:00", "event": "Math Midterm"}
  ],
  "next_deadline": "2025-05-26"
}
```

**Use**: Real-time AI chat, quick decisions

---

## 5. Data Quality & Validation

### 5.1 Pre-export Checks

```python
def validate_export_data(data):
    """Sanity checks before export"""

    # Check 1: Schedule consistency
    for sched in data["schedule_events"]:
        if sched["time_start"] >= sched["time_end"]:
            warn(f"Event {sched['subject']} has invalid time range")

    # Check 2: Task date consistency
    for task in data["todo_tasks"]:
        task_date = datetime.strptime(task["date_str"], "%Y-%m-%d")
        if task_date < datetime.now().date() and task["is_completed"] == 0:
            # Expected OVERDUE context
            assert "OVERDUE" in task["context_note"]

    # Check 3: Subtask progress
    for task in data["todo_tasks"]:
        subs = task["subtasks_list"]
        if len(subs) == 0:
            assert task["context_note"].endswith("0/0")
```

### 5.2 Export Statistics

```python
def print_export_stats(data):
    """Print summary for user verification"""

    schedule_count = len(data["schedule_events"])
    task_count = len(data["todo_tasks"])
    overdue_count = sum(1 for t in data["todo_tasks"] if "OVERDUE" in t["context_note"])

    print(f"✅ Export complete:")
    print(f"   - {schedule_count} schedule events")
    print(f"   - {task_count} tasks ({overdue_count} overdue)")
    print(f"   - Generated: {data['metadata']['generated_at']}")
```

---

## 6. Best Practices

### For Data Consumers (AI Systems)
- ✅ Parse `metadata` first (check timestamp)
- ✅ Sort tasks by `context_note` (OVERDUE first)
- ✅ Use `subtasks_list` for decomposition
- ⚠️ Don't trust task ordering (sort by date/priority yourself)
- ⚠️ Handle null values gracefully

### For Data Producers (microSchedule)
- ✅ Always include metadata
- ✅ Use consistent date format (YYYY-MM-DD)
- ✅ Calculate progress correctly (done_sub/total_sub)
- ⚠️ Don't include internal IDs in external exports (future)
- ⚠️ Document schema changes in version notes

---

## 7. Future Enhancements

- [ ] CSV export format
- [ ] Differential export (only changed items)
- [ ] Versioned snapshots (track historical exports)
- [ ] Filtering options (by priority, date range)
- [ ] API endpoint `/export` (instead of file dialog)
- [ ] Format conversion (JSON → Markdown/Calendar)
- [ ] Real-time sync with external AI services

---

## 8. Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| JSON too large | Too many historical tasks | Filter by date, export recent only |
| Copy to clipboard failed | Clipboard locked | Try "Save to file" instead |
| AI can't parse JSON | Malformed JSON | Check with JSON validator first |
| Missing fields in export | DB query incomplete | Check database.py `generate_planner_data()` |

---
*Tài liệu cập nhật ngày 25/05/2026.*
