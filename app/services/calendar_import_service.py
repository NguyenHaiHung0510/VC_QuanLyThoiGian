import os
import hashlib
import json
from typing import Dict, Any, List

from app.importers.ics_importer import IcsImporter
from app.importers.excel_exam_importer import ExcelExamImporter

class CalendarImportService:
    def __init__(self, conn):
        """
        Accepts a psycopg connection object for dependency injection.
        """
        self.conn = conn

    def calculate_sha256(self, file_path: str) -> str:
        """
        Calculates SHA256 checksum of a file.
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            raise IOError(f"Failed to calculate SHA256 checksum: {str(e)}")

    def import_file(self, source_id, file_path: str) -> Dict[str, Any]:
        """
        Imports an ICS or Excel file for a given calendar source with versioning.
        Returns a summary dict.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)
        file_sha256 = self.calculate_sha256(file_path)

        # 1. Check if this exact file checksum was already successfully imported for this source
        check_query = """
            SELECT id, version_number
            FROM calendar_source_versions
            WHERE source_id = %s AND file_sha256 = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(check_query, (source_id, file_sha256))
            row = cur.fetchone()
            if row:
                return {
                    "status": "duplicate_noop",
                    "message": "File already imported for this source",
                    "source_id": source_id,
                    "version_id": row[0],
                    "version_number": row[1],
                    "parsed_count": 0,
                    "warnings": []
                }

        # 2. Select parser based on file extension
        _, ext = os.path.splitext(file_name.lower())
        events: List[Dict[str, Any]] = []
        warnings: List[str] = []

        if ext == ".ics":
            importer = IcsImporter()
            events = importer.parse(file_path)
        elif ext == ".xlsx":
            importer = ExcelExamImporter()
            events, warnings = importer.parse(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Must be .ics or .xlsx")

        # 3. Transactional database updates
        try:
            with self.conn.cursor() as cur:
                # Find current max version_number for this source
                cur.execute(
                    "SELECT COALESCE(MAX(version_number), 0) FROM calendar_source_versions WHERE source_id = %s",
                    (source_id,)
                )
                max_ver = cur.fetchone()[0]
                new_ver_num = max_ver + 1

                # Create calendar_source_versions entry
                summary_json = {
                    "parsed_count": len(events),
                    "warnings": warnings,
                }

                version_insert = """
                    INSERT INTO calendar_source_versions (source_id, version_number, file_name, file_sha256, imported_at, parser_version, status, summary_json)
                    VALUES (%s, %s, %s, %s, NOW(), 'v2', 'active', %s::jsonb)
                    RETURNING id
                """
                cur.execute(version_insert, (source_id, new_ver_num, file_name, file_sha256, json.dumps(summary_json)))
                version_id = cur.fetchone()[0]

                cur.execute(
                    """
                    UPDATE calendar_source_versions
                    SET status = 'superseded'
                    WHERE source_id = %s AND id <> %s AND status = 'active'
                    """,
                    (source_id, version_id),
                )

                # Insert events
                event_insert = """
                    INSERT INTO calendar_events (source_id, source_version_id, external_uid, content_hash, title, description, starts_at, ends_at, location, event_type, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
                """
                for ev in events:
                    cur.execute(event_insert, (
                        source_id,
                        version_id,
                        ev["external_uid"],
                        ev["content_hash"],
                        ev["title"],
                        ev["description"],
                        ev["starts_at"],
                        ev["ends_at"],
                        ev["location"],
                        ev["event_type"],
                    ))

                # Update current_version_id in calendar_sources
                cur.execute(
                    "UPDATE calendar_sources SET current_version_id = %s, updated_at = NOW() WHERE id = %s",
                    (version_id, source_id)
                )

                # Commit transaction
                self.conn.commit()

                return {
                    "status": "active",
                    "source_id": source_id,
                    "version_id": version_id,
                    "version_number": new_ver_num,
                    "parsed_count": len(events),
                    "warnings": warnings
                }

        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"Database error during schedule import: {str(e)}")
