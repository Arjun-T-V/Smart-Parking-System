from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('parking-slots/', views.parking_slots, name='parking_slots'),
    path('book-slot/', views.book_slot, name='book_slot'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path(
        'cancel-booking/<int:booking_id>/',
        views.cancel_booking,
        name='cancel_booking'
    ),
    path('my-vehicles/', views.my_vehicles, name='my_vehicles'),
    path(
        'admin-dashboard/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),
    path(
        'admin-bookings/',
        views.admin_bookings,
        name='admin_bookings'
    ),
    path(
        'admin-bookings/<int:booking_id>/cancel/',
        views.admin_cancel_booking,
        name='admin_cancel_booking'
    ),
    path(
        'occupancy-report/',
        views.occupancy_report,
        name='occupancy_report'
    ),
    path(
        'api/iot/sensor-update/',
        views.iot_sensor_update,
        name='iot_sensor_update'
    ),
    path(
    'payment/<int:booking_id>/',
    views.payment_checkout,
    name='payment_checkout'
    ),
    path(
        'payment/<int:booking_id>/result/',
        views.demo_payment_result,
        name='demo_payment_result'
    ),
]