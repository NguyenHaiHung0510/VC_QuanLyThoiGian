# DATABASE_SCHEMA.md - Table Relationships & Constraints

Tài liệu này mô tả chi tiết cấu trúc SQLite database của microSchedule, bao gồm table relationships, constraints, và quy tắc dữ liệu.

## 1. Database Overview

```
SQLite Database: todo.db
Location: C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db
Backup: backups\todo_backup_YYYYMMDD_HHMMSS.db (max 15)

Tables:
1. tasks          (Core entities)
2. subtasks       (Decomposition)
3. schedule       (Calendar events)
4. settings       (Configuration)
```

---

## 2. Table Definitions

### 2.1 `tasks` Table

**Purpose**: Store user's to-do items with priority and deadline

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    is_completed INTEGER DEFAULT 0,
    priority TEXT DEFAULT 'Nên làm',
    date_str TEXT,
    note TEXT
)
```

#### Column Specification

| Column | Type | PK | NN | Default | Description |
|--------|------|----|----|---------|-------------|
| `id` | INTEGER | ✓ | ✓ | AUTO | Unique task identifier |
| `title` | TEXT | | ✓ | | Task name (e.g., "Review Chapter 3") |
| `is_completed` | INTEGER | | | 0 | 0=incomplete, 1=complete |
| `priority` | TEXT | | | 'Nên làm' | Priority level (see section 3.2) |
| `date_str` | TEXT | | ✓ | | Due date (YYYY-MM-DD format) |
| `note` | TEXT | | | | Optional notes/description |

#### Constraints

```sql
-- Implicit (via SQL schema)
-- No explicit CHECK constraints (lỏng hơn, dễ develop)

-- Recommended future constraints:
-- CHECK (priority IN ('Optional', 'Nên làm', 'Phải làm', 'Bỏ là nhót', 'Nguy hiểm'))
-- CHECK (is_completed IN (0, 1))
-- CHECK (date_str GLOB '????-??-??')  -- YYYY-MM-DD format
```

#### Sample Data

```sql
-- Upcoming task
INSERT INTO tasks (title, is_completed, priority, date_str, note)
VALUES ('Review Chapter 3-5', 0, 'Phải làm', '2025-05-26', 'Focus on derivatives');
-- id=1

-- Overdue task (incomplete)
INSERT INTO tasks (title, is_completed, priority, date_str, note)
VALUES ('Complete Assignment 2', 0, 'Optional', '2025-05-24', NULL);
-- id=3

-- Completed task
INSERT INTO tasks (title, is_completed, priority, date_str, note)
VALUES ('Finish Reading', 1, 'Nên làm', '2025-05-20', 'Chapters 1-2');
-- id=5
```

#### Query Examples

```sql
-- Get all incomplete tasks
SELECT id, title, priority, date_str FROM tasks
WHERE is_completed = 0;

-- Get overdue incomplete tasks
SELECT id, title, date_str FROM tasks
WHERE is_completed = 0 AND date_str < date('now');

-- Get tasks by priority
SELECT id, title, date_str FROM tasks
WHERE priority = 'Phải làm'
ORDER BY date_str ASC;

-- Count completed tasks
SELECT COUNT(*) as completed_count
FROM tasks
WHERE is_completed = 1;
```

---

### 2.2 `subtasks` Table

**Purpose**: Decompose tasks into smaller, manageable steps

```sql
CREATE TABLE IF NOT EXISTS subtasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    content TEXT,
    is_completed INTEGER DEFAULT 0
)
```

#### Column Specification

| Column | Type | PK | NN | FK | Default | Description |
|--------|------|----|----|----|---------|-----------
| `id` | INTEGER | ✓ | ✓ | | AUTO | Unique subtask identifier |
| `task_id` | INTEGER | | ✓ | tasks.id | | Parent task ID |
| `content` | TEXT | | ✓ | | | Subtask description |
| `is_completed` | INTEGER | | | | 0 | 0=incomplete, 1=complete |

#### Foreign Key Relationship

```
subtasks.task_id → tasks.id (One-to-Many)

Visual:
┌─ tasks ─────────────┐        ┌─ subtasks ──────────┐
│ id=1                │        │ id=1, task_id=1     │
│ title="Review Ch3"  │◄───────│ content="Read p.45" │
│                     │        │ id=2, task_id=1     │
│                     │◄───────│ content="Do Ex 1-10"│
│                     │        │                     │
│ id=3                │        │ id=3, task_id=3     │
│ title="Assignment 2"│◄───────│ content="Code part A"│
│                     │        └─────────────────────┘
└─────────────────────┘

Cardinality: One task → Many subtasks (1:N)
```

#### Sample Data

```sql
-- Subtasks for task_id=1
INSERT INTO subtasks (task_id, content, is_completed)
VALUES (1, 'Read pages 45-60', 1);
-- id=1

INSERT INTO subtasks (task_id, content, is_completed)
VALUES (1, 'Do practice problems 1-10', 0);
-- id=2

-- Subtasks for task_id=3
INSERT INTO subtasks (task_id, content, is_completed)
VALUES (3, 'Code part A', 0);
-- id=3
```

#### Query Examples

```sql
-- Get all subtasks for a task
SELECT id, content, is_completed FROM subtasks
WHERE task_id = 1;

-- Count completed subtasks
SELECT COUNT(*) as done_count
FROM subtasks
WHERE task_id = 1 AND is_completed = 1;

-- Get task progress (done/total)
SELECT 
    task_id,
    SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as done,
    COUNT(*) as total
FROM subtasks
WHERE task_id = 1
GROUP BY task_id;

-- Delete all subtasks for a task (cleanup on task delete)
DELETE FROM subtasks WHERE task_id = 1;
```

#### Integrity Considerations

⚠️ **Current Issue**: No explicit foreign key constraint
- If task is deleted, orphaned subtasks remain
- Recommendation: Add ON DELETE CASCADE

```sql
-- Future migration:
CREATE TABLE subtasks_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_completed INTEGER DEFAULT 0,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
```

---

### 2.3 `schedule` Table

**Purpose**: Store fixed calendar events (imported from ICS/Excel)

```sql
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    time_start TEXT,
    time_end TEXT,
    location TEXT,
    date_str TEXT,
    is_cancelled INTEGER DEFAULT 0
)
```

#### Column Specification

| Column | Type | PK | NN | Default | Description |
|--------|------|----|----|---------|-------------|
| `id` | INTEGER | ✓ | ✓ | AUTO | Unique event identifier |
| `subject` | TEXT | | ✓ | | Event name (e.g., "Math Midterm") |
| `time_start` | TEXT | | ✓ | | Start time (HH:MM format) |
| `time_end` | TEXT | | ✓ | | End time (HH:MM format) |
| `location` | TEXT | | ✓ | | Location (Room/Online) |
| `date_str` | TEXT | | ✓ | | Date (YYYY-MM-DD format) |
| `is_cancelled` | INTEGER | | | 0 | 0=active, 1=cancelled |

#### Constraints

```sql
-- Recommended future constraints:
-- CHECK (time_start GLOB '??:??')  -- HH:MM format
-- CHECK (time_end GLOB '??:??')
-- CHECK (date_str GLOB '????-??-??')  -- YYYY-MM-DD format
-- CHECK (is_cancelled IN (0, 1))
-- CHECK (time_start < time_end)  -- Logical constraint
```

#### Sample Data

```sql
-- Imported from ICS
INSERT INTO schedule (subject, time_start, time_end, location, date_str, is_cancelled)
VALUES ('Math Midterm', '07:00', '09:00', 'Room A2', '2025-05-26', 0);
-- id=1

-- Imported from Excel
INSERT INTO schedule (subject, time_start, time_end, location, date_str, is_cancelled)
VALUES ('[THI] Physics Final', '13:00', '??:??', 'Lab Building', '2025-05-27', 0);
-- id=2

-- Cancelled event
INSERT INTO schedule (subject, time_start, time_end, location, date_str, is_cancelled)
VALUES ('Class Cancelled', '10:00', '11:00', 'Room B5', '2025-05-25', 1);
-- id=3
```

#### Query Examples

```sql
-- Get today's schedule
SELECT subject, time_start, time_end, location FROM schedule
WHERE date_str = date('now') AND is_cancelled = 0
ORDER BY time_start ASC;

-- Get schedule for a week
SELECT subject, date_str, time_start, time_end FROM schedule
WHERE date_str BETWEEN '2025-05-26' AND '2025-06-01'
  AND is_cancelled = 0
ORDER BY date_str ASC, time_start ASC;

-- Find time conflicts
SELECT a.subject as event1, b.subject as event2
FROM schedule a, schedule b
WHERE a.date_str = b.date_str
  AND a.id < b.id
  AND a.time_start < b.time_end
  AND a.time_end > b.time_start;
```

---

### 2.4 `settings` Table

**Purpose**: Store application configuration as key-value pairs

```sql
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
```

#### Column Specification

| Column | Type | PK | NN | Description |
|--------|------|----|----|-------------|
| `key` | TEXT | ✓ | ✓ | Configuration key (unique) |
| `value` | TEXT | | ✓ | Configuration value (JSON string) |

#### Storage Format

Values are stored as **JSON strings** (parsed by application layer):

```python
# In database (text):
settings["locations"] = '[{"name":"A2","icon":"School"},{"name":"Home","icon":"Home"}]'

# In application (after json.loads):
locations = [{"name": "A2", "icon": "School"}, {"name": "Home", "icon": "Home"}]
```

#### Default Settings (Seeded on init)

```sql
INSERT INTO settings (key, value) VALUES ('app_title', '"microSchedule"');

INSERT INTO settings (key, value) VALUES ('locations', '[
  {"name":"A2","icon":"School"},
  {"name":"A3","icon":"School"},
  {"name":"Thư viện","icon":"Library"},
  {"name":"Home","icon":"Home"},
  {"name":"Học Online","icon":"Online"}
]');

INSERT INTO settings (key, value) VALUES ('priorities', '[
  {"name":"Optional","label":"Optional","color":"Grey","icon":"Low"},
  {"name":"Nên làm","label":"Nên làm","color":"Green","icon":"Check"},
  {"name":"Phải làm","label":"Phải làm","color":"Amber","icon":"High"},
  {"name":"Bỏ là nhót","label":"Bỏ là nhót 💀","color":"Orange","icon":"Danger"},
  {"name":"Nguy hiểm","label":"ĐẶC BIỆT NGUY HIỂM 🆘","color":"Red","icon":"Warning"}
]');

INSERT INTO settings (key, value) VALUES ('durations', '[
  {"label":"45p (1 tiết)","value":45},
  {"label":"90p (2 tiết)","value":90},
  {"label":"3h (Vibe)","value":180}
]');
```

#### Query Examples

```sql
-- Get single setting
SELECT value FROM settings WHERE key = 'app_title';
-- Returns: "microSchedule"

-- Get all settings
SELECT key, value FROM settings;

-- Update setting (upsert)
INSERT OR REPLACE INTO settings (key, value) 
VALUES ('app_title', '"My Custom App"');
```

#### Common Keys

| Key | Type | Example Value |
|-----|------|----------------|
| `app_title` | string | "microSchedule" |
| `locations` | array | [{name, icon}, ...] |
| `priorities` | array | [{name, label, color, icon}, ...] |
| `durations` | array | [{label, value}, ...] |

---

## 3. Data Relationships

### 3.1 Entity-Relationship Diagram (ERD)

```
┌──────────────────────┐
│     tasks            │
├──────────────────────┤
│ id (PK)              │
│ title                │
│ is_completed         │
│ priority             │◄──────┐
│ date_str             │       │
│ note                 │       │
└──────────────────────┘       │
         ▲                      │
         │ (1:N)                │
         │                      │  Foreign Key Reference
┌────────┴──────────────┐      │
│ subtasks             │      │
├──────────────────────┤      │
│ id (PK)              │      │
│ task_id (FK) ───────┼──────┘
│ content              │
│ is_completed         │
└──────────────────────┘

┌──────────────────────┐
│  schedule            │       (Independent - no FK)
├──────────────────────┤
│ id (PK)              │
│ subject              │
│ time_start           │
│ time_end             │
│ location             │
│ date_str             │
│ is_cancelled         │
└──────────────────────┘

┌──────────────────────┐
│  settings            │       (Configuration)
├──────────────────────┤
│ key (PK)             │
│ value (JSON)         │
└──────────────────────┘
```

### 3.2 Relationship Rules

| Relationship | Type | Rule | Notes |
|-------------|------|------|-------|
| tasks ↔ subtasks | 1:N | One task → Many subtasks | No enforcement currently |
| tasks ↔ schedule | N/A | Independent | Different concepts |
| tasks ↔ settings | N/A | Settings reference priorities | Config-based link |

---

## 4. Data Integrity & Consistency

### 4.1 Current Weaknesses

| Issue | Risk | Solution |
|-------|------|----------|
| No FK constraints | Orphaned subtasks on task delete | Add ON DELETE CASCADE |
| No CHECK constraints | Invalid priority values | Add CHECK clauses |
| No UNIQUE constraints | Duplicate entries | Add UNIQUE(date_str, time_start) for schedule |
| No transactions | Partial imports on error | Wrap in explicit transaction |
| JSON in settings | Schema-less, hard to validate | Normalize schema |

### 4.2 Recommended Migrations

**Future: Add Foreign Key Support**

```sql
-- Enable FK support (must be done before schema changes)
PRAGMA foreign_keys = ON;

-- Alter subtasks to add cascade delete
ALTER TABLE subtasks ADD CONSTRAINT fk_subtasks_task
FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
```

**Future: Add Constraints**

```sql
-- Add constraint to priorities
ALTER TABLE tasks ADD CONSTRAINT check_priority
CHECK (priority IN ('Optional', 'Nên làm', 'Phải làm', 'Bỏ là nhót', 'Nguy hiểm'));

-- Add constraint to schedule (no time conflicts in same location)
CREATE UNIQUE INDEX idx_schedule_time_location
ON schedule(date_str, location, time_start);
```

---

## 5. Query Patterns

### 5.1 Common Queries (from application code)

**Task Management**:
```sql
-- Load tasks for export (with task date logic)
SELECT id, title, is_completed, priority, date_str, note FROM tasks
WHERE date_str >= '2025-05-25' OR (date_str < '2025-05-25' AND is_completed = 0);

-- Mark task complete
UPDATE tasks SET is_completed = 1 WHERE id = ?;

-- Delete task (should cascade to subtasks)
DELETE FROM tasks WHERE id = ?;
```

**Subtask Management**:
```sql
-- Get all subtasks for a task
SELECT id, content, is_completed FROM subtasks WHERE task_id = ?;

-- Count subtask progress
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed
FROM subtasks WHERE task_id = ?;
```

**Schedule Management**:
```sql
-- Get schedule for a date
SELECT subject, time_start, time_end, location FROM schedule
WHERE date_str = ? AND is_cancelled = 0;

-- Get future schedule
SELECT subject, time_start, time_end, location, date_str FROM schedule
WHERE date_str >= ? ORDER BY date_str ASC, time_start ASC;
```

**Settings Management**:
```sql
-- Get all settings (used on app startup)
SELECT key, value FROM settings;

-- Update single setting
INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);
```

---

## 6. Performance Considerations

### 6.1 Indexing Strategy

**Recommended indexes** (for faster queries):

```sql
-- Speed up task queries by date
CREATE INDEX idx_tasks_date ON tasks(date_str);
CREATE INDEX idx_tasks_is_completed ON tasks(is_completed);

-- Speed up schedule queries
CREATE INDEX idx_schedule_date ON schedule(date_str);
CREATE INDEX idx_schedule_date_time ON schedule(date_str, time_start);

-- Speed up subtask queries
CREATE INDEX idx_subtasks_task_id ON subtasks(task_id);
```

**Current Status**: No indexes created (development stage)

### 6.2 Query Performance

| Query | Estimated Cost | Notes |
|-------|----------------|-------|
| SELECT tasks WHERE date_str >= ? | O(n) | Full table scan (need idx_tasks_date) |
| SELECT subtasks WHERE task_id = ? | O(n) | Full table scan (need idx_subtasks_task_id) |
| SELECT schedule WHERE date_str = ? | O(n) | Full table scan (need idx_schedule_date) |

---

## 7. Backup & Recovery

### 7.1 Backup Strategy

**File Location**: `C:\Users\os\Desktop\Tools\VC_microSchedule_home\backups\`

**Naming**: `todo_backup_YYYYMMDD_HHMMSS.db`

**Automatic Backup**:
- Trigger: Every 2 hours (smart check)
- Max files: 15 (oldest deleted)
- Size: ~50-200KB per backup

**Manual Recovery**:
```python
# Restore from backup (manual process)
import shutil
latest_backup = "backups/todo_backup_20250525_143000.db"
shutil.copy2(latest_backup, "todo.db")
```

---

## 8. Migration Guide

### 8.1 Manual Schema Update

**If you need to add a column**:

```sql
-- Example: Add 'created_at' timestamp to tasks
ALTER TABLE tasks ADD COLUMN created_at TEXT DEFAULT '2025-05-25';
```

**If you need to rename a table**:

```sql
-- Backup first!
ALTER TABLE tasks RENAME TO tasks_old;
-- Create new schema...
INSERT INTO tasks SELECT * FROM tasks_old;
DROP TABLE tasks_old;
```

### 8.2 Data Migration Workflow

1. **Backup current database**: `cp todo.db todo.db.backup`
2. **Test migration on copy**: Do migration on backup first
3. **Create migration script**: SQL statements
4. **Apply to production**: Run migration
5. **Verify**: Spot-check data, run queries
6. **Archive backup**: Keep for historical reference

---

## 9. Best Practices

### Do's ✅
- ✅ Always backup before major changes
- ✅ Use transactions for multi-table changes
- ✅ Validate data on import (check NOT NULL fields)
- ✅ Use parameterized queries (prevent SQL injection)
- ✅ Define indexes for frequently queried columns
- ✅ Document schema changes in version notes

### Don'ts ❌
- ❌ Modify schema without backup
- ❌ Hard-delete data (use soft delete: is_cancelled/is_archived)
- ❌ Store complex objects in TEXT (use JSON normalization)
- ❌ Mix data types (keep date format consistent)
- ❌ Assume application-layer FK constraints exist
- ❌ Forget to update queries after schema changes

---

## 10. Future Schema Enhancements

- [ ] Add timestamps (created_at, updated_at) to all tables
- [ ] Add user_id column (support multi-user in future)
- [ ] Normalize settings table (separate table for each type)
- [ ] Add soft-delete flags (archive instead of delete)
- [ ] Add sync_version column (for cloud sync)
- [ ] Create audit log table (track changes)

---

## Appendix: SQL Commands Reference

### Initialize Database

```sql
-- Run once on app start
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    is_completed INTEGER DEFAULT 0,
    priority TEXT DEFAULT 'Nên làm',
    date_str TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS subtasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    content TEXT,
    is_completed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    time_start TEXT,
    time_end TEXT,
    location TEXT,
    date_str TEXT,
    is_cancelled INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### Verify Schema

```sql
-- Check table structure
.schema tasks
.schema subtasks
.schema schedule
.schema settings

-- Count records
SELECT COUNT(*) as task_count FROM tasks;
SELECT COUNT(*) as subtask_count FROM subtasks;
SELECT COUNT(*) as schedule_count FROM schedule;
SELECT COUNT(*) as setting_count FROM settings;
```

---

*Tài liệu cập nhật ngày 25/05/2026.*
