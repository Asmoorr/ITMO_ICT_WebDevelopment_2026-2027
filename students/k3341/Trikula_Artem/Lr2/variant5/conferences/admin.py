from django.contrib import admin
from django.db import transaction

from .forms import RegistrationAdminForm
from .models import Conference, Registration, Review, Topic, Venue
from .services import set_publication_result


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "address")
    search_fields = ("name", "city")


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "end_date", "venue")
    list_filter = ("topics", "venue")
    search_fields = ("title", "description")
    filter_horizontal = ("topics",)

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if change:
                Conference.objects.select_for_update().get(pk=obj.pk)
            super().save_model(request, obj, form, change)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    form = RegistrationAdminForm
    list_display = ("author", "conference", "title", "result")
    list_filter = ("conference", "result")
    search_fields = ("author__last_name", "title")
    list_select_related = ("author", "conference")

    def get_readonly_fields(self, request, obj=None):
        fields = ["created_at", "updated_at"]
        if obj:
            fields += ["author", "conference"]
        if not request.user.has_perm("conferences.set_publication_result"):
            fields += ["result"]
        return fields

    def save_model(self, request, obj, form, change):
        if change and "result" in form.changed_data:
            set_publication_result(
                actor=request.user, registration_id=obj.pk, result=obj.result
            )
        super().save_model(request, obj, form, change)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "author",
        "conference",
        "rating",
        "conference_start",
        "conference_end",
    )
    list_filter = ("conference", "rating")
    list_select_related = ("author", "conference")
    readonly_fields = ("conference_start", "conference_end", "created_at")

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.readonly_fields)
        if obj:
            fields += ["author", "conference"]
        return fields


admin.site.site_header = "Научные конференции"
admin.site.site_title = "Конференции"
admin.site.index_title = "Управление конференциями и участниками"
