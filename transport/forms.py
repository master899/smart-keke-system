from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import StudentProfile, RideBooking


CAMPUS_LOCATIONS = [
    ("Campus Main Gate", "Campus Main Gate"),
    ("Senate Building", "Senate Building"),
    ("ICT Centre", "ICT Centre"),
    ("Library", "Library"),
    ("Faculty of Science", "Faculty of Science"),
    ("Faculty of Arts", "Faculty of Arts"),
    ("Faculty of Education", "Faculty of Education"),
    ("Student Affairs", "Student Affairs"),
    ("Medical Centre", "Medical Centre"),
    ("School Hostel", "School Hostel"),
    ("Permanent Site", "Permanent Site"),
    ("Take-Off Site", "Take-Off Site"),
    ("Mararaba Akunza Lodge Area", "Mararaba Akunza Lodge Area"),
    ("Bukan Sidi Lodge Area", "Bukan Sidi Lodge Area"),
]


class StudentRegistrationForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "First Name",
            "class": "form-control"
        })
    )

    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "Last Name",
            "class": "form-control"
        })
    )

    matric_number = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            "placeholder": "Matric Number",
            "class": "form-control"
        })
    )

    department = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={
            "placeholder": "Department",
            "class": "form-control"
        })
    )

    level = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Level e.g. 400",
            "class": "form-control"
        })
    )

    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            "placeholder": "Phone Number",
            "class": "form-control"
        })
    )

    hostel_or_lodge = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Hostel or Lodge",
            "class": "form-control"
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "placeholder": "Email Address",
            "class": "form-control"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Password",
            "class": "form-control"
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Confirm Password",
            "class": "form-control"
        })
    )

    def clean_matric_number(self):
        matric_number = self.cleaned_data.get("matric_number")

        if User.objects.filter(username=matric_number).exists():
            raise forms.ValidationError("A student with this matric number already exists.")

        if StudentProfile.objects.filter(matric_number=matric_number).exists():
            raise forms.ValidationError("This matric number has already been registered.")

        return matric_number

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        return cleaned_data


class RideBookingForm(forms.ModelForm):
    pickup_location = forms.ChoiceField(
        choices=CAMPUS_LOCATIONS,
        widget=forms.Select(attrs={"class": "form-control"})
    )

    destination = forms.ChoiceField(
        choices=CAMPUS_LOCATIONS,
        widget=forms.Select(attrs={"class": "form-control"})
    )

    preferred_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            "type": "datetime-local",
            "class": "form-control"
        })
    )

    class Meta:
        model = RideBooking
        fields = [
            "pickup_location",
            "destination",
            "preferred_time",
            "number_of_passengers",
            "payment_method",
        ]

        widgets = {
            "number_of_passengers": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "max": 4
            }),
            "payment_method": forms.Select(attrs={
                "class": "form-control"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        pickup_location = cleaned_data.get("pickup_location")
        destination = cleaned_data.get("destination")
        preferred_time = cleaned_data.get("preferred_time")
        number_of_passengers = cleaned_data.get("number_of_passengers")

        if pickup_location and destination and pickup_location == destination:
            self.add_error("destination", "Pickup location and destination cannot be the same.")

        if preferred_time and preferred_time < timezone.now() - timedelta(minutes=5):
          self.add_error("preferred_time", "Preferred time cannot be in the past.")

        if number_of_passengers and number_of_passengers > 4:
            self.add_error("number_of_passengers", "A Keke ride cannot take more than 4 passengers.")

        return cleaned_data