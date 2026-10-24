from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import StudentProfile


class StudentFlowTests(TestCase):
    def test_homepage_loads(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)

    def test_student_can_register_and_log_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Amina",
                "last_name": "Example",
                "matric_number": "TEST/2026/001",
                "department": "Computer Science",
                "level": "400",
                "phone_number": "08000000000",
                "hostel_or_lodge": "",
                "email": "amina@example.com",
                "password": "A-strong-password-2026",
                "confirm_password": "A-strong-password-2026",
            },
        )

        self.assertRedirects(response, reverse("login"))
        self.assertTrue(
            StudentProfile.objects.filter(matric_number="TEST/2026/001").exists()
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "TEST/2026/001",
                "password": "A-strong-password-2026",
            },
        )

        self.assertRedirects(response, reverse("student_dashboard"))
        self.assertTrue(
            User.objects.filter(username="TEST/2026/001").exists()
        )
