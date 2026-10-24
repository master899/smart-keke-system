from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),

    # Authentication
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Student
    path("student/dashboard/", views.student_dashboard_view, name="student_dashboard"),
    path("student/book-ride/", views.book_ride_view, name="book_ride"),
    path("student/ride-history/", views.student_ride_history_view, name="student_ride_history"),
    path("student/payments/", views.student_payments_view, name="student_payments"),
    path("student/payment/<int:ride_id>/", views.student_payment_view, name="student_payment"),
    path("student/notifications/", views.student_notifications_view, name="student_notifications"),
    path("student/profile/", views.student_profile_view, name="student_profile"),

    # Ride
    path("ride/<int:ride_id>/", views.ride_detail_view, name="ride_detail"),
    path("ride/<int:ride_id>/tracking-data/", views.ride_tracking_data_view, name="ride_tracking_data"),
    path("ride/<int:ride_id>/cancel/", views.cancel_ride_view, name="cancel_ride"),

    # Driver
    path("driver/dashboard/", views.driver_dashboard_view, name="driver_dashboard"),
    path("driver/profile/", views.driver_profile_view, name="driver_profile"),
    path("driver/ride-history/", views.driver_ride_history_view, name="driver_ride_history"),
    path("driver/notifications/", views.driver_notifications_view, name="driver_notifications"),
    path("driver/toggle-availability/", views.driver_toggle_availability_view, name="driver_toggle_availability"),
    path("driver/update-location/", views.driver_update_location_view, name="driver_update_location"),
    path(
        "driver/ride/<int:ride_id>/update/<str:status>/",
        views.update_ride_status_view,
        name="update_ride_status"
),
    # System Admin
    path("system-admin/dashboard/", views.system_admin_dashboard_view, name="system_admin_dashboard"),
    path("system-admin/students/", views.admin_students_view, name="admin_students"),
    path("system-admin/drivers/", views.admin_drivers_view, name="admin_drivers"),
    path("system-admin/rides/", views.admin_rides_view, name="admin_rides"),
    path("system-admin/payments/", views.admin_payments_view, name="admin_payments"),
    path("system-admin/reports/", views.admin_reports_view, name="admin_reports"),
]