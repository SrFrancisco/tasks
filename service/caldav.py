# caldav service

import re
from datetime import datetime, time, timedelta

from consts import (
    CALDAV_CALENDAR_NAME,
    CALDAV_ENABLE_VALARM,
    CALDAV_NOTIFY_TIME,
    CALDAV_SERVER_PASSWORD,
    CALDAV_SERVER_URL,
    CALDAV_SERVER_USERNAME,
    ENABLE_CALDAV,
    PORTUGUESE_LANG,
)

NOTIFY_TAG = "#notify"
NOTIFY_DONE_TAG = "#notify-"
WEEKDAY_NAMES = (
    ("segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo")
    if PORTUGUESE_LANG
    else ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
)
WEEKDAY_INDEX = {name: index for index, name in enumerate(WEEKDAY_NAMES)}
WEEKDAY_PATTERN = re.compile(r"@(\S+)")
TASK_STATE_PATTERN = re.compile(r"^\s*\[[ xw/]\]\s*")
TAG_PATTERN = re.compile(r"#\S+")


def event_summary(line: str) -> str:
    summary = TASK_STATE_PATTERN.sub("", line)
    summary = TAG_PATTERN.sub("", summary)
    summary = WEEKDAY_PATTERN.sub(
        lambda match: ""
        if match.group(1).lower() in WEEKDAY_INDEX
        else match.group(0),
        summary,
    )
    return re.sub(r"\s+", " ", summary).strip()

def _build_event_ical(summary: str, start_at: datetime) -> str:
    from caldav.lib import vcal

    ical = vcal.create_ical(
        objtype="VEVENT",
        dtstart=start_at.date(),
        dtend=start_at.date() + timedelta(days=1),
        summary="task: " + summary,
    )
    if not CALDAV_ENABLE_VALARM:
        return ical

    return ical.replace(
        "END:VEVENT",
        "BEGIN:VALARM\n"
        "ACTION:DISPLAY\n"
        "DESCRIPTION:Reminder\n"
        f"TRIGGER:-PT{CALDAV_NOTIFY_TIME}\n"
        "END:VALARM\n"
        "END:VEVENT",
        1,
    )


def add_to_calendar(events:list[tuple[str, datetime]]):
    assert ENABLE_CALDAV, "This method required caldav to be enabled"
    from caldav.davclient import get_davclient

    if len(events) == 0:
        raise ValueError("List cannot be empty")

    with get_davclient(
        url=CALDAV_SERVER_URL.rstrip("/") + "/",
        username=CALDAV_SERVER_USERNAME,
        password=CALDAV_SERVER_PASSWORD,
    ) as client:
        principal = client.get_principal()
        calendar = principal.calendar(name=CALDAV_CALENDAR_NAME)

        for event in events:
            calendar.save_event(_build_event_ical(event[0], event[1]))
            print("Added event", event)


def resolve_next_due_datetime(line: str, now: datetime | None = None) -> datetime | None:
    now = now or datetime.now()
    for due_tag in WEEKDAY_PATTERN.findall(line):
        weekday_index = WEEKDAY_INDEX.get(due_tag.lower())
        if weekday_index is None:
            continue

        days_until = (weekday_index - now.weekday()) % 7
        if days_until == 0:
            days_until = 7

        due_day = (now + timedelta(days=days_until)).date()
        return datetime.combine(due_day, time.min)
    return None


def extract_notification_events(
    lines: list[str], now: datetime | None = None
) -> tuple[list[tuple[int, str, datetime]], list[str]]:
    pending_events: list[tuple[int, str, datetime]] = []
    skipped_lines: list[str] = []

    for index, line in enumerate(lines):
        if NOTIFY_TAG not in line or NOTIFY_DONE_TAG in line:
            continue
        if not line.lstrip().startswith(("[ ]", "[w]", "[/]")):
            continue

        due_at = resolve_next_due_datetime(line, now=now)
        if due_at is None:
            skipped_lines.append(line.rstrip("\n"))
            continue

        pending_events.append((index, event_summary(line), due_at))

    return pending_events, skipped_lines


def mark_notifications_as_scheduled(
    lines: list[str], scheduled_indexes: list[int]
) -> list[str]:
    updated_lines = list(lines)
    for index in scheduled_indexes:
        updated_lines[index] = updated_lines[index].replace(
            NOTIFY_TAG, NOTIFY_DONE_TAG, 1
        )
    return updated_lines


def process_notification_lines(
    lines: list[str], now: datetime | None = None
) -> list[str]:
    if not ENABLE_CALDAV:
        return lines

    pending_events, skipped_lines = extract_notification_events(lines, now=now)
    if skipped_lines:
        print("Skipping #notify tasks without a weekday due tag:", skipped_lines)
    if not pending_events:
        return lines

    add_to_calendar([(summary, due_at) for _, summary, due_at in pending_events])
    return mark_notifications_as_scheduled(
        lines, [index for index, _, _ in pending_events]
    )
