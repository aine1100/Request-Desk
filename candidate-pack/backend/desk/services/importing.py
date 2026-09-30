import csv
import io
import re
from collections import Counter
from datetime import datetime

from django.utils import timezone

from desk.constants import (
    CSV_COLUMNS,
    KNOWN_ROBOTS,
    MAX_DURATION_SECONDS,
    MIN_DURATION_SECONDS,
    RECORDED_AT_FORMATS,
    RECORDING_ZONE,
)
from desk.errors import DomainError
from desk.models import Episode, Quality
from desk.normalize import normalize_task

EPISODE_ID_RE = re.compile(r"^EP-\d+$")
ISSUE_LIMIT = 100


def import_uploaded(uploaded) -> dict:
    raw = uploaded.read()
    if isinstance(raw, bytes):
        text = raw.decode("utf-8-sig")
    else:
        text = raw
    return import_csv_text(text)


def import_csv_text(text: str) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise DomainError("CSV has no header row.")
    header = [(name or "").strip().lower() for name in reader.fieldnames]
    if header != list(CSV_COLUMNS):
        raise DomainError(
            "CSV header must be: " + ",".join(CSV_COLUMNS)
        )

    seen = {}
    unchanged = 0
    conflicts = 0
    rejected = 0
    reasons = Counter()
    issues = []

    def add_issue(row_number, episode_id, outcome, reason):
        nonlocal conflicts, rejected
        reasons[reason] += 1
        if outcome == "conflict":
            conflicts += 1
        else:
            rejected += 1
        if len(issues) < ISSUE_LIMIT:
            issues.append(
                {
                    "row": row_number,
                    "episode_id": episode_id,
                    "outcome": outcome,
                    "reason": reason,
                }
            )

    for row_number, raw_row in enumerate(reader, start=2):
        if raw_row is None:
            continue
        normalized_row = {
            (key or "").strip().lower(): (value if value is not None else "")
            for key, value in raw_row.items()
        }
        if not any((value or "").strip() for value in normalized_row.values()):
            continue
        parsed, error = _parse_row(normalized_row)
        episode_id = (normalized_row.get("episode_id") or "").strip().upper()
        if error:
            add_issue(row_number, episode_id, "rejected", error)
            continue
        parsed["row"] = row_number
        previous = seen.get(parsed["episode_id"])
        if previous is None:
            seen[parsed["episode_id"]] = parsed
            continue
        if previous["comparable"] == parsed["comparable"]:
            unchanged += 1
        else:
            fields = _differing_fields(previous["comparable"], parsed["comparable"])
            add_issue(
                row_number,
                parsed["episode_id"],
                "conflict",
                f"differs from an earlier row in this file ({fields})",
            )

    existing = _fetch_existing(seen.keys())
    to_create = []
    for episode_id, parsed in seen.items():
        current = existing.get(episode_id)
        if current is None:
            to_create.append(Episode(**parsed["fields"]))
            continue
        if current.comparable() == parsed["comparable"]:
            unchanged += 1
            continue
        fields = _differing_fields(current.comparable(), parsed["comparable"])
        add_issue(
            parsed["row"],
            episode_id,
            "conflict",
            f"differs from the stored episode ({fields})",
        )

    if to_create:
        Episode.objects.bulk_create(to_create, batch_size=1000)

    return {
        "imported": len(to_create),
        "unchanged": unchanged,
        "conflicts": conflicts,
        "rejected": rejected,
        "rejection_reasons": dict(reasons),
        "issues": issues,
        "issues_truncated": (conflicts + rejected) > len(issues),
    }


def _fetch_existing(episode_ids):
    found = {}
    ids = list(episode_ids)
    for start in range(0, len(ids), 1000):
        chunk = ids[start : start + 1000]
        for episode in Episode.objects.filter(episode_id__in=chunk):
            found[episode.episode_id] = episode
    return found


def _parse_row(row):
    episode_id = (row.get("episode_id") or "").strip().upper()
    if not episode_id:
        return None, "missing episode_id"
    if not EPISODE_ID_RE.match(episode_id):
        return None, "invalid episode_id"

    robot_id = (row.get("robot_id") or "").strip().lower()
    if not robot_id:
        return None, "missing robot_id"
    if robot_id not in KNOWN_ROBOTS:
        return None, "unknown robot_id"

    task_name = normalize_task(row.get("task_name") or "")
    if not task_name:
        return None, "missing task_name"

    recorded_at, recorded_error = _parse_recorded_at(row.get("recorded_at") or "")
    if recorded_error:
        return None, recorded_error

    duration, duration_error = _parse_duration(row.get("duration_seconds") or "")
    if duration_error:
        return None, duration_error

    operator_name = (row.get("operator_name") or "").strip()
    if not operator_name:
        return None, "missing operator_name"

    quality = (row.get("quality") or "").strip().lower()
    if not quality:
        return None, "missing quality"
    if quality not in Quality.values:
        return None, "invalid quality"

    fields = {
        "episode_id": episode_id,
        "robot_id": robot_id,
        "task_name": task_name,
        "recorded_at": recorded_at,
        "duration_seconds": duration,
        "operator_name": operator_name,
        "quality": quality,
    }
    return {
        "row": None,
        "episode_id": episode_id,
        "fields": fields,
        "comparable": (
            robot_id,
            task_name,
            recorded_at,
            duration,
            operator_name,
            quality,
        ),
    }, None


def _parse_recorded_at(value):
    value = value.strip()
    if not value:
        return None, "missing recorded_at"
    for fmt in RECORDED_AT_FORMATS:
        try:
            naive = datetime.strptime(value, fmt)
        except ValueError:
            continue
        aware = timezone.make_aware(naive, RECORDING_ZONE)
        return aware, None
    return None, "invalid recorded_at"


def _parse_duration(value):
    value = value.strip()
    if not value:
        return None, "missing duration_seconds"
    try:
        duration = int(value)
    except ValueError:
        return None, "invalid duration_seconds"
    if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
        return None, "duration_seconds out of range"
    return duration, None


def _differing_fields(left, right):
    names = (
        "robot_id",
        "task_name",
        "recorded_at",
        "duration_seconds",
        "operator_name",
        "quality",
    )
    changed = [name for name, a, b in zip(names, left, right) if a != b]
    return ", ".join(changed) or "fields"
