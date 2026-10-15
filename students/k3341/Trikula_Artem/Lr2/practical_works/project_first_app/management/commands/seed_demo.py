"""Repeatable fictional records; never deletes or resets existing user data."""

import os
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from project_first_app.forms import CarForm
from project_first_app.models import Car, CarOwner, DriverLicense, Ownership


class Command(BaseCommand):
    help = "Добавить вымышленные данные и локального администратора из окружения"

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("DJANGO_DEMO_PASSWORD")
        if not password:
            raise CommandError("Укажите DJANGO_DEMO_PASSWORD в Lr2/.env")
        User = get_user_model()
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "email": "admin@example.test",
            },
        )
        if created:
            admin.set_password(password)
            admin.save()
        owners = []
        for index, (first, last) in enumerate(
            [
                ("Артём", "Соколов"),
                ("Анна", "Морозова"),
                ("Иван", "Орлов"),
                ("Мария", "Волкова"),
                ("Павел", "Лебедев"),
                ("Ольга", "Белова"),
            ],
            start=1,
        ):
            owner, created = CarOwner.objects.get_or_create(
                username=f"owner{index}",
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "birth_date": date(1990 + index, 4, 12),
                    "passport_number": f"990000{index:04d}",
                    "home_address": f"Учебный город, Примерная улица, дом {index}",
                    "nationality": "Учебное значение",
                },
            )
            if created:
                owner.set_password(password)
                owner.save()
            owners.append(owner)
            DriverLicense.objects.get_or_create(
                number=f"990000{index:04d}",
                defaults={
                    "owner": owner,
                    "category": "B",
                    "issued_on": date(2018, 1, 1),
                },
            )
        cars = []
        for number, brand, model, color in [
            ("А101АА178", "Toyota", "Corolla", "Серебристый"),
            ("В202ВВ178", "Skoda", "Octavia", "Белый"),
            ("Е303ЕЕ178", "Lada", "Vesta", "Синий"),
            ("К404КК178", "Kia", "Rio", "Красный"),
            ("М505ММ178", "Renault", "Logan", "Серый"),
            ("Н606НН178", "Hyundai", "Solaris", "Чёрный"),
            ("Р707РР178", "Ford", "Focus", "Зелёный"),
        ]:
            car = Car.objects.filter(registration_number=number).first()
            if car is None:
                form = CarForm(
                    {
                        "registration_number": number,
                        "brand": brand,
                        "model_name": model,
                        "color": color,
                    }
                )
                if not form.is_valid():
                    raise CommandError(str(form.errors))
                car = form.save()
            cars.append(car)
        # One car may change owners; inclusive periods do not overlap.
        periods = [
            (0, 0, date(2019, 1, 1), date(2020, 12, 31)),
            (1, 0, date(2021, 1, 1), None),
            (0, 1, date(2019, 1, 1), date(2020, 12, 31)),
            (1, 1, date(2021, 1, 1), None),
            (0, 2, date(2022, 1, 1), None),
            (1, 3, date(2022, 1, 1), None),
        ]
        for owner_index, car_index, start, end in periods:
            ownership, created = Ownership.objects.get_or_create(
                owner=owners[owner_index],
                car=cars[car_index],
                start_date=start,
                defaults={"end_date": end},
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {CarOwner.objects.count()} владельцев, {Car.objects.count()} автомобилей. Администратор: admin (пароль из .env)."
            )
        )
