CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS priorities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL UNIQUE,
    label text NOT NULL,
    color text NOT NULL,
    icon text NULL,
    sort_order integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS calendar_sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name text NOT NULL UNIQUE,
    kind text NOT NULL,
    academic_year integer NULL,
    term text NULL,
    sort_start_date date NULL,
    color text NOT NULL,
    is_visible boolean NOT NULL DEFAULT true,
    current_version_id uuid NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT calendar_sources_kind_check CHECK (
        kind IN (
            'study_schedule',
            'exam_schedule',
            'manual_task_calendar',
            'holiday',
            'other',
            'legacy_v1'
        )
    )
);

CREATE TABLE IF NOT EXISTS calendar_source_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES calendar_sources(id) ON DELETE CASCADE,
    version_number integer NOT NULL,
    file_name text NULL,
    file_sha256 text NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    parser_version text NOT NULL,
    status text NOT NULL,
    summary_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT calendar_source_versions_status_check CHECK (
        status IN ('active', 'duplicate_noop', 'failed', 'superseded')
    ),
    CONSTRAINT calendar_source_versions_source_version_unique UNIQUE (
        source_id,
        version_number
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS calendar_source_versions_source_sha_unique
    ON calendar_source_versions(source_id, file_sha256)
    WHERE file_sha256 IS NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'calendar_sources_current_version_fk'
    ) THEN
        ALTER TABLE calendar_sources
            ADD CONSTRAINT calendar_sources_current_version_fk
            FOREIGN KEY (current_version_id)
            REFERENCES calendar_source_versions(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS calendar_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES calendar_sources(id),
    source_version_id uuid NOT NULL REFERENCES calendar_source_versions(id) ON DELETE CASCADE,
    external_uid text NULL,
    content_hash text NOT NULL,
    title text NOT NULL,
    description text NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    location text NULL,
    event_type text NOT NULL,
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT calendar_events_event_type_check CHECK (
        event_type IN ('class', 'exam', 'manual', 'holiday', 'other', 'legacy')
    ),
    CONSTRAINT calendar_events_status_check CHECK (
        status IN ('active', 'cancelled', 'tentative')
    ),
    CONSTRAINT calendar_events_time_check CHECK (ends_at > starts_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS calendar_events_version_uid_unique
    ON calendar_events(source_version_id, external_uid)
    WHERE external_uid IS NOT NULL;
CREATE INDEX IF NOT EXISTS calendar_events_source_version_idx
    ON calendar_events(source_id, source_version_id);
CREATE INDEX IF NOT EXISTS calendar_events_time_idx
    ON calendar_events(starts_at, ends_at);

CREATE TABLE IF NOT EXISTS tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    note text NULL,
    priority_id uuid NULL REFERENCES priorities(id),
    due_at timestamptz NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz NULL,
    CONSTRAINT tasks_status_check CHECK (status IN ('open', 'completed', 'archived'))
);

CREATE TABLE IF NOT EXISTS task_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    content text NOT NULL,
    is_completed boolean NOT NULL DEFAULT false,
    position integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    body text NULL,
    priority_id uuid NULL REFERENCES priorities(id),
    pinned boolean NOT NULL DEFAULT false,
    archived_at timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS note_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id uuid NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    content text NOT NULL,
    is_done boolean NOT NULL DEFAULT false,
    position integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_settings (
    key text PRIMARY KEY,
    value_json jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backup_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind text NOT NULL,
    status text NOT NULL,
    artifact_path text NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz NULL,
    message text NULL
);

CREATE TABLE IF NOT EXISTS agent_action_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor text NOT NULL,
    action_type text NOT NULL,
    tool_name text NOT NULL,
    permission_scope text NOT NULL,
    status text NOT NULL,
    target_summary_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    before_json jsonb NULL,
    after_json jsonb NULL,
    rollback_json jsonb NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
