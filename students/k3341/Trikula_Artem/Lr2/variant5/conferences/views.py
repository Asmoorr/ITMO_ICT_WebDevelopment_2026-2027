from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Avg, Case, IntegerField, Q, Value, When
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_safe

from . import services
from .forms import (
    CatalogFilterForm,
    ConferenceForm,
    MyRegistrationFilterForm,
    ParticipantFilterForm,
    RegistrationForm,
    ResultForm,
    ReviewFilterForm,
    ReviewForm,
)
from .models import Conference, Registration, Review

PAGE_SIZE = 6


def show_form(request, form, title, *, cancel_url=None, submit_label="Сохранить"):
    return render(
        request,
        "form.jinja",
        {
            "form": form,
            "title": title,
            "cancel_url": cancel_url or reverse("conferences:catalog"),
            "submit_label": submit_label,
        },
        using="jinja2",
    )


def add_operation_error(form, error: ValidationError | IntegrityError) -> None:
    text = (
        " ".join(error.messages)
        if isinstance(error, ValidationError)
        else "Такая запись уже существует. Обновите страницу и проверьте свои заявки или отзывы."
    )
    form.add_error(None, text)


@require_safe
def catalog(request: HttpRequest) -> HttpResponse:
    today = timezone.localdate()
    form = CatalogFilterForm(request.GET)
    conferences = (
        Conference.objects.select_related("venue")
        .prefetch_related("topics")
        .annotate(average_rating=Avg("reviews__rating"))
    )
    if form.is_valid():
        filters = form.cleaned_data
        if filters["q"]:
            query = filters["q"]
            conferences = conferences.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(topics__name__icontains=query)
            )
        if filters["topic"]:
            conferences = conferences.filter(topics=filters["topic"])
        if filters["venue"]:
            conferences = conferences.filter(venue=filters["venue"])
        match filters["phase"]:
            case "upcoming":
                conferences = conferences.filter(start_date__gt=today)
            case "ongoing":
                conferences = conferences.filter(
                    start_date__lte=today, end_date__gte=today
                )
            case "past":
                conferences = conferences.filter(end_date__lt=today)
    else:
        conferences = conferences.none()
    conferences = (
        conferences.alias(
            phase_order=Case(
                When(start_date__gt=today, then=Value(0)),
                When(end_date__gte=today, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("phase_order", "start_date", "pk")
        .distinct()
    )
    page = Paginator(conferences, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "conferences/catalog.jinja",
        {"form": form, "page": page},
        using="jinja2",
    )


@require_safe
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    conference = get_object_or_404(
        Conference.objects.select_related("venue").prefetch_related("topics"), pk=pk
    )
    all_reviews = conference.reviews.select_related("author")
    reviews = all_reviews
    review_filters = ReviewFilterForm(request.GET)
    if review_filters.is_valid():
        query = review_filters.cleaned_data["q"]
        rating = review_filters.cleaned_data["rating"]
        if query:
            reviews = reviews.filter(
                Q(text__icontains=query)
                | Q(author__first_name__icontains=query)
                | Q(author__last_name__icontains=query)
            )
        if rating is not None:
            reviews = reviews.filter(rating=rating)
    else:
        reviews = reviews.none()
    page = Paginator(reviews, PAGE_SIZE).get_page(request.GET.get("page"))
    registration = current_review = None
    if request.user.is_authenticated:
        registration = conference.registrations.filter(author=request.user).first()
        current_review = all_reviews.filter(author=request.user).first()
    context = {
        "conference": conference,
        "page": page,
        "registration": registration,
        "current_review": current_review,
        "participant_count": conference.registrations.count(),
        "average_rating": all_reviews.aggregate(value=Avg("rating"))["value"],
        "review_filters": review_filters,
    }
    return render(request, "conferences/detail.jinja", context, using="jinja2")


@login_required
@require_safe
def my_registrations(request: HttpRequest) -> HttpResponse:
    registrations = request.user.registrations.select_related(
        "conference", "conference__venue"
    )
    form = MyRegistrationFilterForm(request.GET)
    if form.is_valid():
        if form.cleaned_data["q"]:
            query = form.cleaned_data["q"]
            registrations = registrations.filter(
                Q(title__icontains=query) | Q(conference__title__icontains=query)
            )
        if form.cleaned_data["result"]:
            registrations = registrations.filter(result=form.cleaned_data["result"])
    else:
        registrations = registrations.none()
    page = Paginator(registrations, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "conferences/my_registrations.jinja",
        {"page": page, "form": form},
        using="jinja2",
    )


@login_required
@require_http_methods(["GET", "POST"])
def registration_create(request: HttpRequest, pk: int) -> HttpResponse:
    conference = get_object_or_404(Conference, pk=pk)
    instance = Registration(author=request.user, conference=conference)
    form = RegistrationForm(
        request.POST if request.method == "POST" else None, instance=instance
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.save_registration(
                author=request.user, conference_id=pk, data=form.cleaned_data
            )
        except (ValidationError, IntegrityError) as error:
            add_operation_error(form, error)
        else:
            messages.success(request, "Заявка на выступление подана.")
            return redirect("conferences:my_registrations")
    return show_form(
        request,
        form,
        f"Заявка: {conference.title}",
        cancel_url=conference.get_absolute_url(),
        submit_label="Подать заявку",
    )


@login_required
@require_http_methods(["GET", "POST"])
def registration_edit(request: HttpRequest, pk: int) -> HttpResponse:
    registration = get_object_or_404(
        Registration.objects.select_related("conference"), pk=pk, author=request.user
    )
    form = RegistrationForm(
        request.POST if request.method == "POST" else None, instance=registration
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.save_registration(
                author=request.user,
                conference_id=registration.conference_id,
                data=form.cleaned_data,
                registration_id=pk,
            )
        except (ValidationError, IntegrityError) as error:
            add_operation_error(form, error)
        else:
            messages.success(request, "Заявка обновлена.")
            return redirect("conferences:my_registrations")
    return show_form(
        request,
        form,
        "Редактировать заявку",
        cancel_url=reverse("conferences:my_registrations"),
    )


@login_required
@require_http_methods(["GET", "POST"])
def registration_delete(request: HttpRequest, pk: int) -> HttpResponse:
    registration = get_object_or_404(
        Registration.objects.select_related("conference"), pk=pk, author=request.user
    )
    error = None
    if request.method == "POST":
        try:
            services.delete_registration(author=request.user, registration_id=pk)
        except ValidationError as exc:
            error = " ".join(exc.messages)
        else:
            messages.success(request, "Заявка отменена.")
            return redirect("conferences:my_registrations")
    return render(
        request,
        "confirm_delete.jinja",
        {
            "title": "Отменить заявку?",
            "object_name": registration.title,
            "error": error,
            "cancel_url": reverse("conferences:my_registrations"),
        },
        using="jinja2",
    )


@login_required
@require_http_methods(["GET", "POST"])
def review_create(request: HttpRequest, pk: int) -> HttpResponse:
    conference = get_object_or_404(Conference, pk=pk)
    return edit_review(
        request, conference, Review(author=request.user, conference=conference)
    )


@login_required
@require_http_methods(["GET", "POST"])
def review_edit(request: HttpRequest, pk: int) -> HttpResponse:
    review = get_object_or_404(
        Review.objects.select_related("conference"), pk=pk, author=request.user
    )
    return edit_review(request, review.conference, review)


def edit_review(request, conference, review) -> HttpResponse:
    form = ReviewForm(
        request.POST if request.method == "POST" else None, instance=review
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.save_review(
                author=request.user,
                conference_id=conference.pk,
                data=form.cleaned_data,
                review_id=review.pk,
            )
        except (ValidationError, IntegrityError) as error:
            add_operation_error(form, error)
        else:
            messages.success(request, "Отзыв сохранён.")
            return redirect(conference)
    return show_form(
        request,
        form,
        f"Отзыв: {conference.title}",
        cancel_url=conference.get_absolute_url(),
        submit_label="Сохранить отзыв",
    )


@login_required
@permission_required("conferences.view_registration", raise_exception=True)
@require_safe
def participants(request: HttpRequest) -> HttpResponse:
    form = ParticipantFilterForm(request.GET)
    registrations = Registration.objects.select_related("author", "conference")
    if form.is_valid():
        conference = form.cleaned_data["conference"]
        query = form.cleaned_data["q"]
        if conference:
            registrations = registrations.filter(conference=conference)
        if query:
            registrations = registrations.filter(
                Q(title__icontains=query)
                | Q(author__first_name__icontains=query)
                | Q(author__last_name__icontains=query)
            )
    else:
        registrations = registrations.none()
    registrations = registrations.order_by(
        "conference__start_date", "conference_id", "author__last_name", "pk"
    )
    page = Paginator(registrations, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "conferences/participants.jinja",
        {"form": form, "page": page},
        using="jinja2",
    )


@login_required
@permission_required("conferences.set_publication_result", raise_exception=True)
@require_http_methods(["GET", "POST"])
def publication_result(request: HttpRequest, pk: int) -> HttpResponse:
    registration = get_object_or_404(
        Registration.objects.select_related("author", "conference"), pk=pk
    )
    form = ResultForm(
        request.POST if request.method == "POST" else None, instance=registration
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.set_publication_result(
                actor=request.user,
                registration_id=pk,
                result=form.cleaned_data["result"],
            )
        except ValidationError as error:
            add_operation_error(form, error)
        else:
            messages.success(request, "Результат выступления сохранён.")
            return redirect("conferences:participants")
    return show_form(
        request,
        form,
        f"Результат: {registration.title}",
        cancel_url=reverse("conferences:participants"),
    )


@login_required
@permission_required("conferences.add_conference", raise_exception=True)
@require_http_methods(["GET", "POST"])
def conference_create(request: HttpRequest) -> HttpResponse:
    return edit_conference(request, Conference())


@login_required
@permission_required("conferences.change_conference", raise_exception=True)
@require_http_methods(["GET", "POST"])
def conference_edit(request: HttpRequest, pk: int) -> HttpResponse:
    return edit_conference(request, get_object_or_404(Conference, pk=pk))


def edit_conference(request, conference) -> HttpResponse:
    form = ConferenceForm(
        request.POST if request.method == "POST" else None, instance=conference
    )
    if request.method == "POST" and form.is_valid():
        form.save(commit=False)
        try:
            conference = services.save_conference(form)
        except ValidationError as error:
            add_operation_error(form, error)
        else:
            messages.success(request, "Конференция сохранена.")
            return redirect(conference)
    return show_form(
        request,
        form,
        "Редактировать конференцию" if conference.pk else "Новая конференция",
    )
