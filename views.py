from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from .models import ParkingFloor
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from .models import ParkingFloor, ParkingSlot, Booking
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from .models import Vehicle
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from parking.ml.predictor import (
    predict_remaining_time,
    predict_next_available_slot,
)
from .models import Payment
from .payment_utils import calculate_parking_fee
from decimal import Decimal
from parking.ml.predictor import predict_next_available_slot

import json
import hmac

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import IoTSensor

def home(request):
    return render(request, 'parking/home.html')


def login_view(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect('dashboard')

        return render(request, 'parking/login.html', {
            'error': 'Invalid username or password'
        })

    return render(request, 'parking/login.html')


def register_view(request):

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')

    else:
        form = RegisterForm()

    return render(request, 'parking/register.html', {
        'form': form
    })






@login_required
def parking_slots(request):
    from parking.ml.predictor import (
        predict_ground_floor_slots,
        predict_next_available_slot,
    )

    floors = ParkingFloor.objects.prefetch_related(
        'slots__iot_sensor',
        'slots__parking_sessions'
    ).all()

    start_value = request.GET.get('start_time', '')
    end_value = request.GET.get('end_time', '')

    available_slot_ids = None
    conflicting_bookings = {}
    error = None

    # Validate the requested parking time.
    if start_value or end_value:
        if not start_value or not end_value:
            error = 'Enter both arrival and departure times.'

        else:
            try:
                start_time = datetime.fromisoformat(start_value)
                end_time = datetime.fromisoformat(end_value)

                if timezone.is_naive(start_time):
                    start_time = timezone.make_aware(start_time)

                if timezone.is_naive(end_time):
                    end_time = timezone.make_aware(end_time)

                now = timezone.now()

                if start_time <= now:
                    error = 'Choose a future arrival time.'

                elif end_time <= start_time:
                    error = 'Departure time must be after arrival time.'

                else:
                    # Find confirmed bookings overlapping the requested period.
                    overlapping_bookings = Booking.objects.filter(
                        status=Booking.Status.CONFIRMED,
                        start_time__lt=end_time,
                        end_time__gt=start_time,
                    ).select_related(
                        'slot',
                        'slot__floor',
                    ).order_by('end_time')

                    for booking in overlapping_bookings:
                        conflicting_bookings.setdefault(
                            booking.slot_id,
                            booking,
                        )

                    # A slot cannot be booked if it has an overlapping
                    # confirmed booking or is under maintenance.
                    overlapping_slot_ids = set(
                        overlapping_bookings.values_list(
                            'slot_id',
                            flat=True,
                        )
                    )

                    available_slot_ids = set(
                        ParkingSlot.objects.exclude(
                            status=ParkingSlot.Status.MAINTENANCE
                        ).exclude(
                            id__in=overlapping_slot_ids
                        ).values_list(
                            'id',
                            flat=True,
                        )
                    )

            except (ValueError, TypeError):
                error = 'Enter valid arrival and departure times.'

    # Get ground-floor prediction information.
    try:
        ground_floor_predictions = predict_ground_floor_slots()
    except (OSError, ValueError, KeyError, TypeError):
        ground_floor_predictions = []

    predictions_by_slot_id = {
        prediction['slot_id']: prediction
        for prediction in ground_floor_predictions
    }

    # Attach the current sensor status to every slot.
    for floor in floors:
        for slot in floor.slots.all():
            slot.ml_prediction = None
            slot.conflicting_booking = conflicting_bookings.get(slot.id)

            sensor = getattr(slot, 'iot_sensor', None)

            if floor.floor_number == 0:
                slot.ml_prediction = predictions_by_slot_id.get(slot.id)

                if sensor is None or sensor.state == IoTSensor.State.UNKNOWN:
                    slot.live_status = 'UNKNOWN'

                elif sensor.state == IoTSensor.State.DETECTED:
                    slot.live_status = 'OCCUPIED'

                elif sensor.state == IoTSensor.State.CLEAR:
                    slot.live_status = 'AVAILABLE'

                else:
                    slot.live_status = 'UNKNOWN'

            else:
                slot.live_status = slot.status

    # Calculate the unified next-slot availability estimate.
    try:
        next_availability = predict_next_available_slot()

    except (OSError, ValueError, KeyError, TypeError):
        next_availability = {
            'status': 'unknown',
            'message': 'Unable to calculate availability right now.',
            'estimated_release_time': None,
            'remaining_minutes': None,
            'source': None,
        }
    
    return render(
        request,
        'parking/parking_slots.html',
        {
            'floors': floors,
            'start_time': start_value,
            'end_time': end_value,
            'available_slot_ids': available_slot_ids,
            'conflicting_bookings': conflicting_bookings,
            'next_availability': next_availability,
            'error': error,
        },
    )




@login_required
def dashboard(request):
    return render(request, 'parking/dashboard.html')


def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(
        user=request.user
    ).select_related('slot', 'slot__floor')

    return render(
        request,
        'parking/my_bookings.html',
        {'bookings': bookings}
    )





@login_required
def book_slot(request):
    error = None

    selected_slot_id = request.GET.get('slot', '')
    start_value = request.GET.get('start_time', '')
    end_value = request.GET.get('end_time', '')
    selected_vehicle_id = ''

    if request.method == 'POST':
        selected_slot_id = request.POST.get('slot', '')
        start_value = request.POST.get('start_time', '')
        end_value = request.POST.get('end_time', '')
        selected_vehicle_id = request.POST.get('vehicle_id', '')

        try:
            if not selected_slot_id or not selected_vehicle_id:
                raise ValueError

            start_time = datetime.fromisoformat(start_value)
            end_time = datetime.fromisoformat(end_value)

            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time)

            if timezone.is_naive(end_time):
                end_time = timezone.make_aware(end_time)

            vehicle = Vehicle.objects.get(
                pk=selected_vehicle_id,
                user=request.user
            )

            if start_time <= timezone.now():
                error = 'Start time must be in the future.'

            elif end_time <= start_time:
                error = 'End time must be after start time.'

            else:
                parking_fee = calculate_parking_fee(
                    start_time,
                    end_time
                )

                with transaction.atomic():
                    slot = ParkingSlot.objects.select_for_update().get(
                        pk=selected_slot_id,
                        status=ParkingSlot.Status.AVAILABLE
                    )

                    overlapping = Booking.objects.filter(
                        slot=slot,
                        status=Booking.Status.CONFIRMED,
                        start_time__lt=end_time,
                        end_time__gt=start_time
                    ).exists()

                    if overlapping:
                        error = (
                            'This slot is already booked for that time. '
                            'Please choose another slot or time.'
                        )
                    else:
                        booking = Booking.objects.create(
                            user=request.user,
                            slot=slot,
                            vehicle_number=vehicle.vehicle_number,
                            start_time=start_time,
                            end_time=end_time,
                            status=Booking.Status.PENDING
                        )

                        Payment.objects.create(
                            booking=booking,
                            parking_fee=parking_fee,
                            overtime_fine=Decimal('0.00'),
                            total_amount=parking_fee,
                            status=Payment.Status.PENDING,
                            method=Payment.Method.DEMO
                        )

                if not error:
                    messages.success(
                        request,
                        'Booking created. Complete your demo payment next.'
                    )
                    return redirect(
                        'payment_checkout',
                        booking_id=booking.pk
                    )

        except (ValueError, TypeError):
            error = 'Please enter valid booking details.'

        except (Vehicle.DoesNotExist, ParkingSlot.DoesNotExist):
            error = (
                'The selected vehicle or parking slot is invalid. '
                'Please select again.'
            )

    slots = ParkingSlot.objects.filter(
        status=ParkingSlot.Status.AVAILABLE
    ).select_related('floor').order_by(
        'floor__floor_number', 'slot_number'
    )

    vehicles = Vehicle.objects.filter(
        user=request.user
    ).order_by('vehicle_number')

    return render(request, 'parking/book_slot.html', {
        'slots': slots,
        'vehicles': vehicles,
        'selected_slot_id': str(selected_slot_id),
        'selected_vehicle_id': str(selected_vehicle_id),
        'start_time': start_value,
        'end_time': end_value,
        'error': error,
    })





@login_required
@require_POST
def cancel_booking(request, booking_id):
    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
            user=request.user
        )

        if booking.status == Booking.Status.CONFIRMED:
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=['status'])

            messages.success(
                request,
                'Your booking has been cancelled.'
            )
        else:
            messages.error(
                request,
                'This booking is no longer active.'
            )

    return redirect('my_bookings')


@login_required
def my_vehicles(request):
    error = None
    vehicle_number = ''

    if request.method == 'POST':
        vehicle_number = request.POST.get(
            'vehicle_number', ''
        ).strip().upper()

        vehicle_type = request.POST.get('vehicle_type', '')

        valid_types = {
            choice[0] for choice in Vehicle._meta
            .get_field('vehicle_type').choices
        }

        if not vehicle_number or len(vehicle_number) > 20:
            error = 'Enter a valid vehicle registration number.'

        elif vehicle_type not in valid_types:
            error = 'Select a valid vehicle type.'

        elif Vehicle.objects.filter(
            user=request.user,
            vehicle_number__iexact=vehicle_number
        ).exists():
            error = 'This vehicle is already registered to your account.'

        else:
            Vehicle.objects.create(
                user=request.user,
                vehicle_number=vehicle_number,
                vehicle_type=vehicle_type
            )

            messages.success(request, 'Vehicle registered successfully.')
            return redirect('my_vehicles')

    vehicles = Vehicle.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'parking/my_vehicles.html', {
        'vehicles': vehicles,
        'error': error,
        'vehicle_number': vehicle_number,
    })


@user_passes_test(lambda user: user.is_authenticated and user.is_staff)
def admin_dashboard(request):
    context = {
        'total_users': User.objects.count(),
        'total_floors': ParkingFloor.objects.count(),
        'total_slots': ParkingSlot.objects.count(),

        'available_slots': ParkingSlot.objects.filter(
            status=ParkingSlot.Status.AVAILABLE
        ).count(),

        'occupied_slots': ParkingSlot.objects.filter(
            status=ParkingSlot.Status.OCCUPIED
        ).count(),

        'total_vehicles': Vehicle.objects.count(),

        'active_bookings': Booking.objects.filter(
            status=Booking.Status.CONFIRMED
        ).count(),
    }

    return render(
        request,
        'parking/admin_dashboard.html',
        context
    )

@user_passes_test(
    lambda user: user.is_authenticated and user.is_staff
)
def admin_bookings(request):
    search = request.GET.get('search', '').strip()

    bookings = Booking.objects.select_related(
        'user', 'slot', 'slot__floor'
    ).order_by('-created_at')

    if search:
        bookings = bookings.filter(
            Q(user__username__icontains=search)
            | Q(vehicle_number__icontains=search)
        )

    return render(
        request,
        'parking/admin_bookings.html',
        {
            'bookings': bookings,
            'search': search,
        }
    )


@user_passes_test(
    lambda user: user.is_authenticated and user.is_staff
)
@require_POST
def admin_cancel_booking(request, booking_id):
    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id
        )

        if booking.status == Booking.Status.CONFIRMED:
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=['status'])

            messages.success(
                request,
                f'Booking #{booking.id} cancelled successfully.'
            )
        else:
            messages.error(
                request,
                'This booking is not currently confirmed.'
            )

    return redirect('admin_bookings')


@user_passes_test(
    lambda user: user.is_authenticated and user.is_staff
)
def occupancy_report(request):

    total_slots = ParkingSlot.objects.count()

    available_slots = ParkingSlot.objects.filter(
        status=ParkingSlot.Status.AVAILABLE
    ).count()

    occupied_slots = ParkingSlot.objects.filter(
        status=ParkingSlot.Status.OCCUPIED
    ).count()

    reserved_slots = ParkingSlot.objects.filter(
        status=ParkingSlot.Status.RESERVED
    ).count()

    maintenance_slots = ParkingSlot.objects.filter(
        status=ParkingSlot.Status.MAINTENANCE
    ).count()

    occupancy_percentage = (
        round(occupied_slots / total_slots * 100, 2)
        if total_slots else 0
    )

    floor_reports = []

    floors = ParkingFloor.objects.prefetch_related('slots').all()

    for floor in floors:
        slots = floor.slots.all()

        floor_total = slots.count()

        floor_available = slots.filter(
            status=ParkingSlot.Status.AVAILABLE
        ).count()

        floor_occupied = slots.filter(
            status=ParkingSlot.Status.OCCUPIED
        ).count()

        floor_reserved = slots.filter(
            status=ParkingSlot.Status.RESERVED
        ).count()

        floor_maintenance = slots.filter(
            status=ParkingSlot.Status.MAINTENANCE
        ).count()

        floor_percentage = (
            round(floor_occupied / floor_total * 100, 2)
            if floor_total else 0
        )

        floor_reports.append({
            'name': floor.name,
            'total_slots': floor_total,
            'available_slots': floor_available,
            'occupied_slots': floor_occupied,
            'reserved_slots': floor_reserved,
            'maintenance_slots': floor_maintenance,
            'occupancy_percentage': floor_percentage,
        })

    context = {
        'total_slots': total_slots,
        'available_slots': available_slots,
        'occupied_slots': occupied_slots,
        'reserved_slots': reserved_slots,
        'maintenance_slots': maintenance_slots,
        'occupancy_percentage': occupancy_percentage,
        'floor_reports': floor_reports,
    }

    return render(
        request,
        'parking/occupancy_report.html',
        context
    )





@csrf_exempt
@require_POST
def iot_sensor_update(request):
    import json
    import hmac

    from django.conf import settings
    from django.db import transaction
    from django.http import JsonResponse
    from django.utils import timezone

    from .models import Booking, IoTSensor, ParkingSession

    # Authenticate the IoT device.
    expected_token = settings.IOT_DEVICE_TOKEN
    auth_header = request.headers.get("Authorization", "")
    provided_token = auth_header.removeprefix("Bearer ").strip()

    if not auth_header.startswith("Bearer ") or not hmac.compare_digest(
        provided_token, expected_token
    ):
        return JsonResponse({"error": "Invalid device token"}, status=401)

    # Validate request JSON.
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "JSON object required"}, status=400)

    device_id = data.get("device_id")
    state = data.get("state")
    test_mode = data.get("test_mode", False)

    if not isinstance(device_id, str) or not device_id.strip():
        return JsonResponse({"error": "device_id is required"}, status=400)

    if state not in (
        IoTSensor.State.DETECTED,
        IoTSensor.State.CLEAR,
    ):
        return JsonResponse(
            {"error": "State must be DETECTED or CLEAR"},
            status=400,
        )

    if not isinstance(test_mode, bool):
        return JsonResponse(
            {"error": "test_mode must be true or false"},
            status=400,
        )

    try:
        with transaction.atomic():
            sensor = (
                IoTSensor.objects.select_for_update()
                .select_related("slot")
                .get(device_id=device_id.strip())
            )

            now = timezone.now()

            active_session = (
                ParkingSession.objects.select_for_update()
                .filter(slot=sensor.slot, exit_time__isnull=True)
                .order_by("-entry_time")
                .first()
            )

            session_message = "No session change"

            if state == IoTSensor.State.DETECTED:
                if active_session is not None:
                    session_message = "An active session already exists"
                else:
                    matching_booking = None

                    # Test sessions must never attach to a real booking.
                    if not test_mode:
                        matching_booking = (
                            Booking.objects.filter(
                                slot=sensor.slot,
                                status=Booking.Status.CONFIRMED,
                                start_time__lte=now,
                                end_time__gt=now,
                            )
                            .order_by("end_time")
                            .first()
                        )

                    ParkingSession.objects.create(
                        slot=sensor.slot,
                        booking=matching_booking,
                        entry_time=now,
                        is_test_data=test_mode,
                    )

                    if test_mode:
                        session_message = "Test session started"
                    elif matching_booking:
                        session_message = "Session started and linked to booking"
                    else:
                        session_message = "Session started without a matching booking"

            elif state == IoTSensor.State.CLEAR:
                if active_session is not None:
                    # A test request may close only a test session.
                    # A normal request may close only a non-test session.
                    if active_session.is_test_data != test_mode:
                        return JsonResponse(
                            {
                                "error": (
                                    "Session mode mismatch; active session "
                                    "was not changed"
                                )
                            },
                            status=409,
                        )

                    if now > active_session.entry_time:
                        active_session.exit_time = now
                        active_session.save(update_fields=["exit_time"])
                        session_message = (
                            "Test session closed"
                            if test_mode
                            else "Parking session closed"
                        )
                    else:
                        session_message = "Invalid exit timestamp"

            sensor.state = state
            sensor.save(update_fields=["state", "last_updated"])

    except IoTSensor.DoesNotExist:
        return JsonResponse({"error": "Unknown device ID"}, status=404)

    return JsonResponse({
        "success": True,
        "device_id": sensor.device_id,
        "state": sensor.state,
        "slot": str(sensor.slot),
        "test_mode": test_mode,
        "session": session_message,
        "message": "Sensor reading processed",
    })



@login_required
def payment_checkout(request, booking_id):
    booking = get_object_or_404(
        Booking,
        pk=booking_id,
        user=request.user
    )

    payment = get_object_or_404(
        Payment,
        booking=booking
    )

    return render(request, 'parking/payment_checkout.html', {
        'booking': booking,
        'payment': payment,
    })



@login_required
@require_POST
def demo_payment_result(request, booking_id):
    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
            user=request.user
        )

        payment = get_object_or_404(
            Payment.objects.select_for_update(),
            booking=booking
        )

        if payment.status != Payment.Status.PENDING:
            messages.info(request, 'This payment has already been processed.')
            return redirect('my_bookings')

        result = request.POST.get('result')

        if result == 'success':
            payment.status = Payment.Status.PAID
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at'])

            booking.status = Booking.Status.CONFIRMED
            booking.save(update_fields=['status'])

            messages.success(
                request,
                'Payment successful! Your parking booking is confirmed.'
            )

        elif result == 'failure':
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=['status'])

            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=['status'])

            messages.error(
                request,
                'Payment failed. Your booking has been cancelled and the slot released.'
            )

        else:
            messages.error(request, 'Invalid payment result.')

    return redirect('my_bookings')

