from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from .rules import ensure_review_allowed


class Topic(models.Model):
    name = models.CharField("Тематика", max_length=100, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Тематика"
        verbose_name_plural = "Тематики"

    def __str__(self) -> str:
        return self.name


class Venue(models.Model):
    name = models.CharField("Место проведения", max_length=180)
    city = models.CharField("Город", max_length=100)
    address = models.CharField("Адрес", max_length=255)
    description = models.TextField("Описание площадки")

    class Meta:
        ordering = ("city", "name", "pk")
        verbose_name = "Площадка"
        verbose_name_plural = "Площадки"

    def __str__(self) -> str:
        return f"{self.name}, {self.city}"


class Conference(models.Model):
    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание")
    start_date = models.DateField("Начало")
    end_date = models.DateField("Окончание")
    participation_terms = models.TextField("Условия участия")
    venue = models.ForeignKey(
        Venue,
        on_delete=models.PROTECT,
        related_name="conferences",
        verbose_name="Площадка",
    )
    topics = models.ManyToManyField(
        Topic, related_name="conferences", verbose_name="Тематики"
    )

    class Meta:
        ordering = ("start_date", "pk")
        verbose_name = "Конференция"
        verbose_name_plural = "Конференции"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="conference_dates_order",
            )
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("conferences:detail", args=[self.pk])

    @property
    def registration_open(self) -> bool:
        return timezone.localdate() < self.start_date

    @property
    def finished(self) -> bool:
        return timezone.localdate() > self.end_date

    @property
    def phase(self) -> str:
        if self.registration_open:
            return "Приём заявок"
        return "Завершена" if self.finished else "Идёт сейчас"


class Registration(models.Model):
    class Result(models.TextChoices):
        PENDING = "pending", "Не рассмотрен"
        RECOMMENDED = "recommended", "Рекомендован к публикации"
        NOT_RECOMMENDED = "not_recommended", "Не рекомендован к публикации"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name="Автор",
    )
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name="Конференция",
    )
    title = models.CharField("Название доклада", max_length=200)
    abstract = models.TextField("Аннотация", max_length=4000)
    result = models.CharField(
        "Результат выступления",
        max_length=20,
        choices=Result.choices,
        default=Result.PENDING,
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Изменена", auto_now=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        permissions = [
            ("set_publication_result", "Может указывать результат выступления")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("author", "conference"),
                name="registration_author_conference_unique",
            ),
            models.CheckConstraint(
                condition=Q(result__in=["pending", "recommended", "not_recommended"]),
                name="registration_result_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.author}: {self.title}"


class Review(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Автор",
    )
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Конференция",
    )
    text = models.TextField("Отзыв", max_length=4000)
    rating = models.PositiveSmallIntegerField(
        "Оценка от 1 до 10", validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    conference_start = models.DateField("Дата начала конференции", editable=False)
    conference_end = models.DateField("Дата окончания конференции", editable=False)
    created_at = models.DateTimeField("Опубликован", auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        constraints = [
            models.UniqueConstraint(
                fields=("author", "conference"), name="review_author_conference_unique"
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=10), name="review_rating_range"
            ),
            models.CheckConstraint(
                condition=Q(conference_end__gte=F("conference_start")),
                name="review_snapshot_dates_order",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.author_id and self.conference_id:
            ensure_review_allowed(self.author, self.conference)
            if self._state.adding:
                self.conference_start = self.conference.start_date
                self.conference_end = self.conference.end_date

    def __str__(self) -> str:
        return f"{self.author}: {self.rating}/10"
