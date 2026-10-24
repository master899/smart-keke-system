from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    matric_number = models.CharField(max_length=30, unique=True)
    department = models.CharField(max_length=120)
    level = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=20)
    hostel_or_lodge = models.CharField(max_length=150, blank=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.matric_number}"


class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="driver_profile")
    driver_id = models.CharField(max_length=30, unique=True)
    phone_number = models.CharField(max_length=20)
    keke_plate_number = models.CharField(max_length=30, unique=True)
    vehicle_color = models.CharField(max_length=50, default="Yellow")
    current_location = models.CharField(max_length=150, default="Campus Main Gate")
    current_latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    current_longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)
    vehicle_photo = models.ImageField(upload_to="vehicle_photos/", blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    total_completed_rides = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.keke_plate_number}"


class RideBooking(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ASSIGNED = "assigned"
    STATUS_ARRIVING = "arriving"
    STATUS_IN_TRANSIT = "in_transit"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ASSIGNED, "Driver Assigned"),
        (STATUS_ARRIVING, "Driver Arriving"),
        (STATUS_IN_TRANSIT, "In Transit"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PAYMENT_CASH = "cash"
    PAYMENT_TRANSFER = "transfer"
    PAYMENT_WALLET = "campus_wallet"

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_TRANSFER, "Bank Transfer"),
        (PAYMENT_WALLET, "Campus Wallet"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="rides")
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        related_name="assigned_rides",
        blank=True,
        null=True
    )
    pickup_location = models.CharField(max_length=150)
    destination = models.CharField(max_length=150)
    preferred_time = models.DateTimeField()
    number_of_passengers = models.PositiveIntegerField(default=1)
    estimated_distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=1.00)
    estimated_eta_minutes = models.PositiveIntegerField(default=5)
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_CASH)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    cancellation_reason = models.TextField(blank=True)
    date_booked = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_booked"]

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.pickup_location} to {self.destination}"


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    PAYMENT_STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    ride = models.OneToOneField(RideBooking, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=30, choices=RideBooking.PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default=STATUS_PENDING)
    transaction_reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Ride #{self.ride.id} - {self.status}"


class RideFeedback(models.Model):
    ride = models.OneToOneField(RideBooking, on_delete=models.CASCADE, related_name="feedback")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="feedbacks")
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="feedbacks")
    rating = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    comment = models.TextField(blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.get_full_name()} rated {self.driver.user.get_full_name()} {self.rating}/5"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=120)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_created"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"