from django.urls import path

from . import views

app_name = "conferences"
urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("conferences/<int:pk>/", views.detail, name="detail"),
    path(
        "conferences/<int:pk>/register/",
        views.registration_create,
        name="registration_create",
    ),
    path("my/registrations/", views.my_registrations, name="my_registrations"),
    path(
        "my/registrations/<int:pk>/edit/",
        views.registration_edit,
        name="registration_edit",
    ),
    path(
        "my/registrations/<int:pk>/delete/",
        views.registration_delete,
        name="registration_delete",
    ),
    path("conferences/<int:pk>/review/", views.review_create, name="review_create"),
    path("my/reviews/<int:pk>/edit/", views.review_edit, name="review_edit"),
    path("manage/participants/", views.participants, name="participants"),
    path(
        "manage/registrations/<int:pk>/result/",
        views.publication_result,
        name="publication_result",
    ),
    path(
        "manage/conferences/create/", views.conference_create, name="conference_create"
    ),
    path(
        "manage/conferences/<int:pk>/edit/",
        views.conference_edit,
        name="conference_edit",
    ),
]
