from collections.abc import Callable
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods, require_safe
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import CarForm, OwnerCreationForm
from .models import Car, CarOwner

SEARCH_QUERY_LIMIT = 100
PAGE_SIZE = 10


def is_registry_staff(user: AbstractUser | AnonymousUser) -> bool:
    return user.is_active and user.is_staff


def search_query(request: HttpRequest) -> str:
    return request.GET.get("q", "").strip()[:SEARCH_QUERY_LIMIT]


def staff_required(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @login_required
    @wraps(view)
    def wrapped(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not is_registry_staff(request.user):
            raise PermissionDenied("Требуется доступ сотрудника реестра.")
        return view(request, *args, **kwargs)

    return wrapped


@staff_required
@require_safe
def owner_list(request: HttpRequest) -> HttpResponse:
    owners = CarOwner.objects.all()
    query = search_query(request)
    if query:
        owners = owners.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    page = Paginator(owners, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request, "project_first_app/owner_list.html", {"page_obj": page, "query": query}
    )


@login_required
@require_safe
def owner_detail(request: HttpRequest, owner_id: int) -> HttpResponse:
    if not request.user.is_staff and request.user.pk != owner_id:
        raise PermissionDenied("Можно просматривать только свой профиль.")
    owner = get_object_or_404(
        CarOwner.objects.prefetch_related("licenses"), pk=owner_id
    )
    ownerships = owner.ownerships.select_related("car").order_by("start_date", "pk")
    return render(request, "owner.html", {"owner": owner, "ownerships": ownerships})


class CarListView(ListView):
    model = Car
    template_name = "project_first_app/car_list.html"
    context_object_name = "cars"
    paginate_by = PAGE_SIZE

    def get_queryset(self) -> QuerySet[Car]:
        queryset = super().get_queryset()
        query = search_query(self.request)
        if query:
            queryset = queryset.filter(
                Q(brand__icontains=query)
                | Q(model_name__icontains=query)
                | Q(registration_number__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = search_query(self.request)
        return context


class CarDetailView(DetailView):
    model = Car
    template_name = "project_first_app/car_detail.html"
    context_object_name = "car"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ownerships"] = self.object.ownerships.select_related("owner")
        return context


@require_safe
def home(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(
            "registry:owner_list"
            if request.user.is_staff
            else request.user.get_absolute_url()
        )
    return redirect("login")


@require_http_methods(["GET", "POST"])
def owner_create(request: HttpRequest) -> HttpResponse:
    form = OwnerCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request, "Учётная запись создана. Войдите с указанным паролем."
        )
        return redirect("login")
    return render(
        request,
        "project_first_app/form.html",
        {"form": form, "title": "Регистрация владельца"},
    )


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        return is_registry_staff(self.request.user)


class CarCreateView(StaffRequiredMixin, CreateView):
    model = Car
    form_class = CarForm
    template_name = "project_first_app/form.html"
    extra_context = {"title": "Добавить автомобиль"}


class CarUpdateView(StaffRequiredMixin, UpdateView):
    model = Car
    form_class = CarForm
    template_name = "project_first_app/form.html"
    extra_context = {"title": "Редактировать автомобиль"}


class CarDeleteView(StaffRequiredMixin, DeleteView):
    model = Car
    template_name = "project_first_app/car_confirm_delete.html"
    success_url = reverse_lazy("registry:car_list")
