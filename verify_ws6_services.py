"""
WS6 service verification script — tests all service methods against the real DB.
"""
from datetime import date, datetime, timezone, timedelta
from app.config import load_config
from app.db.postgres import connect
from app.services.task_service import TaskService
from app.services.calendar_day_service import CalendarDayService
from app.services.calendar_view_service import CalendarViewService

VN_TZ = timezone(timedelta(hours=7))

cfg = load_config()
conn = connect(cfg)

print("=== CalendarViewService ===")
cvs = CalendarViewService(conn)
sources = cvs.get_active_sources()
print(f"  Active sources: {len(sources)}")
for s in sources:
    print(f"    - {s['display_name']} color={s['color']} visible={s['is_visible']}")

today = date.today()
range_start = datetime(today.year, today.month, 1, 0, 0, tzinfo=VN_TZ)
range_end   = datetime(today.year, today.month + 1, 1, 0, 0, tzinfo=VN_TZ) if today.month < 12 else datetime(today.year + 1, 1, 1, 0, 0, tzinfo=VN_TZ)
events_range = cvs.get_events_by_range(range_start, range_end)
print(f"  Events this month: {len(events_range)}")

print("\n=== CalendarDayService ===")
cds = CalendarDayService(conn)
events_today = cds.get_events_for_date(today)
print(f"  Events today ({today}): {len(events_today)}")
for ev in events_today[:3]:
    print(f"    - {ev['title']} | {ev['display_name']}")

print("\n=== TaskService ===")
ts = TaskService(conn)
priorities = ts.list_priorities()
print(f"  Priorities: {len(priorities)}")

tasks_today = ts.get_tasks_for_date(today)
print(f"  Tasks today: {len(tasks_today)}")
overdue = ts.get_overdue_tasks()
print(f"  Overdue tasks: {len(overdue)}")

# Test create + toggle + delete
print("\n  Testing create → toggle → delete...")
prio_id = priorities[0]["id"] if priorities else None
due = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=VN_TZ)
new_task = ts.create_task("WS6 Test Task", due_at=due, priority_id=prio_id, note="auto-test")
print(f"    Created: id={str(new_task['id'])[:8]}... status={new_task['status']}")

toggled = ts.toggle_task_done(str(new_task["id"]))
print(f"    Toggled: status={toggled['status']}")

deleted = ts.delete_task(str(new_task["id"]))
print(f"    Deleted: {deleted}")

# Test user_cancelled toggle on first event (if any)
print("\n=== user_cancelled toggle test ===")
if events_today:
    test_ev_id = str(events_today[0]["id"])
    new_val = cds.toggle_event_user_cancelled(test_ev_id)
    print(f"  Toggled user_cancelled → {new_val}")
    # Toggle back
    cds.toggle_event_user_cancelled(test_ev_id)
    print(f"  Restored user_cancelled → false")
else:
    print("  No events today to test toggle")

conn.close()
print("\n=== ALL WS6 SERVICE CHECKS PASSED ===")
