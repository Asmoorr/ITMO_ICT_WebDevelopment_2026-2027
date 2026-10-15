from datetime import date
from io import StringIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import resolve, reverse

from project_first_app.models import Car, CarOwner, DriverLicense, Ownership


class RegistryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_superuser(
            username="staff", password="Valid-test-12345"
        )
        cls.owner = cls.make_owner("Первый", "Владелец", 1)
        cls.other = cls.make_owner("Второй", "Владелец", 2)
        cls.car = Car.objects.create(
            registration_number="TEST-001",
            brand="Toyota",
            model_name="Corolla",
            color="Белый",
        )
        cls.period = Ownership.objects.create(
            owner=cls.owner,
            car=cls.car,
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31),
        )
        DriverLicense.objects.create(
            owner=cls.owner,
            number="1234567890",
            category="B",
            issued_on=date(2019, 1, 1),
        )

    @classmethod
    def make_owner(cls, first, last, number):
        return CarOwner.objects.create_user(
            username=f"person{number}",
            password="Valid-test-12345",
            first_name=first,
            last_name=last,
            passport_number=f"110000{number:04d}",
            home_address="Тестовый адрес",
            nationality="Тестовое значение",
        )

    def test_owner_detail_missing_and_escaping(self):
        self.client.force_login(self.staff)
        self.owner.first_name = "<script>alert(1)</script>"
        self.owner.save()
        response = self.client.get(self.owner.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "1234567890")
        self.assertContains(response, "TEST-001")
        self.assertEqual(self.client.get("/owner/999999/").status_code, 404)

    def test_models_registered_in_admin(self):
        for model in (CarOwner, Car, DriverLicense, Ownership):
            self.assertIn(model, admin.site._registry)
            self.client.force_login(self.staff)
            self.assertEqual(
                self.client.get(
                    reverse(
                        f"admin:project_first_app_{model._meta.model_name}_changelist"
                    )
                ).status_code,
                200,
            )

    def test_overlap_validation(self):
        invalid = Ownership(
            owner=self.other, car=self.car, start_date=date(2021, 12, 31), end_date=None
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()
        # A sale date is inclusive: a new owner starts on the following day.
        valid = Ownership(owner=self.other, car=self.car, start_date=date(2022, 1, 1))
        valid.full_clean()
        valid.save()
        self.assertEqual(self.car.owners.count(), 2)

    def test_overlap_blocked_by_postgresql_even_without_full_clean(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ownership.objects.create(
                owner=self.other, car=self.car, start_date=date(2021, 1, 1)
            )

    def test_reversed_dates_blocked_by_postgresql(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ownership.objects.create(
                owner=self.other,
                car=self.car,
                start_date=date(2030, 1, 2),
                end_date=date(2030, 1, 1),
            )

    def test_duplicate_registration_blocked_by_postgresql(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Car.objects.create(
                registration_number=self.car.registration_number,
                brand="Kia",
                model_name="Rio",
            )

    def test_list_search_and_pagination(self):
        self.client.force_login(self.staff)
        for number in range(20):
            Car.objects.create(
                registration_number=f"SEARCH-{number}",
                brand="Lada",
                model_name=f"Vesta {number}",
            )
        response = self.client.get(
            reverse("registry:car_list"), {"q": "Lada", "page": 2}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 20)
        self.assertContains(response, "q=Lada")
        self.assertNotContains(response, "Corolla")
        self.assertEqual(
            self.client.get(reverse("registry:car_list"), {"page": 999}).status_code,
            404,
        )

    def test_seed_is_repeatable_and_does_not_reset_password(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"DJANGO_DEMO_PASSWORD": "Seed-Password-123"}):
            call_command("seed_demo", stdout=StringIO())
            counts = (
                CarOwner.objects.count(),
                Car.objects.count(),
                Ownership.objects.count(),
            )
            admin_user = get_user_model().objects.get(username="admin")
            admin_user.set_password("Changed-Password-123")
            admin_user.save()
            call_command("seed_demo", stdout=StringIO())
        self.assertEqual(
            counts,
            (CarOwner.objects.count(), Car.objects.count(), Ownership.objects.count()),
        )
        admin_user.refresh_from_db()
        self.assertTrue(admin_user.check_password("Changed-Password-123"))

    def test_car_crud_via_class_based_views(self):
        self.client.force_login(self.staff)
        url = reverse("registry:car_create")
        self.assertTrue(hasattr(resolve(url).func, "view_class"))
        payload = {
            "registration_number": "CRUD-100",
            "brand": "Skoda",
            "model_name": "Octavia",
            "color": "Серый",
        }
        response = self.client.post(url, payload)
        car = Car.objects.get(registration_number="CRUD-100")
        self.assertRedirects(response, car.get_absolute_url())
        payload["color"] = "Белый"
        response = self.client.post(
            reverse("registry:car_update", args=[car.pk]), payload
        )
        car.refresh_from_db()
        self.assertEqual(car.color, "Белый")
        delete_url = reverse("registry:car_delete", args=[car.pk])
        self.assertEqual(self.client.get(delete_url).status_code, 200)
        self.assertTrue(Car.objects.filter(pk=car.pk).exists())
        self.assertRedirects(self.client.post(delete_url), reverse("registry:car_list"))
        self.assertFalse(Car.objects.filter(pk=car.pk).exists())

    def test_mutations_require_staff_and_csrf(self):
        url = reverse("registry:car_update", args=[self.car.pk])
        self.assertEqual(self.client.post(url, {"brand": "Hacked"}).status_code, 302)
        ordinary = get_user_model().objects.create_user(
            username="ordinary", password="Valid-test-12345"
        )
        self.client.force_login(ordinary)
        self.assertEqual(self.client.post(url, {"brand": "Hacked"}).status_code, 403)
        self.car.refresh_from_db()
        self.assertEqual(self.car.brand, "Toyota")
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        self.assertEqual(csrf_client.post(url, {"brand": "Hacked"}).status_code, 403)

    def test_duplicate_car_form_has_errors(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("registry:car_create"),
            {
                "registration_number": self.car.registration_number,
                "brand": "Kia",
                "model_name": "Rio",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("registration_number", response.context["form"].errors)

    def test_owner_creation_is_function_based_and_saves_three_records(self):
        self.client.force_login(self.staff)
        url = reverse("registry:owner_create")
        self.assertFalse(hasattr(resolve(url).func, "view_class"))
        for number in range(3):
            payload = {
                "first_name": f"Новый{number}",
                "last_name": "Владелец",
                "birth_date": "1995-01-01",
            }
            payload.update(
                username=f"new{number}",
                passport_number=f"220000{number:04d}",
                home_address="Вымышленная улица",
                nationality="Учебная",
                password1="Valid-test-12345",
                password2="Valid-test-12345",
                is_staff="on",
                is_superuser="on",
            )
            response = self.client.post(url, payload)
            self.assertEqual(
                response.status_code, 302, getattr(response, "context", None)
            )
        self.assertEqual(
            CarOwner.objects.filter(
                last_name="Владелец", first_name__startswith="Новый"
            ).count(),
            3,
        )

    def test_public_signup_hashes_password_and_never_grants_privileges(self):
        payload = {
            "username": "signup",
            "first_name": "Новый",
            "last_name": "Пользователь",
            "birth_date": "1996-05-03",
            "passport_number": "3300000001",
            "home_address": "Вымышленный адрес",
            "nationality": "Учебная",
            "password1": "Valid-test-12345",
            "password2": "Valid-test-12345",
            "is_staff": "on",
            "is_superuser": "on",
        }
        self.assertRedirects(
            self.client.post(reverse("registry:owner_create"), payload),
            reverse("login"),
        )
        owner = CarOwner.objects.get(username="signup")
        self.assertTrue(owner.check_password(payload["password1"]))
        self.assertNotEqual(owner.password, payload["password1"])
        self.assertFalse(owner.is_staff)
        self.assertFalse(owner.is_superuser)
        self.assertTrue(
            self.client.login(username="signup", password=payload["password1"])
        )
        response = self.client.get(owner.get_absolute_url())
        self.assertContains(response, "3300000001")
        self.assertContains(response, "Вымышленный адрес")
        self.assertContains(response, "Учебная")
        self.assertRedirects(self.client.get("/"), owner.get_absolute_url())

    def test_personal_data_is_private(self):
        self.assertEqual(
            self.client.get(self.owner.get_absolute_url()).status_code, 302
        )
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(self.owner.get_absolute_url()).status_code, 403
        )
        self.assertEqual(
            self.client.get(reverse("registry:owner_list")).status_code, 403
        )
        self.assertNotContains(
            self.client.get(self.car.get_absolute_url()), self.owner.passport_number
        )

    def test_registration_rejects_invalid_passport_and_weak_password(self):
        payload = {
            "username": "bad",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "passport_number": "abcdefghij",
            "home_address": "Адрес",
            "nationality": "Учебная",
            "password1": "123",
            "password2": "123",
        }
        response = self.client.post(reverse("registry:owner_create"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("passport_number", response.context["form"].errors)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(CarOwner.objects.filter(username="bad").exists())

    def test_extended_fields_in_admin(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("admin:project_first_app_carowner_change", args=[self.owner.pk])
        )
        for name in ("passport_number", "home_address", "nationality", "birth_date"):
            self.assertContains(response, f'name="{name}"')

    def test_admin_can_add_a_car_and_ownership(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("admin:project_first_app_ownership_add"),
            {
                "owner": self.other.pk,
                "car": self.car.pk,
                "start_date": "2022-01-01",
                "end_date": "2023-01-01",
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Ownership.objects.filter(
                owner=self.other, car=self.car, start_date=date(2022, 1, 1)
            ).exists()
        )

    def test_admin_rejects_overlapping_ownership(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("admin:project_first_app_ownership_add"),
            {
                "owner": self.other.pk,
                "car": self.car.pk,
                "start_date": "2021-01-01",
                "end_date": "2023-01-01",
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "уже есть владелец")
        self.assertEqual(self.car.ownerships.count(), 1)

    def test_three_cars_created_through_http_form(self):
        self.client.force_login(self.staff)
        for number in range(3):
            response = self.client.post(
                reverse("registry:car_create"),
                {
                    "registration_number": f"FORM-{number}",
                    "brand": "Lada",
                    "model_name": "Vesta",
                    "color": "Белый",
                },
            )
            self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Car.objects.filter(registration_number__startswith="FORM-").count(), 3
        )

    def test_new_car_inline_rejects_overlapping_unsaved_periods(self):
        from django.forms.models import inlineformset_factory

        from project_first_app.admin import OwnershipInlineFormSet

        FormSet = inlineformset_factory(
            Car,
            Ownership,
            formset=OwnershipInlineFormSet,
            fields=("owner", "start_date", "end_date"),
            extra=2,
        )
        formset = FormSet(
            instance=Car(
                registration_number="INLINE-TEST", brand="Lada", model_name="Vesta"
            ),
            prefix="ownerships",
            data={
                "ownerships-TOTAL_FORMS": "2",
                "ownerships-INITIAL_FORMS": "0",
                "ownerships-0-owner": str(self.owner.pk),
                "ownerships-0-start_date": "2025-01-01",
                "ownerships-0-end_date": "2025-12-31",
                "ownerships-1-owner": str(self.other.pk),
                "ownerships-1-start_date": "2025-06-01",
                "ownerships-1-end_date": "",
            },
        )
        self.assertFalse(formset.is_valid())
        self.assertIn("пересекаться", str(formset.non_form_errors()))
