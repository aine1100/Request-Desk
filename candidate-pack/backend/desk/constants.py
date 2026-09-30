from zoneinfo import ZoneInfo

KNOWN_ROBOTS = frozenset({"arm-01", "arm-02", "arm-03", "mobile-01", "humanoid-01"})
MIN_DURATION_SECONDS = 1
# Sample clips are under two minutes. 999999 in the export is corrupt, not a real take.
MAX_DURATION_SECONDS = 3600
RECORDED_AT_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d",
)
# CSV timestamps have no offset. Treat them as Kigali local time.
RECORDING_ZONE = ZoneInfo("Africa/Kigali")
CSV_COLUMNS = (
    "episode_id",
    "robot_id",
    "task_name",
    "recorded_at",
    "duration_seconds",
    "operator_name",
    "quality",
)
