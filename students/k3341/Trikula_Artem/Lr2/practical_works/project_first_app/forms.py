from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Car, CarOwner


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ("registration_number", "brand", "model_name", "color")


class OwnerCreationForm(UserCreationForm):
    first_name = forms.CharField(label="Имя", max_length=30)
    last_name = forms.CharField(label="Фамилия", max_length=30)
    passport_number = forms.CharField(
        label="Номер паспорта", min_length=10, max_length=10
    )
    home_address = forms.CharField(label="Домашний адрес", max_length=255)
    nationality = forms.CharField(label="Национальность", max_length=80)

    class Meta(UserCreationForm.Meta):
        model = CarOwner
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "birth_date",
            "passport_number",
            "home_address",
            "nationality",
        )
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        }
