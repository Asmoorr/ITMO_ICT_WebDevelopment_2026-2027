from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class ConferenceUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "organization", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Работа и учёба", {"fields": ("organization",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Участник", {"fields": ("first_name", "last_name", "email", "organization")}),
    )
