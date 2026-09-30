from datetime import datetime, timedelta

from django.db import connection
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

from desk.errors import DomainError
from desk.models import DatasetRequest, Episode, RequestStatus, StatusEvent


def analytics_for_range(start_value, end_value):
    start, end = _parse_range(start_value, end_value)
    return {
        "start": start_value,
        "end": end_value,
        "episodes_per_day_per_robot": _episodes_per_day(start, end),
        "requests_by_status": _requests_by_status(start, end),
        "median_seconds_submitted_to_delivered": _median_delivery_seconds(start, end),
        "top_tasks_by_good_episodes": _top_tasks(start, end),
    }


def _parse_range(start_value, end_value):
    start_date = parse_date(start_value or "")
    end_date = parse_date(end_value or "")
    if start_date is None or end_date is None:
        raise DomainError("start and end are required dates (YYYY-MM-DD).")
    if end_date < start_date:
        raise DomainError("end is before start.")
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), zone)
    end = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time()), zone
    )
    return start, end


def _episodes_per_day(start, end):
    rows = (
        Episode.objects.filter(recorded_at__gte=start, recorded_at__lt=end)
        .annotate(day=TruncDate("recorded_at"))
        .values("day", "robot_id")
        .annotate(count=Count("id"))
        .order_by("day", "robot_id")
    )
    return [
        {"date": row["day"].isoformat(), "robot_id": row["robot_id"], "count": row["count"]}
        for row in rows
    ]


def _submitted_request_ids(start, end):
    return StatusEvent.objects.filter(
        to_status=RequestStatus.SUBMITTED,
        created_at__gte=start,
        created_at__lt=end,
    ).values("request_id")


def _requests_by_status(start, end):
    counts = {status: 0 for status in RequestStatus.values}
    rows = (
        DatasetRequest.objects.filter(id__in=_submitted_request_ids(start, end))
        .values("status")
        .annotate(count=Count("id"))
    )
    for row in rows:
        counts[row["status"]] = row["count"]
    return counts


def _top_tasks(start, end):
    rows = (
        Episode.objects.filter(
            quality="good", recorded_at__gte=start, recorded_at__lt=end
        )
        .values("task_name")
        .annotate(count=Count("id"))
        .order_by("-count", "task_name")[:5]
    )
    return [{"task_name": row["task_name"], "count": row["count"]} for row in rows]


def _median_delivery_seconds(start, end):
    """Median seconds from the first submitted event to the first later delivered event.

    Computed in SQL. The request set is small relative to episodes, so this stays
    cheap at episode scale; the episode aggregations above use indexes on
    recorded_at and quality.
    """
    if connection.vendor == "postgresql":
        delta = "EXTRACT(EPOCH FROM (d.created_at - s.created_at))"
    else:
        delta = "(julianday(d.created_at) - julianday(s.created_at)) * 86400.0"
    sql = f"""
        WITH spans AS (
            SELECT {delta} AS seconds
            FROM status_events s
            JOIN status_events d
              ON d.request_id = s.request_id
             AND d.to_status = 'delivered'
            WHERE s.to_status = 'submitted'
              AND s.created_at >= %s
              AND s.created_at < %s
              AND s.created_at = (
                    SELECT MIN(s2.created_at) FROM status_events s2
                    WHERE s2.request_id = s.request_id AND s2.to_status = 'submitted'
              )
              AND d.created_at = (
                    SELECT MIN(d2.created_at) FROM status_events d2
                    WHERE d2.request_id = s.request_id
                      AND d2.to_status = 'delivered'
                      AND d2.created_at >= s.created_at
              )
        ),
        ranked AS (
            SELECT seconds,
                   ROW_NUMBER() OVER (ORDER BY seconds) AS rn,
                   COUNT(*) OVER () AS cnt
            FROM spans
        )
        SELECT AVG(seconds) FROM ranked
        WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [start, end])
        row = cursor.fetchone()
    if not row or row[0] is None:
        return None
    return round(float(row[0]), 3)
