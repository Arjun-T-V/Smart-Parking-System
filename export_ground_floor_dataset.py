
import os
import csv
import django
from pathlib import Path

from django.utils import timezone

# Configure Django
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "project_parking.settings"
)
django.setup()

from parking.models import ParkingSession

# Output file in the project root
OUTPUT_FILE = Path(__file__).resolve().parent / "ground_floor_parking.csv"

# Fetch completed sessions from the ground floor only
sessions = ParkingSession.objects.filter(
    slot__floor__name__iexact="GROUND FLOOR",
    exit_time__isnull=False,
).select_related("slot", "slot__floor").order_by("entry_time")

columns = [
    "slot_id",
    "entry_time",
    "exit_time",
    "entry_hour",
    "day_of_week",
    "is_weekend",
    "duration_minutes",
    "data_source",
]

exported_rows = []

for session in sessions:
    entry = session.entry_time
    exit_time = session.exit_time

    # Convert timestamps to the configured local timezone
    if timezone.is_aware(entry):
        entry = timezone.localtime(entry)

    if timezone.is_aware(exit_time):
        exit_time = timezone.localtime(exit_time)

    duration = (exit_time - entry).total_seconds() / 60

    # Skip invalid or zero-duration records
    if duration <= 0:
        print(f"Skipping invalid session: {session.pk}")
        continue

    exported_rows.append({
        "slot_id": session.slot.slot_number,
        "entry_time": entry.isoformat(),
        "exit_time": exit_time.isoformat(),
        "entry_hour": entry.hour,
        "day_of_week": entry.weekday(),
        "is_weekend": int(entry.weekday() >= 5),
        "duration_minutes": round(duration, 2),
        "data_source": "real",
    })

with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows(exported_rows)

print("\nGround-floor dataset export complete.")
print("Output file:", OUTPUT_FILE)
print("Completed sessions exported:", len(exported_rows))
print("Active sessions excluded:", ParkingSession.objects.filter(
    slot__floor__name__iexact="GROUND FLOOR",
    exit_time__isnull=True,
).count())
