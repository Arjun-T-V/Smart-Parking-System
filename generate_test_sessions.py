
import os
import sys
import csv
import random
from pathlib import Path
from datetime import datetime, timedelta

# --------------------------------------------------
# PARKEASE: Synthetic Parking Session Generator
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "project_parking.settings",
)

sys.path.insert(0, str(BASE_DIR))

import django
django.setup()

from django.db import transaction
from django.utils import timezone
from parking.models import ParkingFloor, ParkingSlot, ParkingSession


TOTAL_SESSIONS = 1000
RANDOM_SEED = 42

MANIFEST_PATH = BASE_DIR / "synthetic_sessions_manifest.csv"

random.seed(RANDOM_SEED)


def get_ground_floor_slots():
    """Return only slots belonging to the ground floor."""

    slots = list(
        ParkingSlot.objects.filter(
            floor__floor_number=0
        ).select_related("floor")
    )

    # Fallback for projects where the ground floor
    # is named "Ground Floor" but has another number.
    if not slots:
        slots = list(
            ParkingSlot.objects.filter(
                floor__name__icontains="ground"
            ).select_related("floor")
        )

    return slots


def generate_session_times(now):
    """
    Generate a historical parking session.

    Entries are spread across the previous 90 days.
    Durations range from 15 to 240 minutes.
    Every generated session ends before the current time.
    """

    local_now = timezone.localtime(now)
    days_ago = random.randint(1, 90)

    entry_date = (local_now - timedelta(days=days_ago)).date()

    # More entries during typical daytime parking hours.
    entry_hour = random.choices(
        population=list(range(24)),
        weights=[
            1, 1, 1, 1, 1, 2,
            4, 7, 9, 8, 7, 7,
            8, 8, 8, 9, 10, 10,
            8, 6, 4, 3, 2, 1,
        ],
        k=1,
    )[0]

    entry_minute = random.randint(0, 59)

    local_entry = datetime.combine(
        entry_date,
        datetime.min.time(),
    ).replace(
        hour=entry_hour,
        minute=entry_minute,
    )

    entry_time = timezone.make_aware(
        local_entry,
        timezone.get_current_timezone(),
    )

    duration_minutes = random.randint(15, 240)
    exit_time = entry_time + timedelta(minutes=duration_minutes)

    # Ensure the complete session is in the past.
    if exit_time >= now:
        exit_time = now - timedelta(minutes=random.randint(1, 60))
        entry_time = exit_time - timedelta(
            minutes=duration_minutes
        )

    return entry_time, exit_time, duration_minutes


def main():
    print("\nPARKEASE SYNTHETIC DATA GENERATOR")
    print("=" * 42)

    now = timezone.now()
    slots = get_ground_floor_slots()

    if not slots:
        print("ERROR: No ground-floor parking slots were found.")
        print(
            "Check ParkingFloor.floor_number and your "
            "existing ParkingSlot records."
        )
        sys.exit(1)

    print(f"Ground-floor slots found: {len(slots)}")
    print(f"Sessions to generate: {TOTAL_SESSIONS}")
    print("Data type: SYNTHETIC / TEST ONLY")
    print()

    # Use the model's synthetic flag if it already exists.
    # Otherwise, the CSV manifest will identify every record.
    try:
        ParkingSession._meta.get_field("is_synthetic")
        has_synthetic_field = True
    except Exception:
        has_synthetic_field = False

    generated_sessions = []
    manifest_rows = []

    with transaction.atomic():
        for index in range(TOTAL_SESSIONS):
            slot = random.choice(slots)

            entry_time, exit_time, duration = (
                generate_session_times(now)
            )

            session_kwargs = {
                "slot": slot,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "booking": None,
            }

            if has_synthetic_field:
                session_kwargs["is_synthetic"] = True

            session = ParkingSession(**session_kwargs)
            generated_sessions.append(session)

            manifest_rows.append({
                "marker": "SYNTHETIC_TEST_DATA",
                "slot_id": slot.id,
                "floor": slot.floor.name,
                "slot_number": slot.slot_number,
                "entry_time": entry_time.isoformat(),
                "exit_time": exit_time.isoformat(),
                "duration_minutes": round(duration, 2),
            })

        # Insert only new records. Existing sessions are untouched.
        created_sessions = ParkingSession.objects.bulk_create(
            generated_sessions,
            batch_size=200,
        )

        # Associate generated database IDs with the audit manifest.
        for session, row in zip(created_sessions, manifest_rows):
            row["session_id"] = session.pk

    # Append to the manifest so earlier generated IDs are preserved.
    file_exists = (
        MANIFEST_PATH.exists()
        and MANIFEST_PATH.stat().st_size > 0
    )

    fieldnames = [
        "marker",
        "session_id",
        "slot_id",
        "floor",
        "slot_number",
        "entry_time",
        "exit_time",
        "duration_minutes",
    ]

    with MANIFEST_PATH.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(manifest_rows)

    print("SUCCESS: Synthetic sessions created.")
    print(f"Inserted sessions: {len(created_sessions)}")
    print(f"Audit manifest: {MANIFEST_PATH}")
    print(
        "Database field is_synthetic available: "
        f"{has_synthetic_field}"
    )

    if not has_synthetic_field:
        print(
            "\nIMPORTANT: Your current model has no is_synthetic "
            "field. Use the manifest to identify these records "
            "and exclude them from real-data training."
        )

    print("\nDo not interpret synthetic-data accuracy as real-world accuracy.")


if __name__ == "__main__":
    main()
