from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Car, CarOwner, DriverLicense, Ownership


class OwnershipInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        periods = []
        for form in self.forms:
            data = form.cleaned_data
            if not data or data.get("DELETE"):
                continue
            item = form.instance
            if (
                not item.car_id and not isinstance(self.instance, Car)
            ) or not item.start_date:
                continue
            for previous in periods:
                if (
                    item.car_id == previous.car_id
                    and (not item.end_date or previous.start_date <= item.end_date)
                    and (not previous.end_date or item.start_date <= previous.end_date)
                ):
                    raise ValidationError(
                        "Периоды владения одним автомобилем не должны пересекаться."
                    )
            periods.append(item)


class LicenseInline(admin.TabularInline):
    model = DriverLicense
    extra = 0


class OwnershipInline(admin.TabularInline):
    model = Ownership
    formset = OwnershipInlineFormSet
    extra = 0


@admin.register(CarOwner)
class CarOwnerAdmin(UserAdmin):
    list_display = (
        "username",
        "last_name",
        "first_name",
        "birth_date",
        "nationality",
        "is_staff",
    )
    fieldsets = UserAdmin.fieldsets + (
        (
            "Данные владельца",
            {
                "fields": (
                    "birth_date",
                    "passport_number",
                    "home_address",
                    "nationality",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Данные владельца",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "birth_date",
                    "passport_number",
                    "home_address",
                    "nationality",
                )
            },
        ),
    )
    inlines = (LicenseInline, OwnershipInline)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "brand", "model_name", "color")
    list_filter = ("brand",)
    search_fields = ("registration_number", "brand", "model_name")
    inlines = (OwnershipInline,)


@admin.register(Ownership)
class OwnershipAdmin(admin.ModelAdmin):
    list_display = ("owner", "car", "start_date", "end_date")
    list_select_related = ("owner", "car")
    search_fields = ("owner__last_name", "car__registration_number")


@admin.register(DriverLicense)
class DriverLicenseAdmin(admin.ModelAdmin):
    list_display = ("number", "owner", "category", "issued_on")
    list_filter = ("category",)
    list_select_related = ("owner",)
    search_fields = ("number", "owner__last_name")


admin.site.site_header = "Реестр автомобилей"
admin.site.site_title = "Реестр"
admin.site.index_title = "Управление реестром"
