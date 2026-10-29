from django.core.exceptions import ValidationError
from django.utils import timezone


def ensure_registration_open(conference) -> None:
    if timezone.localdate() >= conference.start_date:
        raise ValidationError(
            "Приём и изменение заявок закрыты: конференция уже началась."
        )


def ensure_review_allowed(author, conference) -> None:
    if timezone.localdate() <= conference.end_date:
        raise ValidationError("Отзыв можно оставить после окончания конференции.")
    if not conference.registrations.filter(author_id=author.pk).exists():
        raise ValidationError(
            "Оставить отзыв могут только зарегистрированные участники конференции."
        )
