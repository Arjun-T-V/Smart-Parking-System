from django.db import models
from django.conf import settings


class ParkingFloor(models.Model):
    name = models.CharField(max_length=50)
    floor_number = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


class ParkingSlot(models.Model):

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        RESERVED = 'RESERVED', 'Reserved'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'

    floor = models.ForeignKey(
        ParkingFloor,
        on_delete=models.CASCADE,
        related_name='slots'
    )

    slot_number = models.CharField(max_length=20)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )

    def __str__(self):
        return f"{self.floor} - Slot {self.slot_number}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['floor', 'slot_number'],
                name='unique_slot_per_floor'
            )
        ]




class Booking(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Payment'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parking_bookings'
    )

    slot = models.ForeignKey(
        ParkingSlot,
        on_delete=models.PROTECT,
        related_name='bookings'
    )

    vehicle_number = models.CharField(max_length=20)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.slot}"

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F('start_time')),
                name='booking_end_after_start'
            )
        ]
        
class Vehicle(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )

    vehicle_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(
        max_length=20,
        choices=[
            ('CAR', 'Car'),
            ('BIKE', 'Bike'),
            ('SUV', 'SUV'),
            ('OTHER', 'Other'),
        ],
        default='CAR'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'vehicle_number'],
                name='unique_vehicle_per_user'
            )
        ]

    def __str__(self):
        return f"{self.vehicle_number} - {self.user.username}"


class IoTSensor(models.Model):

    class State(models.TextChoices):
        DETECTED = 'DETECTED', 'Vehicle Detected'
        CLEAR = 'CLEAR', 'No Vehicle Detected'
        UNKNOWN = 'UNKNOWN', 'Unknown'

    slot = models.OneToOneField(
        ParkingSlot,
        on_delete=models.CASCADE,
        related_name='iot_sensor'
    )

    device_id = models.CharField(
        max_length=50,
        unique=True
    )

    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.UNKNOWN
    )

    last_updated = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.device_id} - {self.slot}"


class ParkingSession(models.Model):
    booking = models.ForeignKey(
        'Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parking_sessions'
    )

    slot = models.ForeignKey(
        ParkingSlot,
        on_delete=models.PROTECT,
        related_name='parking_sessions'
    )

    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(
        null=True,
        blank=True
    )
    
    is_test_data = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True for sessions created by controlled testing."
    )


    class Meta:
        ordering = ['-entry_time']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(exit_time__isnull=True) |
                    models.Q(exit_time__gt=models.F('entry_time'))
                ),
                name='session_exit_after_entry'
            )
        ]

    @property
    def duration_minutes(self):
        if self.exit_time is None:
            return None

        return (self.exit_time - self.entry_time).total_seconds() / 60

    @property
    def schedule_difference_minutes(self):
        """
        Positive: vehicle exited after the scheduled booking end.
        Negative: vehicle exited before the scheduled booking end.
        None: no linked booking or session is still active.
        """
        if self.booking is None or self.exit_time is None:
            return None

        return (
            self.exit_time - self.booking.end_time
        ).total_seconds() / 60

    def __str__(self):
        return f"{self.slot} - {self.entry_time}"


class Payment(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'

    class Method(models.TextChoices):
        DEMO = 'DEMO', 'Demo Payment'

    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name='payment'
    )

    parking_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    overtime_fine = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    method = models.CharField(
        max_length=10,
        choices=Method.choices,
        default=Method.DEMO
    )

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment for Booking {self.booking_id} - {self.status}"
