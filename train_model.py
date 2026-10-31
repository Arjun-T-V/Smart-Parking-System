
import os
import sys
import csv
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

# --------------------------------------------------
# PARKEASE: Train using genuine completed sessions
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "project_parking.settings",
)

import django
django.setup()

from django.utils import timezone
from parking.models import ParkingSession

UNVERIFIED_PATH = BASE_DIR / "unverified_sessions.csv"
MANIFEST_PATH = BASE_DIR / "synthetic_sessions_manifest.csv"
OUTPUT_DIR = BASE_DIR / "parking" / "ml_model"
MODEL_PATH = OUTPUT_DIR / "parking_duration_model.joblib"

FEATURES = [
    "entry_hour",
    "day_of_week",
    "floor_number",
    "is_weekend",
]

MIN_RECORDS = 30


def load_synthetic_session_ids():
    """Read synthetic session IDs from the audit manifest."""

    synthetic_ids = set()

    if not MANIFEST_PATH.exists():
        return synthetic_ids

    with MANIFEST_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            session_id = row.get("session_id")

            if session_id:
                synthetic_ids.add(int(session_id))

    return synthetic_ids



def load_unverified_session_ids():
    """Return session IDs that must not be used for training."""

    unverified_ids = set()

    if not UNVERIFIED_PATH.exists():
        return unverified_ids

    with UNVERIFIED_PATH.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as csvfile:
        # Skip any blank lines before or between CSV records.
        reader = csv.DictReader(
            line for line in csvfile if line.strip()
        )

        for row in reader:
            session_id = row.get("session_id")

            if session_id and session_id.strip().isdigit():
                unverified_ids.add(int(session_id.strip()))

    return unverified_ids


def main():
    
    print("\nPARKEASE REAL-DATA TRAINING")
    print("=" * 42)

    synthetic_ids = load_synthetic_session_ids()
    unverified_ids = load_unverified_session_ids()

    excluded_ids = synthetic_ids | unverified_ids

    print("Synthetic IDs:", len(synthetic_ids))
    print("Unverified session IDs:", sorted(unverified_ids))
    

    print("Synthetic IDs in manifest:", len(synthetic_ids))

    sessions = ParkingSession.objects.filter(
        exit_time__isnull=False
    ).select_related(
        "slot",
        "slot__floor",
    ).order_by("entry_time")

    rows = []
    excluded_synthetic = 0

    excluded_test_flag = 0
    excluded_unverified = 0

    
    for session in sessions.iterator():

        if session.is_test_data:
            excluded_test_flag += 1
            continue

        if session.pk in synthetic_ids:
            excluded_synthetic += 1
            continue

        if session.pk in unverified_ids:
            excluded_unverified += 1
            continue

        if not session.entry_time or not session.exit_time:
            continue

        if session.exit_time <= session.entry_time:
            continue

        entry_local = timezone.localtime(session.entry_time)

        duration_minutes = (
            session.exit_time - session.entry_time
        ).total_seconds() / 60

        if duration_minutes <= 0:
            continue

        rows.append({
            "entry_hour": entry_local.hour,
            "day_of_week": entry_local.weekday(),
            "floor_number": session.slot.floor.floor_number,
            "is_weekend": int(entry_local.weekday() >= 5),
            "duration_minutes": duration_minutes,
        })

    print("Test-flagged sessions excluded:", excluded_test_flag)
    print("Unverified sessions excluded:", excluded_unverified)

    data = pd.DataFrame(rows)

    print("Synthetic completed sessions excluded:", excluded_synthetic)
    print("Genuine completed sessions available:", len(data))

    if data.empty or len(data) < MIN_RECORDS:
        print("\nTRAINING STOPPED.")
        print(
            f"At least {MIN_RECORDS} genuine completed sessions "
            "are required."
        )
        print(
            "Synthetic records were not used to train the model."
        )
        return

    data = data.dropna(subset=FEATURES + ["duration_minutes"])
    data = data[data["duration_minutes"] > 0]

    if len(data) < MIN_RECORDS:
        print("\nTRAINING STOPPED after data validation.")
        print(f"Valid genuine records: {len(data)}")
        return

    X = data[FEATURES]
    y = data["duration_minutes"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    model = RandomForestRegressor(
        n_estimators=200,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model_data = {
        "model": model,
        "features": FEATURES,
        "training_data": "genuine_completed_parking_sessions",
        "training_records": len(data),
        "test_mae_minutes": float(mae),
    }

    joblib.dump(model_data, MODEL_PATH)

    print("\nMODEL TRAINED SUCCESSFULLY")
    print("Training records:", len(X_train))
    print("Test records:", len(X_test))
    print(f"Test MAE: {mae:.2f} minutes")
    print("Model saved to:", MODEL_PATH)


if __name__ == "__main__":
    main()
