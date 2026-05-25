import hashlib
from datetime import datetime, timedelta, timezone

VIETNAM_TZ = timezone(timedelta(hours=7))

class IcsImporter:
    def __init__(self):
        pass

    def parse_date(self, dt_str: str) -> datetime:
        """
        Parses ICS date/time strings into a timezone-aware datetime.
        Handles:
          - YYYYMMDDTHHMMSSZ (UTC)
          - YYYYMMDDTHHMMSS (local naive, assumed to be Asia/Ho_Chi_Minh)
          - YYYYMMDD (date only, assumed 00:00:00 local time)
        """
        if not dt_str:
            return None

        # Clean parameter prefixes/suffixes (e.g., DTSTART;VALUE=DATE-TIME:20260113T070000 -> 20260113T070000)
        clean_str = dt_str.split(":")[-1].strip()

        # Check for UTC suffix
        is_utc = clean_str.endswith("Z")
        if is_utc:
            clean_str = clean_str[:-1]

        # Try parsing YYYYMMDDTHHMMSS
        try:
            dt = datetime.strptime(clean_str, "%Y%m%dT%H%M%S")
            if is_utc:
                return dt.replace(tzinfo=timezone.utc).astimezone(VIETNAM_TZ)
            else:
                return dt.replace(tzinfo=VIETNAM_TZ)
        except ValueError:
            pass

        # Try parsing YYYYMMDD (date only)
        try:
            dt = datetime.strptime(clean_str, "%Y%m%d")
            return dt.replace(tzinfo=VIETNAM_TZ)
        except ValueError:
            pass

        return None

    def parse(self, file_path: str) -> list:
        """
        Reads and parses an ICS file, returning a list of event dictionaries.
        """
        events = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content_lines = f.read().splitlines()
        except Exception as e:
            raise IOError(f"Failed to read ICS file: {str(e)}")

        # Unfold lines according to RFC 5545
        unfolded_lines = []
        for line in content_lines:
            if line.startswith(" ") or line.startswith("\t"):
                if unfolded_lines:
                    unfolded_lines[-1] += line.strip()
            else:
                unfolded_lines.append(line)

        in_event = False
        curr_event = {}

        for line in unfolded_lines:
            if not line.strip():
                continue
            if line == "BEGIN:VEVENT":
                in_event = True
                curr_event = {}
            elif line == "END:VEVENT":
                in_event = False
                if "DTSTART" in curr_event and "SUMMARY" in curr_event:
                    starts_at = self.parse_date(curr_event["DTSTART"])
                    if starts_at:
                        ends_at = self.parse_date(curr_event.get("DTEND"))
                        if not ends_at:
                            ends_at = starts_at + timedelta(minutes=90)

                        title = curr_event["SUMMARY"].strip()
                        # Clean parameters in summary (e.g. SUMMARY;LANGUAGE=en-us:Title -> Title)
                        if ":" in curr_event["SUMMARY"] and ";" in curr_event["SUMMARY"].split(":", 1)[0]:
                            title = curr_event["SUMMARY"].split(":", 1)[1].strip()

                        description = curr_event.get("DESCRIPTION", "").strip()
                        location = curr_event.get("LOCATION", "").strip()
                        external_uid = curr_event.get("UID", "").strip()

                        # Contract values: class, exam, manual, holiday, other, legacy.
                        event_type = "class"
                        if (
                            title.upper().startswith("[THI]")
                            or "LICH THI" in description.upper()
                            or "LICHTHI" in external_uid.upper()
                        ):
                            event_type = "exam"

                        # Compute content hash
                        starts_at_str = starts_at.isoformat()
                        ends_at_str = ends_at.isoformat()
                        hash_payload = f"{title}|{description}|{starts_at_str}|{ends_at_str}|{location}|{event_type}"
                        content_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

                        events.append({
                            "external_uid": external_uid if external_uid else None,
                            "content_hash": content_hash,
                            "title": title,
                            "description": description if description else None,
                            "starts_at": starts_at,
                            "ends_at": ends_at,
                            "location": location if location else None,
                            "event_type": event_type,
                            "status": "active"
                        })
            elif in_event:
                if ":" in line:
                    key_part, val_part = line.split(":", 1)
                    # Normalize key name by stripping parameters (e.g. SUMMARY;LANGUAGE=en-us -> SUMMARY)
                    key_name = key_part.split(";")[0].strip()
                    curr_event[key_name] = val_part.strip()

        return events
