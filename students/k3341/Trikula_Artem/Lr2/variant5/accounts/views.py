from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SignUpForm


@require_http_methods(["GET", "POST"])
def signup(request: HttpRequest) -> HttpResponse:
    form = SignUpForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request, "Учётная запись создана. Войдите, чтобы подать заявку."
        )
        return redirect("login")
    return render(
        request,
        "form.jinja",
        {
            "form": form,
            "title": "Регистрация участника",
            "submit_label": "Создать учётную запись",
        },
        using="jinja2",
    )
