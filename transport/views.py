import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import Q, Sum, Count

from .forms import StudentRegistrationForm, RideBookingForm
from .models import (
    StudentProfile,
    DriverProfile,
    RideBooking,
    Payment,
    Notification,
)


LOCATION_COORDINATES = {
    "Campus Main Gate": (1, 1),
    "Senate Building": (2, 4),
    "ICT Centre": (3, 5),
    "Library": (4, 5),
    "Faculty of Science": (5, 4),
    "Faculty of Arts": (6, 3),
    "Faculty of Education": (5, 2),
    "Student Affairs": (3, 3),
    "Medical Centre": (2, 2),
    "School Hostel": (1, 5),
    "Permanent Site": (7, 7),
    "Take-Off Site": (2, 1),
    "Mararaba Akunza Lodge Area": (8, 3),
    "Bukan Sidi Lodge Area": (7, 1),
}


def calculate_distance_km(start_location, end_location):
    start = LOCATION_COORDINATES.get(start_location, (1, 1))
    end = LOCATION_COORDINATES.get(end_location, (1, 1))

    x_distance = abs(start[0] - end[0])
    y_distance = abs(start[1] - end[1])

    distance = x_distance + y_distance

    if distance <= 0:
        distance = 1

    return Decimal(distance)


def calculate_eta_minutes(distance_km):
    eta = int(distance_km * 4) + 3
    return max(5, eta)


def calculate_fare(distance_km, passengers):
    base_fare = Decimal("250.00")
    distance_charge = distance_km * Decimal("120.00")
    passenger_charge = Decimal(passengers - 1) * Decimal("100.00")
    fare = base_fare + distance_charge + passenger_charge
    return fare


def calculate_driver_pickup_distance(driver_location, pickup_location):
    driver_coordinate = LOCATION_COORDINATES.get(driver_location, (1, 1))
    pickup_coordinate = LOCATION_COORDINATES.get(pickup_location, (1, 1))

    x_distance = abs(driver_coordinate[0] - pickup_coordinate[0])
    y_distance = abs(driver_coordinate[1] - pickup_coordinate[1])

    distance = x_distance + y_distance

    if distance <= 0:
        distance = 1

    return Decimal(distance)


def calculate_driver_pickup_eta(distance_km):
    eta = int(distance_km * 3) + 2
    return max(3, eta)


# Precise GPS coordinates for known campus locations. Used by map views.
LOCATION_GPS_COORDINATES = {
    "Campus Main Gate": {"lat": 8.479152810354291, "lng":8.557571840196514},
    "Faculty of Computing": {"lat": 8.4793000, "lng": 8.5578000},
    "Senate Building": {"lat": 8.4791000, "lng": 8.5576000},
    "ICT Centre": {"lat": 8.4794500, "lng": 8.5580500},
    "Library": {"lat": 8.4798000, "lng": 8.5584000},
    "Faculty of Science": {"lat": 8.4802500, "lng": 8.5588500},
    "Faculty of Arts": {"lat": 8.4789500, "lng": 8.5589000},
    "Faculty of Education": {"lat": 8.4785000, "lng": 8.5583000},
    "Student Affairs": {"lat": 8.4783500, "lng": 8.5577500},
    "Medical Centre": {"lat": 8.4779500, "lng": 8.5573500},
    "School Hostel": {"lat": 8.4775000, "lng": 8.5581000},
    "Permanent Site": {"lat": 8.4787287, "lng": 8.5571845},
    "Take-Off Site": {"lat": 8.4939000, "lng": 8.5153200},
    "Mararaba Akunza Lodge Area": {"lat": 8.4878000, "lng": 8.5455000},
    "Bukan Sidi Lodge Area": {"lat": 8.4919000, "lng": 8.5228000},
}


def get_location_gps(location_name):
    return LOCATION_GPS_COORDINATES.get(
        location_name,
        LOCATION_GPS_COORDINATES["Campus Main Gate"]
    )


def find_nearest_available_driver(pickup_location):
    available_drivers = DriverProfile.objects.filter(
        is_available=True,
        is_verified=True
    )

    if not available_drivers.exists():
        return None

    pickup_coordinate = LOCATION_COORDINATES.get(pickup_location, (1, 1))

    best_driver = None
    best_distance = None

    for driver in available_drivers:
        driver_coordinate = LOCATION_COORDINATES.get(driver.current_location, (1, 1))

        distance = abs(driver_coordinate[0] - pickup_coordinate[0]) + abs(
            driver_coordinate[1] - pickup_coordinate[1]
        )

        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_driver = driver

    return best_driver


def get_logged_in_student_or_redirect(request):
    if not request.user.is_authenticated:
        return None

    try:
        return StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        return None


def home_view(request):
    return render(request, "pages/home.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("student_dashboard")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["matric_number"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"]
            )

            StudentProfile.objects.create(
                user=user,
                matric_number=form.cleaned_data["matric_number"],
                department=form.cleaned_data["department"],
                level=form.cleaned_data["level"],
                phone_number=form.cleaned_data["phone_number"],
                hostel_or_lodge=form.cleaned_data["hostel_or_lodge"],
                is_verified=True
            )

            messages.success(request, "Registration successful. You can now login.")
            return redirect("login")
    else:
        form = StudentRegistrationForm()

    return render(request, "auth/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect("system_admin_dashboard")

        if hasattr(request.user, "driver_profile"):
            return redirect("driver_dashboard")

        return redirect("student_dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_staff or user.is_superuser:
                return redirect("system_admin_dashboard")

            if hasattr(user, "driver_profile"):
                return redirect("driver_dashboard")

            return redirect("student_dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You have logged out successfully.")
    return redirect("login")


@login_required
def student_dashboard_view(request):
    student = get_object_or_404(StudentProfile, user=request.user)

    active_ride = RideBooking.objects.filter(
        student=student
    ).exclude(
        status__in=[
            RideBooking.STATUS_COMPLETED,
            RideBooking.STATUS_CANCELLED
        ]
    ).first()

    recent_rides = RideBooking.objects.filter(student=student)[:3]

    context = {
        "student": student,
        "active_ride": active_ride,
        "recent_rides": recent_rides,
    }

    return render(request, "student/dashboard.html", context)


@login_required
def book_ride_view(request):
    student = get_object_or_404(StudentProfile, user=request.user)

    active_ride_exists = RideBooking.objects.filter(
        student=student
    ).exclude(
        status__in=[
            RideBooking.STATUS_COMPLETED,
            RideBooking.STATUS_CANCELLED
        ]
    ).exists()

    if active_ride_exists:
        messages.error(request, "You already have an active ride. Complete or cancel it before booking another.")
        return redirect("student_dashboard")

    if not student.is_verified:
        messages.error(request, "Your student account is not verified yet.")
        return redirect("student_dashboard")

    if request.method == "POST":
        form = RideBookingForm(request.POST)

        if form.is_valid():
            pickup_location = form.cleaned_data["pickup_location"]
            destination = form.cleaned_data["destination"]
            passengers = form.cleaned_data["number_of_passengers"]

            distance_km = calculate_distance_km(pickup_location, destination)
            eta_minutes = calculate_eta_minutes(distance_km)
            fare = calculate_fare(distance_km, passengers)

            driver = find_nearest_available_driver(pickup_location)

            if driver is None:
                messages.error(request, "No verified driver is currently available. Please try again later.")
                return redirect("book_ride")

            ride = form.save(commit=False)
            ride.student = student
            ride.driver = driver
            ride.estimated_distance_km = distance_km
            ride.estimated_eta_minutes = eta_minutes
            ride.estimated_fare = fare
            ride.status = RideBooking.STATUS_ASSIGNED
            ride.save()

            driver.is_available = False
            driver.save()

            Payment.objects.create(
                ride=ride,
                amount=fare,
                method=ride.payment_method,
                status=Payment.STATUS_PENDING
            )

            Notification.objects.create(
                user=student.user,
                title="Ride Confirmed",
                message=f"Your ride has been assigned to {driver.user.get_full_name()}."
            )

            Notification.objects.create(
                user=driver.user,
                title="New Ride Assigned",
                message=f"Pickup: {ride.pickup_location}. Destination: {ride.destination}."
            )

            messages.success(request, "Ride booked successfully. A driver has been assigned.")
            return redirect("ride_detail", ride_id=ride.id)
    else:
        form = RideBookingForm()

    return render(request, "student/book_ride.html", {"form": form})


@login_required
def ride_detail_view(request, ride_id):
    ride = get_object_or_404(RideBooking, id=ride_id)

    if hasattr(request.user, "student_profile") and ride.student.user != request.user:
        messages.error(request, "You are not allowed to view this ride.")
        return redirect("student_dashboard")

    if hasattr(request.user, "driver_profile") and ride.driver and ride.driver.user != request.user:
        messages.error(request, "You are not allowed to view this ride.")
        return redirect("driver_dashboard")

    tracking_title = "Waiting for Driver"
    tracking_from_label = "Driver Current Location"
    tracking_to_label = "Pickup Point"
    tracking_from_value = "Not available"
    tracking_to_value = ride.pickup_location
    tracking_distance = Decimal("0.00")
    tracking_eta = 0
    driver_progress_percent = 0

    pickup_gps = get_location_gps(ride.pickup_location)
    destination_gps = get_location_gps(ride.destination)
    driver_gps = None

    if ride.driver:
        if ride.driver.current_latitude and ride.driver.current_longitude:
            driver_gps = {
                "lat": float(ride.driver.current_latitude),
                "lng": float(ride.driver.current_longitude),
            }
        else:
            driver_gps = get_location_gps(ride.driver.current_location)

        if ride.status in [RideBooking.STATUS_ASSIGNED, RideBooking.STATUS_ARRIVING]:
            tracking_title = "Keke pickup progress"
            tracking_from_label = "Driver Current Location"
            tracking_to_label = "Pickup Point"
            tracking_from_value = ride.driver.current_location
            tracking_to_value = ride.pickup_location

            tracking_distance = calculate_driver_pickup_distance(
                ride.driver.current_location,
                ride.pickup_location
            )
            tracking_eta = calculate_driver_pickup_eta(tracking_distance)

            if ride.status == RideBooking.STATUS_ASSIGNED:
                driver_progress_percent = 30
            elif ride.status == RideBooking.STATUS_ARRIVING:
                driver_progress_percent = 70

        elif ride.status == RideBooking.STATUS_IN_TRANSIT:
            tracking_title = "Trip progress to destination"
            tracking_from_label = "Current Location"
            tracking_to_label = "Destination"
            tracking_from_value = ride.pickup_location
            tracking_to_value = ride.destination
            tracking_distance = ride.estimated_distance_km
            tracking_eta = ride.estimated_eta_minutes
            driver_progress_percent = 55

        elif ride.status == RideBooking.STATUS_COMPLETED:
            tracking_title = "Trip completed"
            tracking_from_label = "Pickup Point"
            tracking_to_label = "Destination"
            tracking_from_value = ride.pickup_location
            tracking_to_value = ride.destination
            tracking_distance = Decimal("0.00")
            tracking_eta = 0
            driver_progress_percent = 100

        elif ride.status == RideBooking.STATUS_CANCELLED:
            tracking_title = "Ride cancelled"
            tracking_from_label = "Driver Location"
            tracking_to_label = "Pickup Point"
            tracking_from_value = ride.driver.current_location
            tracking_to_value = ride.pickup_location
            tracking_distance = Decimal("0.00")
            tracking_eta = 0
            driver_progress_percent = 0

    ride_map_data = {
        "rideId": ride.id,
        "trackingUrl": request.build_absolute_uri(
            reverse("ride_tracking_data", kwargs={"ride_id": ride.id})
        ),
        "driver": driver_gps,
        "pickup": pickup_gps,
        "destination": destination_gps,
        "pickupName": ride.pickup_location,
        "destinationName": ride.destination,
        "driverName": ride.driver.user.get_full_name() if ride.driver else "Driver not assigned",
        "status": ride.status,
    }

    context = {
        "ride": ride,
        "tracking_title": tracking_title,
        "tracking_from_label": tracking_from_label,
        "tracking_to_label": tracking_to_label,
        "tracking_from_value": tracking_from_value,
        "tracking_to_value": tracking_to_value,
        "tracking_distance": tracking_distance,
        "tracking_eta": tracking_eta,
        "driver_progress_percent": driver_progress_percent,
        "ride_map_data": ride_map_data,
    }

    return render(request, "student/ride_detail.html", context)


@login_required
def ride_tracking_data_view(request, ride_id):
    ride = get_object_or_404(RideBooking, id=ride_id)

    allowed = False

    if hasattr(request.user, "student_profile") and ride.student.user == request.user:
        allowed = True

    if hasattr(request.user, "driver_profile") and ride.driver and ride.driver.user == request.user:
        allowed = True

    if request.user.is_staff or request.user.is_superuser:
        allowed = True

    if not allowed:
        return JsonResponse({
            "success": False,
            "message": "You are not allowed to access this tracking data."
        }, status=403)

    driver_data = None

    if ride.driver:
        if ride.driver.current_latitude and ride.driver.current_longitude:
            driver_data = {
                "lat": float(ride.driver.current_latitude),
                "lng": float(ride.driver.current_longitude),
                "lastUpdate": (
                    timezone.localtime(ride.driver.last_location_update).strftime("%Y-%m-%d %H:%M:%S")
                    if ride.driver.last_location_update else "Not updated"
                ),
            }
        else:
            fallback_gps = get_location_gps(ride.driver.current_location)
            driver_data = {
                "lat": fallback_gps["lat"],
                "lng": fallback_gps["lng"],
                "lastUpdate": "Using saved driver location",
            }

    return JsonResponse({
        "success": True,
        "rideStatus": ride.status,
        "rideStatusDisplay": ride.get_status_display(),
        "driver": driver_data,
        "pickup": get_location_gps(ride.pickup_location),
        "destination": get_location_gps(ride.destination),
    })


@login_required
def student_ride_history_view(request):
    student = get_object_or_404(StudentProfile, user=request.user)

    status_filter = request.GET.get("status", "").strip()

    rides = RideBooking.objects.filter(student=student)

    if status_filter:
        rides = rides.filter(status=status_filter)

    context = {
        "student": student,
        "rides": rides,
        "status_filter": status_filter,
        "status_choices": RideBooking.STATUS_CHOICES,
    }

    return render(request, "student/ride_history.html", context)


@login_required
def student_payment_view(request, ride_id):
    student = get_object_or_404(StudentProfile, user=request.user)
    ride = get_object_or_404(RideBooking, id=ride_id, student=student)

    if request.method == "POST":
        payment = getattr(ride, "payment", None)

        if payment is None:
            Payment.objects.create(
                ride=ride,
                amount=ride.estimated_fare,
                method=ride.payment_method,
                status=Payment.STATUS_PAID
            )
        else:
            payment.status = Payment.STATUS_PAID
            payment.save()

        Notification.objects.create(
            user=student.user,
            title="Payment Confirmed",
            message=f"Your payment of ₦{ride.estimated_fare} for ride #{ride.id} has been confirmed."
        )

        messages.success(request, "Payment confirmed successfully.")
        return redirect("ride_detail", ride_id=ride.id)

    return render(request, "student/payment.html", {"ride": ride})


@login_required
def student_payments_view(request):
    student = get_logged_in_student_or_redirect(request)

    if student is None:
        if request.user.is_staff or request.user.is_superuser:
            return redirect("system_admin_dashboard")

        if hasattr(request.user, "driver_profile"):
            return redirect("driver_dashboard")

        return redirect("login")

    rides = RideBooking.objects.filter(student=student).select_related("driver", "payment")

    context = {
        "student": student,
        "rides": rides,
    }

    return render(request, "student/payments.html", context)


@login_required
def student_notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)

    unread_notifications = notifications.filter(is_read=False)

    if request.method == "POST":
        unread_notifications.update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect("student_notifications")

    context = {
        "notifications": notifications,
        "unread_count": unread_notifications.count(),
    }

    return render(request, "student/notifications.html", context)


@login_required
def student_profile_view(request):
    student = get_object_or_404(StudentProfile, user=request.user)

    if request.method == "POST":
        phone_number = request.POST.get("phone_number", "").strip()
        hostel_or_lodge = request.POST.get("hostel_or_lodge", "").strip()
        level = request.POST.get("level", "").strip()

        if not phone_number:
            messages.error(request, "Phone number is required.")
            return redirect("student_profile")

        student.phone_number = phone_number
        student.hostel_or_lodge = hostel_or_lodge
        student.level = level
        student.save()

        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.last_name = request.POST.get("last_name", "").strip()
        request.user.email = request.POST.get("email", "").strip()
        request.user.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("student_profile")

    return render(request, "student/profile.html", {"student": student})


@login_required
def cancel_ride_view(request, ride_id):
    student = get_object_or_404(StudentProfile, user=request.user)
    ride = get_object_or_404(RideBooking, id=ride_id, student=student)

    if ride.status in [RideBooking.STATUS_COMPLETED, RideBooking.STATUS_CANCELLED]:
        messages.error(request, "This ride cannot be cancelled.")
        return redirect("ride_detail", ride_id=ride.id)

    ride.status = RideBooking.STATUS_CANCELLED
    ride.cancellation_reason = "Cancelled by student"
    ride.save()

    if ride.driver:
        ride.driver.is_available = True
        ride.driver.save()

    if hasattr(ride, "payment"):
        ride.payment.status = Payment.STATUS_CANCELLED
        ride.payment.save()

    Notification.objects.create(
        user=student.user,
        title="Ride Cancelled",
        message=f"Your ride from {ride.pickup_location} to {ride.destination} has been cancelled."
    )

    if ride.driver:
        Notification.objects.create(
            user=ride.driver.user,
            title="Ride Cancelled",
            message=f"The ride request from {ride.pickup_location} has been cancelled by the student."
        )

    messages.success(request, "Ride cancelled successfully.")
    return redirect("student_dashboard")


@login_required
def driver_dashboard_view(request):
    driver = get_object_or_404(DriverProfile, user=request.user)

    active_rides = RideBooking.objects.filter(
        driver=driver
    ).exclude(
        status__in=[
            RideBooking.STATUS_COMPLETED,
            RideBooking.STATUS_CANCELLED
        ]
    )

    completed_rides = RideBooking.objects.filter(
        driver=driver,
        status=RideBooking.STATUS_COMPLETED
    )[:5]

    context = {
        "driver": driver,
        "active_rides": active_rides,
        "completed_rides": completed_rides,
    }

    return render(request, "driver/dashboard.html", context)


@login_required
def driver_profile_view(request):
    if not hasattr(request.user, "driver_profile"):
        messages.error(request, "Only drivers can access this page.")
        return redirect("student_dashboard")

    driver = request.user.driver_profile

    if request.method == "POST":
        phone_number = request.POST.get("phone_number", "").strip()
        vehicle_color = request.POST.get("vehicle_color", "").strip()
        current_location = request.POST.get("current_location", "").strip()

        if not phone_number:
            messages.error(request, "Phone number is required.")
            return redirect("driver_profile")

        if not current_location:
            messages.error(request, "Current location is required.")
            return redirect("driver_profile")

        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.last_name = request.POST.get("last_name", "").strip()
        request.user.email = request.POST.get("email", "").strip()
        request.user.save()

        driver.phone_number = phone_number
        driver.vehicle_color = vehicle_color or "Yellow"
        driver.current_location = current_location
        driver.save()

        messages.success(request, "Driver profile updated successfully.")
        return redirect("driver_profile")

    return render(request, "driver/profile.html", {"driver": driver})


@login_required
def driver_ride_history_view(request):
    if not hasattr(request.user, "driver_profile"):
        messages.error(request, "Only drivers can access this page.")
        return redirect("student_dashboard")

    driver = request.user.driver_profile
    status_filter = request.GET.get("status", "").strip()

    rides = RideBooking.objects.filter(driver=driver)

    if status_filter:
        rides = rides.filter(status=status_filter)

    context = {
        "driver": driver,
        "rides": rides,
        "status_filter": status_filter,
        "status_choices": RideBooking.STATUS_CHOICES,
    }

    return render(request, "driver/ride_history.html", context)


@login_required
def driver_notifications_view(request):
    if not hasattr(request.user, "driver_profile"):
        messages.error(request, "Only drivers can access this page.")
        return redirect("student_dashboard")

    notifications = Notification.objects.filter(user=request.user)
    unread_notifications = notifications.filter(is_read=False)

    if request.method == "POST":
        unread_notifications.update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect("driver_notifications")

    context = {
        "notifications": notifications,
        "unread_count": unread_notifications.count(),
    }

    return render(request, "driver/notifications.html", context)


@login_required
def driver_toggle_availability_view(request):
    if not hasattr(request.user, "driver_profile"):
        messages.error(request, "Only drivers can update availability.")
        return redirect("student_dashboard")

    driver = request.user.driver_profile

    active_ride_exists = RideBooking.objects.filter(
        driver=driver
    ).exclude(
        status__in=[
            RideBooking.STATUS_COMPLETED,
            RideBooking.STATUS_CANCELLED
        ]
    ).exists()

    if active_ride_exists:
        messages.error(request, "You cannot change availability while you have an active ride.")
        return redirect("driver_dashboard")

    driver.is_available = not driver.is_available
    driver.save()

    if driver.is_available:
        messages.success(request, "You are now available to receive ride requests.")
    else:
        messages.success(request, "You are now unavailable for new ride requests.")

    return redirect("driver_dashboard")


@login_required
def update_ride_status_view(request, ride_id, status):
    driver = get_object_or_404(DriverProfile, user=request.user)
    ride = get_object_or_404(RideBooking, id=ride_id, driver=driver)

    allowed_statuses = [
        RideBooking.STATUS_ARRIVING,
        RideBooking.STATUS_IN_TRANSIT,
        RideBooking.STATUS_COMPLETED,
        RideBooking.STATUS_CANCELLED,
    ]

    if status not in allowed_statuses:
        messages.error(request, "Invalid ride status.")
        return redirect("driver_dashboard")

    ride.status = status
    ride.save()

    if status == RideBooking.STATUS_COMPLETED:
        driver.is_available = True
        driver.current_location = ride.destination
        driver.total_completed_rides += 1
        driver.save()

        if hasattr(ride, "payment"):
            ride.payment.status = Payment.STATUS_PAID
            ride.payment.save()

    if status == RideBooking.STATUS_CANCELLED:
        driver.is_available = True
        driver.save()

        if hasattr(ride, "payment"):
            ride.payment.status = Payment.STATUS_CANCELLED
            ride.payment.save()

    Notification.objects.create(
        user=ride.student.user,
        title="Ride Status Updated",
        message=f"Your ride status is now: {ride.get_status_display()}."
    )

    messages.success(request, "Ride status updated successfully.")
    return redirect("driver_dashboard")


@login_required
@require_POST
def driver_update_location_view(request):
    if not hasattr(request.user, "driver_profile"):
        return JsonResponse({
            "success": False,
            "message": "Only drivers can update GPS location."
        }, status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
        latitude = Decimal(str(data.get("latitude")))
        longitude = Decimal(str(data.get("longitude")))
    except (json.JSONDecodeError, InvalidOperation, TypeError):
        return JsonResponse({
            "success": False,
            "message": "Invalid GPS coordinates."
        }, status=400)

    if latitude < Decimal("-90") or latitude > Decimal("90"):
        return JsonResponse({
            "success": False,
            "message": "Latitude out of range."
        }, status=400)

    if longitude < Decimal("-180") or longitude > Decimal("180"):
        return JsonResponse({
            "success": False,
            "message": "Longitude out of range."
        }, status=400)

    driver = request.user.driver_profile
    driver.current_latitude = latitude
    driver.current_longitude = longitude
    driver.last_location_update = timezone.now()
    driver.save()

    return JsonResponse({
        "success": True,
        "message": "Driver GPS location updated successfully.",
        "latitude": str(driver.current_latitude),
        "longitude": str(driver.current_longitude),
        "updated_at": timezone.localtime(driver.last_location_update).strftime("%Y-%m-%d %H:%M:%S"),
    })


@login_required
def system_admin_dashboard_view(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Only system administrators can access this page.")
        return redirect("login")

    total_students = StudentProfile.objects.count()
    verified_students = StudentProfile.objects.filter(is_verified=True).count()

    total_drivers = DriverProfile.objects.count()
    available_drivers = DriverProfile.objects.filter(is_available=True).count()
    busy_drivers = DriverProfile.objects.filter(is_available=False).count()
    verified_drivers = DriverProfile.objects.filter(is_verified=True).count()

    total_rides = RideBooking.objects.count()
    active_rides = RideBooking.objects.exclude(
        status__in=[RideBooking.STATUS_COMPLETED, RideBooking.STATUS_CANCELLED]
    ).count()
    completed_rides = RideBooking.objects.filter(status=RideBooking.STATUS_COMPLETED).count()
    cancelled_rides = RideBooking.objects.filter(status=RideBooking.STATUS_CANCELLED).count()

    pending_payments = Payment.objects.filter(status=Payment.STATUS_PENDING).count()
    paid_payments = Payment.objects.filter(status=Payment.STATUS_PAID).count()
    cancelled_payments = Payment.objects.filter(status=Payment.STATUS_CANCELLED).count()

    total_revenue = Payment.objects.filter(status=Payment.STATUS_PAID).aggregate(
        total=Sum("amount")
    )["total"] or 0

    recent_rides = RideBooking.objects.select_related("student__user", "driver__user")[:6]
    recent_payments = Payment.objects.select_related("ride")[:6]

    context = {
        "total_students": total_students,
        "verified_students": verified_students,
        "total_drivers": total_drivers,
        "available_drivers": available_drivers,
        "busy_drivers": busy_drivers,
        "verified_drivers": verified_drivers,
        "total_rides": total_rides,
        "active_rides": active_rides,
        "completed_rides": completed_rides,
        "cancelled_rides": cancelled_rides,
        "pending_payments": pending_payments,
        "paid_payments": paid_payments,
        "cancelled_payments": cancelled_payments,
        "total_revenue": total_revenue,
        "recent_rides": recent_rides,
        "recent_payments": recent_payments,
    }

    return render(request, "admin_dashboard/dashboard.html", context)


@login_required
def admin_students_view(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Only system administrators can access this page.")
        return redirect("login")

    search_query = request.GET.get("q", "").strip()

    students = StudentProfile.objects.select_related("user").all()

    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(matric_number__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )

    context = {
        "students": students,
        "search_query": search_query,
    }

    return render(request, "admin_dashboard/students.html", context)


@login_required
def admin_drivers_view(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Only system administrators can access this page.")
        return redirect("login")

    search_query = request.GET.get("q", "").strip()
    availability_filter = request.GET.get("availability", "").strip()

    drivers = DriverProfile.objects.select_related("user").all()

    if search_query:
        drivers = drivers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(driver_id__icontains=search_query) |
            Q(keke_plate_number__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(current_location__icontains=search_query)
        )

    if availability_filter == "available":
        drivers = drivers.filter(is_available=True)

    if availability_filter == "busy":
        drivers = drivers.filter(is_available=False)

    context = {
        "drivers": drivers,
        "search_query": search_query,
        "availability_filter": availability_filter,
    }

    return render(request, "admin_dashboard/drivers.html", context)


@login_required
def admin_rides_view(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Only system administrators can access this page.")
        return redirect("login")

    status_filter = request.GET.get("status", "").strip()
    search_query = request.GET.get("q", "").strip()

    rides = RideBooking.objects.select_related("student__user", "driver__user").all()

    if status_filter:
        rides = rides.filter(status=status_filter)

    if search_query:
        rides = rides.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__matric_number__icontains=search_query) |
            Q(driver__user__first_name__icontains=search_query) |
            Q(driver__user__last_name__icontains=search_query) |
            Q(pickup_location__icontains=search_query) |
            Q(destination__icontains=search_query)
        )

    context = {
        "rides": rides,
        "status_filter": status_filter,
        "search_query": search_query,
        "status_choices": RideBooking.STATUS_CHOICES,
    }

    return render(request, "admin_dashboard/rides.html", context)


@login_required
def admin_payments_view(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Only system administrators can access this page.")
        return redirect("login")

    status_filter = request.GET.get("status", "").strip()
    search_query = request.GET.get("q", "").strip()

    payments = Payment.objects.select_related(
        "ride__student__user",
        "ride__driver__user"
    ).all()

    if status_filter:
        payments = payments.filter(status=status_filter)

    if search_query:
        payments = payments.filter(
            Q(ride__student__user__first_name__icontains=search_query) |
            Q(ride__student__user__last_name__icontains=search_query) |
            Q(ride__student__matric_number__icontains=search_query) |
            Q(ride__driver__user__first_name__icontains=search_query) |
            Q(ride__driver__user__last_name__icontains=search_query) |
            Q(transaction_reference__icontains=search_query)
        )

    context = {
        "payments": payments,
        "status_filter": status_filter,
        "search_query": search_query,
        "payment_status_choices": Payment.PAYMENT_STATUS_CHOICES,
    }

    return render(request, "admin_dashboard/payments.html", context)


@login_required
def admin_reports_view(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Only system administrators can access this page.")
        return redirect("login")

    total_rides = RideBooking.objects.count()
    completed_rides = RideBooking.objects.filter(status=RideBooking.STATUS_COMPLETED).count()
    cancelled_rides = RideBooking.objects.filter(status=RideBooking.STATUS_CANCELLED).count()
    active_rides = RideBooking.objects.exclude(
        status__in=[RideBooking.STATUS_COMPLETED, RideBooking.STATUS_CANCELLED]
    ).count()

    total_revenue = Payment.objects.filter(status=Payment.STATUS_PAID).aggregate(
        total=Sum("amount")
    )["total"] or 0

    top_pickups = RideBooking.objects.values("pickup_location").annotate(
        total=Count("id")
    ).order_by("-total")[:5]

    top_destinations = RideBooking.objects.values("destination").annotate(
        total=Count("id")
    ).order_by("-total")[:5]

    driver_performance = DriverProfile.objects.select_related("user").order_by(
        "-total_completed_rides"
    )[:5]

    context = {
        "total_rides": total_rides,
        "completed_rides": completed_rides,
        "cancelled_rides": cancelled_rides,
        "active_rides": active_rides,
        "total_revenue": total_revenue,
        "top_pickups": top_pickups,
        "top_destinations": top_destinations,
        "driver_performance": driver_performance,
    }

    return render(request, "admin_dashboard/reports.html", context)