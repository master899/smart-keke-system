from django.contrib import admin
from .models import (
    StudentProfile,
    DriverProfile,
    RideBooking,
    Payment,
    RideFeedback,
    Notification,
)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "matric_number", "department", "phone_number", "is_verified", "date_created")
    list_filter = ("department", "is_verified", "date_created")
    search_fields = ("user__first_name", "user__last_name", "matric_number", "department", "phone_number")


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "driver_id",
        "phone_number",
        "keke_plate_number",
        "current_location",
        "is_available",
        "is_verified",
        "average_rating",
    )
    list_filter = ("is_available", "is_verified", "current_location")
    search_fields = ("user__first_name", "user__last_name", "driver_id", "keke_plate_number", "phone_number")


@admin.register(RideBooking)
class RideBookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "driver",
        "pickup_location",
        "destination",
        "preferred_time",
        "estimated_fare",
        "payment_method",
        "status",
        "date_booked",
    )
    list_filter = ("status", "payment_method", "date_booked")
    search_fields = (
        "student__user__first_name",
        "student__user__last_name",
        "driver__user__first_name",
        "driver__user__last_name",
        "pickup_location",
        "destination",
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("ride", "amount", "method", "status", "transaction_reference", "date_created")
    list_filter = ("method", "status", "date_created")
    search_fields = ("transaction_reference",)


@admin.register(RideFeedback)
class RideFeedbackAdmin(admin.ModelAdmin):
    list_display = ("ride", "student", "driver", "rating", "date_created")
    list_filter = ("rating", "date_created")
    search_fields = ("student__user__first_name", "driver__user__first_name", "comment")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "date_created")
    list_filter = ("is_read", "date_created")
    search_fields = ("user__username", "title", "message")