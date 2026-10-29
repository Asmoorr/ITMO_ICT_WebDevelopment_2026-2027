from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.jinja", template_engine="jinja2"
        ),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("conferences.urls")),
]
