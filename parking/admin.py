
from django.contrib import admin
from .models import ParkingFloor, ParkingSlot, Booking, ParkingSession, IoTSensor, Payment



admin.site.register(IoTSensor)

class ParkingSlotInline(admin.TabularInline):
    model = ParkingSlot
    extra = 1


@admin.register(ParkingFloor)
class ParkingFloorAdmin(admin.ModelAdmin):
    list_display = ('name', 'floor_number')
    inlines = [ParkingSlotInline]


@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ('slot_number', 'floor', 'status')
    list_filter = ('floor', 'status')
    search_fields = ('slot_number',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'slot',
        'vehicle_number',
        'start_time',
        'end_time',
        'status',
    )

    list_filter = ('status', 'start_time')
    search_fields = ('user__username', 'vehicle_number', 'slot__slot_number')
    readonly_fields = ('created_at',)

admin.site.register(ParkingSession)
admin.site.register(Payment)