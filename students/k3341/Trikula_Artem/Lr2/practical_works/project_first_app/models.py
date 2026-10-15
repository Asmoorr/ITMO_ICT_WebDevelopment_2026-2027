from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q, Value
from django.urls import reverse


class CarOwner(AbstractUser):
    first_name = models.CharField("Имя", max_length=30)
    last_name = models.CharField("Фамилия", max_length=30)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)
    passport_number = models.CharField(
        "Номер паспорта",
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        validators=[
            RegexValidator(r"^\d{10}$", "Укажите 10 цифр: серию и номер паспорта.")
        ],
    )
    home_address = models.CharField("Домашний адрес", max_length=255, blank=True)
    nationality = models.CharField("Национальность", max_length=80, blank=True)

    class Meta:
        ordering = ("last_name", "first_name", "pk")
        verbose_name = "Владелец-пользователь"
        verbose_name_plural = "Владельцы-пользователи"

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    def get_absolute_url(self) -> str:
        return reverse("registry:owner_detail", args=[self.pk])


class Car(models.Model):
    registration_number = models.CharField(
        "Государственный номер", max_length=15, unique=True
    )
    brand = models.CharField("Марка", max_length=20)
    model_name = models.CharField("Модель", max_length=20)
    color = models.CharField("Цвет", max_length=30, blank=True)
    owners = models.ManyToManyField(
        "CarOwner", through="Ownership", related_name="cars", verbose_name="Владельцы"
    )

    class Meta:
        ordering = ("brand", "model_name", "pk")
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"

    def __str__(self) -> str:
        return f"{self.brand} {self.model_name} · {self.registration_number}"

    def get_absolute_url(self) -> str:
        return reverse("registry:car_detail", args=[self.pk])


class Ownership(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ownerships",
        verbose_name="Владелец",
    )
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="ownerships",
        verbose_name="Автомобиль",
    )
    start_date = models.DateField("Начало владения")
    end_date = models.DateField(
        "Окончание владения",
        null=True,
        blank=True,
        help_text="Последний день владения включительно. Пусто — владение продолжается.",
    )

    class Meta:
        ordering = ("car_id", "start_date", "pk")
        verbose_name = "Владение"
        verbose_name_plural = "История владения"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="ownership_dates_order",
            ),
            ExclusionConstraint(
                name="ownership_car_period_exclusion",
                expressions=[
                    ("car", RangeOperators.EQUAL),
                    (
                        models.Func(
                            F("start_date"),
                            F("end_date"),
                            Value("[]"),
                            function="DATERANGE",
                            output_field=DateRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if not self.car_id or not self.start_date:
            return
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "Окончание не может быть раньше начала."}
            )
        overlaps = type(self).objects.filter(car_id=self.car_id).exclude(pk=self.pk)
        overlaps = overlaps.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=self.start_date)
        )
        if self.end_date:
            overlaps = overlaps.filter(start_date__lte=self.end_date)
        if overlaps.exists():
            raise ValidationError("У автомобиля уже есть владелец в указанном периоде.")

    def __str__(self) -> str:
        return f"{self.owner} — {self.car} с {self.start_date}"


class DriverLicense(models.Model):
    class Category(models.TextChoices):
        A = "A", "A — мотоциклы"
        B = "B", "B — легковые автомобили"
        C = "C", "C — грузовые автомобили"
        D = "D", "D — автобусы"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="licenses",
        verbose_name="Владелец",
    )
    number = models.CharField(
        "Номер удостоверения",
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^\d{10}$", "Номер должен содержать 10 цифр.")],
    )
    category = models.CharField("Категория", max_length=10, choices=Category.choices)
    issued_on = models.DateField("Дата выдачи")

    class Meta:
        ordering = ("-issued_on", "pk")
        verbose_name = "Водительское удостоверение"
        verbose_name_plural = "Водительские удостоверения"

    def __str__(self) -> str:
        return f"{self.number} ({self.category})"
