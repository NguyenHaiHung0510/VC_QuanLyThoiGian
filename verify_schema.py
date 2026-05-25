from app.config import load_config
from app.db.postgres import connect

cfg = load_config()
conn = connect(cfg)
cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type, column_default
    FROM information_schema.columns
    WHERE table_name = 'calendar_events' AND column_name = 'user_cancelled'
""")
row = cur.fetchone()
print('user_cancelled column:', row)

# Also check counts
cur.execute("SELECT cs.display_name, cs.is_visible, COUNT(ce.id) AS total FROM calendar_sources cs LEFT JOIN calendar_events ce ON ce.source_id = cs.id AND ce.status = 'active' GROUP BY cs.id, cs.display_name, cs.is_visible")
rows = cur.fetchall()
for r in rows:
    print(f'  source: {r[0]}, visible={r[1]}, events={r[2]}')

cur.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
for r in cur.fetchall():
    print(f'  tasks: status={r[0]}, count={r[1]}')

conn.close()
print("All DB checks OK")
