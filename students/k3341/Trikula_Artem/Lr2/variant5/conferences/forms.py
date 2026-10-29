from django import forms

from .models import Conference, Registration, Review, Topic, Venue
from .rules import ensure_registration_open


class CatalogFilterForm(forms.Form):
    q = forms.CharField(label="Поиск", max_length=100, required=False)
    topic = forms.ModelChoiceField(
        label="Тематика",
        queryset=Topic.objects.all(),
        empty_label="Все тематики",
        required=False,
    )
    venue = forms.ModelChoiceField(
        label="Площадка",
        queryset=Venue.objects.all(),
        empty_label="Все площадки",
        required=False,
    )
    phase = forms.ChoiceField(
        label="Период",
        choices=[
            ("", "Все конференции"),
            ("upcoming", "Приём заявок"),
            ("ongoing", "Идут сейчас"),
            ("past", "Завершённые"),
        ],
        required=False,
    )


class ConferenceForm(forms.ModelForm):
    class Meta:
        model = Conference
        fields = (
            "title",
            "description",
            "start_date",
            "end_date",
            "venue",
            "topics",
            "participation_terms",
        )
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "topics": forms.CheckboxSelectMultiple(),
        }


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ("title", "abstract")
        widgets = {"abstract": forms.Textarea(attrs={"rows": 6})}


class ResultForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ("result",)


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "text")
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 10}),
            "text": forms.Textarea(attrs={"rows": 6}),
        }


class RegistrationAdminForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = "__all__"

    def clean(self):
        data = super().clean()
        conference = data.get("conference") or getattr(
            self.instance, "conference", None
        )
        if conference and (
            not self.instance.pk
            or {"title", "abstract"}.intersection(self.changed_data)
        ):
            ensure_registration_open(conference)
        return data


class ParticipantFilterForm(forms.Form):
    conference = forms.ModelChoiceField(
        label="Конференция",
        queryset=Conference.objects.all(),
        empty_label="Все конференции",
        required=False,
    )
    q = forms.CharField(label="Автор или доклад", max_length=100, required=False)


class MyRegistrationFilterForm(forms.Form):
    q = forms.CharField(
        label="Название доклада или конференции", max_length=100, required=False
    )
    result = forms.ChoiceField(
        label="Результат",
        choices=[("", "Все результаты"), *Registration.Result.choices],
        required=False,
    )


class ReviewFilterForm(forms.Form):
    q = forms.CharField(label="Поиск в отзывах", max_length=100, required=False)
    rating = forms.TypedChoiceField(
        label="Оценка",
        choices=[
            ("", "Все оценки"),
            *((str(value), str(value)) for value in range(1, 11)),
        ],
        coerce=int,
        empty_value=None,
        required=False,
    )
