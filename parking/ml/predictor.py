
from datetime import timedelta
from pathlib import Path

import joblib
import pandas as pd
from django.utils import timezone

from parking.models import IoTSensor, ParkingSession, ParkingSlot


MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "ml_model"
    / "parking_duration_model.joblib"
)

REQUIRED_TRAINING_RECORDS = 30
REQUIRED_TRAINING_TYPE = "genuine_completed_parking_sessions"

_model_bundle = None
_model_checked = False


def load_model():
    """
    Load only a validated model trained on genuine completed sessions.

    Synthetic or legacy models are rejected.
    """
    global _model_bundle, _model_checked

    if _model_checked:
        return _model_bundle

    _model_checked = True

    if not MODEL_PATH.exists():
        return None

    try:
        bundle = joblib.load(MODEL_PATH)

        if not isinstance(bundle, dict):
            return None

        if bundle.get("training_data") != REQUIRED_TRAINING_TYPE:
            return None

        if bundle.get("training_records", 0) < REQUIRED_TRAINING_RECORDS:
            return None

        if "model" not in bundle or "features" not in bundle:
            return None

        required_features = {
            "entry_hour",
            "day_of_week",
            "floor_number",
            "is_weekend",
        }

        if set(bundle["features"]) != required_features:
            return None

        _model_bundle = bundle
        return _model_bundle

    except Exception:
        # An unavailable or unreadable model must not break the page.
        return None


def predict_remaining_time(entry_time, floor_number):
    """
    Predict remaining duration using a validated genuine-data model.

    Returns None when a trustworthy model is unavailable.
    """
    bundle = load_model()

    if bundle is None:
        return None

    now = timezone.now()

    if timezone.is_naive(entry_time):
        entry_time = timezone.make_aware(
            entry_time,
            timezone.get_current_timezone(),
        )

    entry_local = timezone.localtime(entry_time)

    elapsed_minutes = max(
        0,
        (now - entry_time).total_seconds() / 60,
    )

    sample = pd.DataFrame([{
        "entry_hour": entry_local.hour,
        "day_of_week": entry_local.weekday(),
        "floor_number": floor_number,
        "is_weekend": int(entry_local.weekday() >= 5),
    }])[bundle["features"]]

    predicted_total = max(
        1.0,
        float(bundle["model"].predict(sample)[0]),
    )

    remaining_minutes = max(
        0,
        round(predicted_total - elapsed_minutes),
    )

    predicted_release_time = (
        entry_time + timedelta(minutes=predicted_total)
    )

    return {
        "predicted_total_minutes": round(predicted_total),
        "elapsed_minutes": round(elapsed_minutes),
        "remaining_minutes": remaining_minutes,
        "predicted_release_time": predicted_release_time,
        "training_records": bundle["training_records"],
        "test_mae_minutes": bundle.get("test_mae_minutes"),
        "experimental": False,
    }


def predict_ground_floor_slots():
    """
    Report ground-floor sensor status and genuine-data ML estimates.

    Booking end times are not used as ML predictions.
    UNKNOWN sensor state is never treated as AVAILABLE.
    """
    results = []

    slots = (
        ParkingSlot.objects
        .filter(floor__floor_number=0)
        .select_related("floor")
        .order_by("slot_number")
    )

    for slot in slots:
        sensor = IoTSensor.objects.filter(slot=slot).first()

        active_session = (
            ParkingSession.objects
            .filter(slot=slot, exit_time__isnull=True)
            .order_by("-entry_time")
            .first()
        )

        sensor_state = sensor.state if sensor else "UNKNOWN"

        item = {
            "slot_id": slot.id,
            "slot_number": slot.slot_number,
            "sensor_state": sensor_state,
            "status": "unknown",
            "estimated_release_time": None,
            "remaining_minutes": None,
            "estimate_source": None,
            "experimental": False,
        }

        if sensor_state == IoTSensor.State.CLEAR:
            item["status"] = "available"
            item["estimate_source"] = "live_sensor"
            results.append(item)
            continue

        if sensor_state != IoTSensor.State.DETECTED:
            item["estimate_source"] = "sensor_data_unavailable"
            results.append(item)
            continue

        item["status"] = "occupied"

        if active_session is None:
            item["estimate_source"] = "no_active_session"
            results.append(item)
            continue

        prediction = predict_remaining_time(
            active_session.entry_time,
            slot.floor.floor_number,
        )

        if prediction is None:
            item["estimate_source"] = "ml_model_unavailable"
            results.append(item)
            continue

        item["estimated_release_time"] = (
            prediction["predicted_release_time"]
        )
        item["remaining_minutes"] = prediction["remaining_minutes"]
        item["estimate_source"] = "genuine_ml"
        item["experimental"] = False

        results.append(item)

    return results


def predict_next_available_slot():
    """
    Find the earliest estimated ground-floor slot availability.

    Priority:
    1. A live CLEAR sensor reading.
    2. Genuine-data ML estimates for DETECTED slots with active sessions.
    3. Unavailable estimate when neither source can establish availability.

    Confirmed booking end times are deliberately not used.
    """
    now = timezone.now()

    slots = list(
        ParkingSlot.objects
        .filter(floor__floor_number=0)
        .select_related("floor")
        .order_by("slot_number")
    )

    if not slots:
        return {
            "status": "no_slots",
            "message": "No ground-floor parking slots are configured.",
            "estimated_release_time": None,
            "remaining_minutes": None,
            "remaining_hours": None,
            "remaining_remainder_minutes": None,
            "slot_number": None,
            "source": None,
        }

    slot_ids = [slot.id for slot in slots]

    sensors = {
        sensor.slot_id: sensor
        for sensor in IoTSensor.objects.filter(slot_id__in=slot_ids)
    }

    # A confirmed clear reading is stronger than an estimate.
    clear_slots = [
        slot for slot in slots
        if (
            slot.id in sensors
            and sensors[slot.id].state == IoTSensor.State.CLEAR
        )
    ]

    if clear_slots:
        slot = clear_slots[0]

        return {
            "status": "available_now",
            "message": "A live sensor confirms that this slot is clear.",
            "estimated_release_time": now,
            "remaining_minutes": 0,
            "remaining_hours": 0,
            "remaining_remainder_minutes": 0,
            "slot_number": slot.slot_number,
            "source": "live_sensor",
        }

    # Do not use booking schedules as a substitute for ML.
    candidates = []

    for slot in slots:
        sensor = sensors.get(slot.id)

        if sensor is None or sensor.state != IoTSensor.State.DETECTED:
            continue

        active_session = (
            ParkingSession.objects
            .filter(slot=slot, exit_time__isnull=True)
            .order_by("-entry_time")
            .first()
        )

        if active_session is None:
            continue

        prediction = predict_remaining_time(
            active_session.entry_time,
            slot.floor.floor_number,
        )

        if prediction is None:
            continue

        candidates.append({
            "slot": slot,
            **prediction,
        })

    if candidates:
        # Choose the smallest predicted remaining duration.
        best = min(
            candidates,
            key=lambda candidate: candidate["remaining_minutes"],
        )

        remaining_minutes = best["remaining_minutes"]
        hours, minutes = divmod(remaining_minutes, 60)

        return {
            "status": "ml_estimate",
            "message": (
                "Estimated using a model trained on genuine completed "
                "parking sessions. Actual departure time may differ."
            ),
            "estimated_release_time": best["predicted_release_time"],
            "remaining_minutes": remaining_minutes,
            "remaining_hours": hours,
            "remaining_remainder_minutes": minutes,
            "slot_number": best["slot"].slot_number,
            "source": "genuine_ml",
        }

    return {
        "status": "unknown",
        "message": (
            "ML prediction is unavailable because a validated model "
            "trained on enough genuine completed sessions is not "
            "available, or no occupied slot has a usable active session. "
            "Collect genuine entry and exit records to enable predictions."
        ),
        "estimated_release_time": None,
        "remaining_minutes": None,
        "remaining_hours": None,
        "remaining_remainder_minutes": None,
        "slot_number": None,
        "source": None,
    }
