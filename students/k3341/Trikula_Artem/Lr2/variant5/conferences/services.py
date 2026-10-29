from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Conference, Registration, Review
from .rules import ensure_registration_open


@transaction.atomic
def save_registration(
    *, author, conference_id: int, data: dict, registration_id: int | None = None
) -> Registration:
    conference = get_object_or_404(
        Conference.objects.select_for_update(), pk=conference_id
    )
    ensure_registration_open(conference)
    registration = (
        get_object_or_404(
            Registration, pk=registration_id, author=author, conference=conference
        )
        if registration_id
        else Registration(author=author, conference=conference)
    )
    registration.title = data["title"]
    registration.abstract = data["abstract"]
    registration.full_clean()
    registration.save()
    return registration


@transaction.atomic
def delete_registration(*, author, registration_id: int) -> None:
    registration = get_object_or_404(
        Registration.objects.select_related("conference"),
        pk=registration_id,
        author=author,
    )
    conference = get_object_or_404(
        Conference.objects.select_for_update(), pk=registration.conference_id
    )
    ensure_registration_open(conference)
    registration.delete()


@transaction.atomic
def set_publication_result(*, actor, registration_id: int, result: str) -> Registration:
    if not actor.is_active or not actor.has_perm("conferences.set_publication_result"):
        raise PermissionDenied("Недостаточно прав для изменения результата.")
    registration = get_object_or_404(
        Registration.objects.select_for_update(), pk=registration_id
    )
    registration.result = result
    registration.full_clean()
    registration.save(update_fields=["result", "updated_at"])
    return registration


@transaction.atomic
def save_review(
    *, author, conference_id: int, data: dict, review_id: int | None = None
) -> Review:
    conference = get_object_or_404(
        Conference.objects.select_for_update(), pk=conference_id
    )
    review = (
        get_object_or_404(Review, pk=review_id, author=author, conference=conference)
        if review_id
        else Review(author=author, conference=conference)
    )
    if not review.pk:
        review.conference_start = conference.start_date
        review.conference_end = conference.end_date
    review.rating = data["rating"]
    review.text = data["text"]
    review.full_clean()
    review.save()
    return review


@transaction.atomic
def save_conference(form) -> Conference:
    conference = form.instance
    if conference.pk:
        Conference.objects.select_for_update().get(pk=conference.pk)
    conference.full_clean()
    conference.save()
    form.save_m2m()
    return conference
